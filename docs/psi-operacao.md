# Coleta PSI: diagnóstico e retomada controlada

Auditoria em 26/10/2026, sobre `main` em `b56471dc6bbf12b84a05d6836236e79cb40cba7d`.
Nenhuma coleta real foi iniciada nesta investigação; credenciais, cobrança e
agendamentos externos não foram alterados. Esta mudança só produz efeito após merge.

## O que foi efetivamente preservado

- A última observação com métricas encontrada em Git é de **30/06/2025,
  03:38:17.540 UTC**: `http://simoes.pi.gov.br`, performance 0,66,
  acessibilidade 0,92, SEO 0,92 e boas práticas 0,83. Foi incorporada pelo
  [commit 299d956](https://github.com/franklinbaldo/rossio/commit/299d95604cadeedd370cdde00e4eac88288e3d6a).
  Isso comprova um resultado persistido; os logs antigos não permitem certificar
  a completude ou o sucesso integral daquela execução.
- `data/psi-results.json`: 2.984 registros, 2.926 URLs distintas, timestamps de
  04/06/2025 a 30/06/2025; 2.982 registros têm performance não nula. CSV e
  `psi_processing_state.json` também estão versionados. O histórico de commits
  preserva versões anteriores desses arquivos, não apenas o snapshot atual.
  Esses dados legados não são automaticamente convertidos em auditorias
  mobile/desktop completas do novo esquema.
- `docs/data/summary.json`, gerado em **23/01/2026 às 10:17 UTC**, contém
  `total_audits=0`. Ranking e quarentena estão vazios. A execução
  [21282646645](https://github.com/franklinbaldo/rossio/actions/runs/21282646645)
  foi marcada como sucesso, mas o commit `eeed930` a descreve como coleta com
  erros e não contém novas métricas. Seus logs já retornam HTTP 410.
- Nas duas páginas consultadas de runs (184 runs totais, de todos os workflows),
  havia 74 runs PSI: 59 canceladas, 13 falhas, uma marcada como sucesso e uma
  em andamento. Isso descreve o histórico **disponível na consulta**, não todos
  os runs desde 2019.
- Em [25/10/2026, run 40175532623](https://github.com/franklinbaldo/rossio/actions/runs/40175532623),
  a API retornava `400: API key not valid. Please pass a valid API key.`.
  O progresso passou de 1.600 sites, todos com erro, antes do timeout de duas
  horas. O cache restaurado tinha apenas **288 bytes**. O processo escritor
  continuava vivo durante as etapas `always()`: exportação/estatísticas/
  quarentena falharam com bloqueio do DuckDB. O commit informou nenhuma alteração.
  A implementação anterior salvava o banco só em cache, sem seu WAL, e os
  artefatos não incluíam o banco. Não há evidência de uma série Python válida
  recuperável nesse cache; ele deve ser tratado somente como tentativa de recuperação.
- O artefato [12595615459](https://github.com/franklinbaldo/rossio/actions/runs/40175532623/artifacts/12595615459)
  estava disponível: 14.988 bytes, expiração em **24/11/2026**,
  SHA-256 `be96a3d2cb51b969eacf2f17921e0f5cb8e020c1b6d23fbd88602e6abc19147d`.
  Os logs informam dez arquivos enviados. O ZIP não foi baixado por esta
  investigação; seu conteúdo exato não foi certificado. Pela configuração,
  inclui saídas/quarentena/painel/log, sem DuckDB; o sucesso do upload não
  comprova métricas novas.
- O run [40293340909](https://github.com/franklinbaldo/rossio/actions/runs/40293340909),
  de 26/10, aparecia em andamento na etapa de coleta. Não foi iniciado nem
  cancelado por esta investigação e não foi contado como resultado válido.

## Internet Archive

O job de validação de 25/10 confirmou ausência de `IA_ACCESS_KEY` e
`IA_SECRET_KEY`; o upload foi pulado. A consulta pública a
`https://archive.org/metadata/psi_brazilian_city_audits`, via Jatobá, retornou
`{}`. Portanto, **não foi possível confirmar arquivos públicos preservados
nesse item**. Isso não prova que nunca existiram uploads nem exclui outros itens.
Nenhuma chave foi criada, lida ou modificada nesta investigação.

A nova rotina mantém publicação opcional no mesmo item e envia um bundle
com nome por run, evitando substituir o snapshot anterior. Confere respostas
HTTP, marca falhas e mantém uma cópia independente em GitHub Releases. Sem
chaves, registra `skipped_missing_credentials`, nunca “publicado”. O manifesto
no bundle remoto registra submissão; o recibo local final registra o resultado
HTTP. A confirmação de disponibilidade/checksum remoto é uma etapa operacional
posterior, não alegada apenas com um HTTP de upload bem-sucedido.

## Comparação de infraestrutura

O repositório é **público** e usa `ubuntu-latest`, um runner padrão. Seus minutos
são gratuitos e não consomem a franquia de minutos dos repositórios privados.
O aviso dos 2.000 minutos não justifica, por si só, migrar o Rossio.
Armazenamento de cache/artefatos tem regras próprias: não confundir gratuidade
compute com retenção ilimitada de artefatos.

| Alternativa | Compute e limites | Preservação e custo operacional | Decisão |
| --- | --- | --- | --- |
| Actions diário anterior | Até 3.600 minutos/mês num mês de 30 dias, como teto nominal, não medição faturada | Repetia chave inválida; cache volátil e banco sem WAL | Substituir |
| Actions semanal limitado | Até 20 minutos de coleta por semana: 80–100/mês, mais preparação/exportação/publicação | Releases por execução; artefato de recuperação de sete dias; sem nova identidade de serviço | Escolhida, com agenda opt-in após reparo da chave |
| Cloud Build `e2-standard-2` | 2.500 minutos gratuitos/mês por conta de faturamento; excedente US$ 0,006/min, conforme tabela consultada | Compartilha franquia com outros projetos; GCS, rede, logs, agendamento e integração de segredos precisam ser avaliados | Sem vantagem de compute sobre Actions público; não provisionar |
| Cloud Run Jobs | Pode executar o mesmo coletor Python com orçamento e storage externo | Exige configurar imagem, persistência, IAM, segredos, scheduler e avaliar cobrança | Alternativa futura se houver necessidade independente do Actions |
| VM Jatobá | VM pequena; política de uso como plano de controle | Não hospedar DuckDB/coleta nacional; pode disparar execução externa | Não escolhida como executor |

Fontes oficiais consultadas em 26/10/2026:
[GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions),
[runners padrão](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[Cloud Build pricing](https://cloud.google.com/build/pricing).
Não foi validado saldo livre de Cloud Build, trigger Rossio ou uma integração
operacional disponível para este repositório. A tentativa de consulta pela VM
não demonstrou acesso autenticado utilizável; não se presume infraestrutura pronta.

## Política implementada

- A agenda diária passa a semanal, segunda-feira às **03:17 UTC** (domingo
  23:17 em Porto Velho). Só coleta se a variável `PSI_SCHEDULE_ENABLED=true`.
  Sem essa opção, o cron não faz checkout nem instala dependências. Não há
  commits artificiais para contornar a desativação por inatividade.
- `workflow_dispatch` permanece disponível para validação curta. O teto é de
  1.000 sites/1.200 segundos. Visita primeiro os sites com tentativa mais antiga
  no banco, em ordem determinística; não reinicia sempre pelos mesmos municípios.
  O orçamento de tempo cancela e aguarda as tarefas de rede; gravações já
  iniciadas terminam antes de fechar o banco. Exportação/publicação têm margem
  no timeout global de 35 minutos.
- A frequência semanal é uma proposta operacional conservadora para retomada,
  **não uma série nacional semanal completa**. Mil sites por semana exigiriam
  pelo menos seis rodadas para cobrir o cadastro, e a latência pode ampliar esse
  prazo. O manifesto registra tentativas, sucessos, falhas, população elegível e
  motivo de parada para dimensionar cobertura antes de aumentar orçamento.
  Não há evidência atual que justifique auditoria nacional diária.
- Não repete erros HTTP 4xx; 401/403/429 ou chave inválida interrompem o lote sem
  atribuir uma falha da credencial ao município. Três erros locais consecutivos
  interrompem a rodada. Falhas de transporte/5xx mantêm retries limitados.
- Fecha o escritor antes de copiar o DuckDB; banco completo, respostas novas em
  JSONL, exports JSON/Parquet, painel/quarentena quando produzidos, CSV de entrada,
  cópia dos três arquivos legados, manifesto e SHA-256 vão no bundle. Os JSONs
  resumidos não substituem a história completa do banco.
- Cada run/attempt gera uma Release própria, sem apagar anteriores. Restauração
  usa a Release mais recente com prefixo `psi-state-`, verifica checksum e falha
  se download/verificação falhar. Só na ausência de Releases tenta o cache antigo
  com o formato original. Cache não é o arquivo histórico nem recebe novos bancos.
- Falhas não atualizam painel/quarentena em Git. Rodadas válidas propõem PR em
  branch única, sem force-push nem auto-merge. Um único escritor roda por vez.
- O arquivo `uv.lock` passa a ser versionado; `uv sync --frozen` e o SHA do código
  identificam o ambiente. O comando é portátil, sem dependência do runner Actions.

## Retomada e reprodução

Após merge, a coleta automática fica suspensa pela variável opt-in. Para retomar:

1. O operador deve corrigir/validar `PSI_KEY` no provedor. Esta PR não altera a chave.
2. Fazer um dispatch de **um site e até 120 segundos**. Verificar o manifesto e
   métricas mobile/desktop; ausência de chave, status de erro ou snapshot vazio
   não autorizam alegar continuidade.
3. Conferir uma Release, download/checksum e abertura do DuckDB. Verificar também
   a rota de recuperação e a PR do painel.
4. Se desejado, configurar as credenciais IA pelo processo autorizado e verificar
   a presença e o checksum do bundle no item público. Sem isso, a cópia no IA
   permanece pendente, mesmo que Releases funcione.
5. Só então habilitar `PSI_SCHEDULE_ENABLED=true`. Se o GitHub tiver desativado
   o workflow por inatividade, reativá-lo explicitamente após o reparo.

Reprodução do ambiente/testes sem PSI nem Internet Archive:

```bash
uv sync --frozen --extra dev
uv run --frozen pytest tests/test_scheduled.py -q
```

Execução intencional e limitada (requer chave fornecida pelo operador):

```bash
uv run --frozen python -m rossio.scheduled \
  --csv sites_das_prefeituras_brasileiras.csv \
  --db data/rossio.duckdb --output data/runs/ensaio-unico \
  --max-sites 1 --seconds 120
```

O diretório deve ser novo. Para verificar um snapshot, extrair o bundle em
um diretório de recuperação e executar `sha256sum -c SHA256SUMS` dentro do
run. Não apagar o banco anterior. Para republicar um bundle após falha IA,
`--publish-only --output <diretorio-do-run>` não chama a API PSI.

Os dados são publicados sob CC BY 4.0 e o código sob MIT, conforme a licença
existente. Não registrar chaves em comandos versionados ou recibos.

## Verificação desta PR

- Sete regressões offline novas cobrem credencial inválida, limite de sites,
  preservação de histórico após falha subsequente, cancelamento, falhas locais,
  ausência/falha/sucesso HTTP no IA e zero retries em HTTP 400.
- Nova rotina, CLI e armazenamento: **39 testes aprovados** no ambiente travado.
  Ruff dos arquivos alterados, MyPy da rotina nova, parse YAML e MkDocs estrito
  também passaram.
- A suíte ampla inicial teve 65 aprovações e quatro falhas. As quatro foram
  reproduzidas em checkout separado da `main`, com as mesmas dependências.
  Uma é incompatibilidade Ibis 12/DuckDB 2 (`fetch_arrow_table` removido); esta
  PR restringe DuckDB a `<2` e trava 1.5.6, verificando novamente todos os testes
  de armazenamento. As outras três são problemas anteriores nos mocks: respostas
  insuficientes no lote misto, limite de um segundo incompatível com o throttler
  e rotas de teste sobrescritas no cenário de erro parcial. Não foram ocultadas
  nem convertidas em sucesso; permanecem fora do escopo funcional desta correção.
- O lint completo também aponta F402 anterior em `storage.py:740`; há uma PR
  existente sobre a política do Ruff. Os arquivos alterados passam no lint.
- O teste antigo de CSV foi corrigido para simular `BatchProcessor.process`;
  antes chamava o coletor real com rate limit 0,1 que era truncado para zero.
  Não houve coleta extensa nem validação com a chave real.
