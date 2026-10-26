"""Bounded PSI runs with closed database snapshots and explicit failure receipts."""

import argparse
import asyncio
import csv
import hashlib
import json
import os
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .collector import PageSpeedCollector
from .storage import DuckDBStorage


def ordered_urls(csv_file: Path, storage: DuckDBStorage) -> list[str]:
    """Visit least recently attempted sites first; keep deterministic CSV tie order."""
    with csv_file.open(encoding="utf-8") as stream:
        urls = list(
            dict.fromkeys(
                row["url"].strip()
                for row in csv.DictReader(stream)
                if row.get("url", "").startswith(("http://", "https://"))
            )
        )
    rows = storage.con.raw_sql(
        "SELECT url, MAX(timestamp) FROM audits GROUP BY url"
    ).fetchall()
    recent = {url.rstrip("/"): str(timestamp) for url, timestamp in rows}
    return sorted(urls, key=lambda url: recent.get(url.rstrip("/"), ""))


def global_failure(error: str | None) -> bool:
    """Credential/quota failures describe the collector, not a municipality."""
    return bool(
        error
        and (
            error.startswith(("HTTP 401:", "HTTP 403:", "HTTP 429:"))
            or "API key not valid" in error
        )
    )


async def collect(
    csv_file: Path,
    db: Path,
    output: Path,
    *,
    max_sites: int = 1000,
    seconds: float = 1200,
    failure_limit: int = 3,
) -> dict[str, Any]:
    """Bound wall time and attempts; always close the writer before copying its DB."""
    if max_sites < 1 or seconds <= 0 or failure_limit < 1:
        raise ValueError("Limits must be positive")
    output.mkdir(parents=True, exist_ok=False)
    receipt: dict[str, Any] = {
        "schema": 1,
        "started_at": datetime.now(UTC).isoformat(),
        "source_sha": os.getenv("GITHUB_SHA", "local"),
        "input_sha256": hashlib.sha256(csv_file.read_bytes()).hexdigest(),
        "max_sites": max_sites,
        "seconds": seconds,
        "failure_limit": failure_limit,
        "attempted": 0,
        "successful": 0,
        "failed": 0,
        "status": "failed",
        "internet_archive": "not_attempted",
    }
    shutil.copy2(csv_file, output / "input.csv")
    for name in ("psi-results.json", "psi-results.csv", "psi_processing_state.json"):
        legacy = Path("data") / name
        if legacy.exists():
            (output / "legacy").mkdir(exist_ok=True)
            shutil.copy2(legacy, output / "legacy" / name)
    storage = DuckDBStorage(str(db))
    initialized = False
    try:
        key = os.getenv("PAGESPEED_API_KEY") or os.getenv("PSI_KEY")
        if not key:
            raise ValueError("Missing PSI credential")
        await storage.initialize()
        initialized = True
        urls = ordered_urls(csv_file, storage)
        receipt["eligible_sites"] = len(urls)
        consecutive = 0
        # Cancellation is awaited inside the context before closing the DB.
        try:
            async with asyncio.timeout(seconds), PageSpeedCollector(key) as collector:
                with (output / "audits.jsonl").open("w", encoding="utf-8") as stream:
                    for url in urls[:max_sites]:
                        audit = await collector.audit_site(url)
                        receipt["attempted"] += 1
                        if global_failure(audit.error_message):
                            receipt["status"] = "credential_or_quota_failure"
                            break
                        saving = asyncio.create_task(storage.save_audit(audit))
                        try:
                            await asyncio.shield(saving)
                        except asyncio.CancelledError:
                            # to_thread writes must finish before disconnect/snapshot.
                            await saving
                            raise
                        stream.write(audit.model_dump_json() + "\n")
                        stream.flush()
                        if audit.error_message:
                            receipt["failed"] += 1
                            consecutive += 1
                        else:
                            receipt["successful"] += 1
                            consecutive = 0
                        if consecutive >= failure_limit:
                            receipt["status"] = "consecutive_failures"
                            break
                    else:
                        receipt["status"] = (
                            "complete" if len(urls) <= max_sites else "site_budget"
                        )
        except TimeoutError:
            receipt["status"] = "time_budget"
        # Failed runs never replace the dashboard or update municipality quarantine.
        if receipt["successful"]:
            await storage.export_to_parquet(output)
            await storage.export_to_json(output)
            await storage.export_dashboard_json(output / "dashboard")
            # Keep the existing quarantine rule; never synthesize missing observations.
            await storage.update_quarantine(min_consecutive_days=3)
            await storage.export_quarantine_json(output / "quarantine.json")
    except Exception as exc:
        # Do not serialize exception URLs: httpx can include an API key in them.
        receipt["exception_type"] = type(exc).__name__
        receipt["status"] = "failed"
    finally:
        await storage.close()
        if initialized and db.exists():
            shutil.copy2(db, output / "rossio.duckdb")
        receipt["finished_at"] = datetime.now(UTC).isoformat()
        (output / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def seal(output: Path) -> Path:
    """Checksum a complete run, including its DB, raw responses and receipt."""
    files = sorted(
        p for p in output.rglob("*") if p.is_file() and p.name != "SHA256SUMS"
    )
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(output)}\n"
            for p in files
        )
    )
    bundle = output.with_suffix(".tar.gz")
    with tarfile.open(bundle, "w:gz") as archive:
        archive.add(output, arcname=output.name)
    return bundle


