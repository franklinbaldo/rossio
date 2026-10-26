"""Offline regressions for runaway collection and history preservation."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import duckdb
import httpx
import pytest

from rossio.collector import PageSpeedCollector
from rossio.models import SiteAudit
from rossio.scheduled import collect, ordered_urls, publish_archive, seal
from rossio.storage import DuckDBStorage


@pytest.fixture(autouse=True)
def offline_proxy_environment(monkeypatch):
    # The executor has a SOCKS proxy; all PSI requests here are mocked.
    for name in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.asyncio
async def test_invalid_key_stops_and_does_not_quarantine(tmp_path, monkeypatch):
    monkeypatch.setenv("PSI_KEY", "fake-test-credential")
    csv = tmp_path / "sites.csv"
    csv.write_text("url\nhttps://example.com\nhttps://example.org\n")
    output = tmp_path / "run"
    audit = SiteAudit(
        url="https://example.com", error_message="HTTP 400: API key not valid."
    )
    with patch.object(
        PageSpeedCollector, "audit_site", AsyncMock(return_value=audit)
    ) as call:
        receipt = await collect(csv, tmp_path / "db.duckdb", output)
    assert call.await_count == 1
    assert receipt["status"] == "credential_or_quota_failure"
    assert receipt["successful"] == 0
    assert not (output / "dashboard").exists()
    # Reopening the copied DB proves the writer was closed/checkpointed.
    with duckdb.connect(str(output / "rossio.duckdb")) as db:
        assert db.execute("SELECT COUNT(*) FROM audits").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_site_budget_preserves_raw_data_and_rotates(tmp_path, monkeypatch):
    monkeypatch.setenv("PSI_KEY", "fake-test-credential")
    csv = tmp_path / "sites.csv"
    csv.write_text("url\nhttps://example.com\nhttps://example.org\n")
    # Use a real PSI-shaped fixture from the test suite; no network.
    from rossio.models import PageSpeedInsightsResult
    from tests.conftest import create_psi_response

    response = PageSpeedInsightsResult(**create_psi_response("https://example.com"))
    audit = SiteAudit(
        url="https://example.com", mobile_result=response, desktop_result=response
    )
    output = tmp_path / "run"
    with patch.object(
        PageSpeedCollector, "audit_site", AsyncMock(return_value=audit)
    ) as call:
        receipt = await collect(csv, tmp_path / "db.duckdb", output, max_sites=1)
    assert call.await_count == 1
    assert receipt["status"] == "site_budget"
    assert receipt["successful"] == 1, receipt
    assert (output / "dashboard/summary.json").exists(), receipt
    assert json.loads((output / "audits.jsonl").read_text())["mobile_result"]
    storage = DuckDBStorage(str(tmp_path / "db.duckdb"))
    await storage.initialize()
    try:
        assert ordered_urls(csv, storage)[0] == "https://example.org"
    finally:
        await storage.close()
    seal(output)
    assert "rossio.duckdb" in (output / "SHA256SUMS").read_text()
    # A subsequent credential failure must retain earlier valid history.
    broken = SiteAudit(url="https://example.org", error_message="HTTP 403: denied")
    with patch.object(PageSpeedCollector, "audit_site", AsyncMock(return_value=broken)):
        second = tmp_path / "second-run"
        await collect(csv, tmp_path / "db.duckdb", second)
    with duckdb.connect(str(second / "rossio.duckdb")) as db:
        assert db.execute("SELECT COUNT(*) FROM audits").fetchone()[0] == 1
    assert not (second / "dashboard").exists()


@pytest.mark.asyncio
async def test_timeout_waits_for_cancellation_before_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("PSI_KEY", "fake-test-credential")
    csv = tmp_path / "sites.csv"
    csv.write_text("url\nhttps://example.com\n")
    cancelled = asyncio.Event()

    async def wait(*args):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    with patch.object(PageSpeedCollector, "audit_site", wait):
        receipt = await collect(
            csv, tmp_path / "db.duckdb", tmp_path / "run", seconds=0.1
        )
    assert cancelled.is_set()
    assert receipt["status"] == "time_budget"
    assert (tmp_path / "run/rossio.duckdb").exists()


@pytest.mark.asyncio
async def test_failures_stop_at_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("PSI_KEY", "fake-test-credential")
    csv = tmp_path / "sites.csv"
    csv.write_text("url\n" + "\n".join(f"https://example{i}.com" for i in range(10)))
    audit = SiteAudit(url="https://example.com", error_message="HTTP 404: not found")
    with patch.object(
        PageSpeedCollector, "audit_site", AsyncMock(return_value=audit)
    ) as call:
        receipt = await collect(csv, tmp_path / "db.duckdb", tmp_path / "run")
    assert call.await_count == 3
    assert receipt["status"] == "consecutive_failures"
    assert receipt["failed"] == 3


@pytest.mark.asyncio
async def test_400_is_not_retried_and_no_sibling_task_leaks(respx_mock):
    route = respx_mock.get(
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    ).mock(
        return_value=httpx.Response(
            400, json={"error": {"message": "API key not valid."}}
        )
    )
    async with PageSpeedCollector(
        "fake-test-credential", requests_per_second=10
    ) as collector:
        result = await collector.audit_site("https://example.com")
    assert route.call_count == 2  # one request per strategy, zero retries
    assert "API key not valid" in result.error_message


def test_archive_missing_keys_is_explicit_and_failure_is_not_success(
    tmp_path, monkeypatch
):
    output = tmp_path / "run"
    output.mkdir()
    (output / "manifest.json").write_text("{}")
    monkeypatch.delenv("IA_ACCESS_KEY", raising=False)
    monkeypatch.delenv("IA_SECRET_KEY", raising=False)
    assert publish_archive(output, "test-item", "test-run")
    assert (
        json.loads((output / "manifest.json").read_text())["internet_archive"]
        == "skipped_missing_credentials"
    )
    monkeypatch.setenv("IA_ACCESS_KEY", "fake")
    monkeypatch.setenv("IA_SECRET_KEY", "fake")
    with patch("internetarchive.upload", return_value=[httpx.Response(503)]):
        assert not publish_archive(output, "test-item", "test-run")
    assert (
        json.loads((output / "manifest.json").read_text())["internet_archive"]
        == "upload_failed"
    )


def test_archive_http_success_has_explicit_receipt(tmp_path, monkeypatch):
    output = tmp_path / "run"
    output.mkdir()
    (output / "manifest.json").write_text("{}")
    monkeypatch.setenv("IA_ACCESS_KEY", "fake")
    monkeypatch.setenv("IA_SECRET_KEY", "fake")
    with patch("internetarchive.upload", return_value=[httpx.Response(200)]) as upload:
        assert publish_archive(output, "test-item", "run-123")
    assert next(iter(upload.call_args.kwargs["files"])) == "runs/run-123/run.tar.gz"
    assert (
        json.loads((output / "manifest.json").read_text())["internet_archive"]
        == "uploaded_http_success"
    )