def publish_archive(output: Path, identifier: str, run_id: str) -> bool:
    """Publish immutable per-run files; require successful HTTP responses."""
    from internetarchive import upload

    manifest_path = output / "manifest.json"
    receipt = json.loads(manifest_path.read_text())
    access, secret = os.getenv("IA_ACCESS_KEY"), os.getenv("IA_SECRET_KEY")
    if not access or not secret:
        receipt["internet_archive"] = "skipped_missing_credentials"
        manifest_path.write_text(json.dumps(receipt, indent=2) + "\n")
        seal(output)
        return True  # explicitly skipped, never represented as published
    receipt["internet_archive"] = "submitted_verify_remote"
    manifest_path.write_text(json.dumps(receipt, indent=2) + "\n")
    bundle = seal(output)
    try:
        responses = list(
            upload(
                identifier,
                files={f"runs/{run_id}/{bundle.name}": str(bundle)},
                access_key=access,
                secret_key=secret,
                metadata={"mediatype": "data", "collection": "opensource_data"},
            )
        )
        if not responses or any(
            not 200 <= getattr(r, "status_code", 0) < 300 for r in responses
        ):
            raise RuntimeError("Archive upload rejected")
        receipt["internet_archive"] = "uploaded_http_success"
    except Exception:
        receipt["internet_archive"] = "upload_failed"
    manifest_path.write_text(json.dumps(receipt, indent=2) + "\n")
    seal(output)
    return bool(receipt["internet_archive"] == "uploaded_http_success")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv", type=Path, default=Path("sites_das_prefeituras_brasileiras.csv")
    )
    parser.add_argument("--db", type=Path, default=Path("data/rossio.duckdb"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-sites", type=int, default=1000)
    parser.add_argument("--seconds", type=float, default=1200)
    parser.add_argument("--publish-only", action="store_true")
    args = parser.parse_args()
    if args.publish_only:
        ok = publish_archive(
            args.output,
            "psi_brazilian_city_audits",
            os.getenv("GITHUB_RUN_ID", args.output.name),
        )
    else:
        receipt = asyncio.run(
            collect(
                args.csv,
                args.db,
                args.output,
                max_sites=args.max_sites,
                seconds=args.seconds,
            )
        )
        seal(args.output)
        ok = receipt["successful"] > 0 and receipt["status"] in {
            "complete",
            "site_budget",
            "time_budget",
        }
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
