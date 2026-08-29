# Interface de Linha de Comando (CLI)

O Sites Prefeituras oferece uma CLI completa para coleta, analise e exportacao de dados.

## Instalacao

```bash
# Instalar dependencias
uv sync

# Verificar instalacao
uv run rossio --help
```

## Comandos Disponiveis

### audit

Audita um site individual.

```bash
uv run rossio audit <URL> [OPCOES]
```

**Opcoes:**
- `--output`: Formato de saida (`console` ou `json`)
- `--no-save-to-db`: Nao salvar no banco de dados

**Exemplo:**
```bash
uv run rossio audit https://www.prefeitura.sp.gov.br --output json
```

---

### batch

Executa auditoria em lote a partir de um arquivo CSV.

```bash
uv run rossio batch <CSV_FILE> [OPCOES]
```

**Opcoes:**
- `--output-dir`: Diretorio de saida (default: `./output`)
- `--max-concurrent`: Maximo de requisicoes simultaneas (default: 10)
- `--requests-per-second`: Taxa de requisicoes por segundo (default: 3.5, max: 4.0)
- `--url-column`: Nome da coluna com URLs (default: `url`)
- `--skip-recent`: Pular sites auditados nas ultimas N horas (default: 24, 0=desativado)
- `--export-parquet / --no-export-parquet`: Exportar para Parquet
- `--export-json / --no-export-json`: Exportar para JSON

**Exemplo:**
```bash
# Coleta completa
uv run rossio batch sites_das_prefeituras_brasileiras.csv \
  --max-concurrent 10 \
  --requests-per-second 3.5

# Coleta incremental (pula sites recentes)
uv run rossio batch sites_das_prefeituras_brasileiras.csv \
  --skip-recent 24
```

---

### stats

Mostra estatisticas dos dados coletados.

```bash
uv run rossio stats [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados

**Exemplo:**
```bash
uv run rossio stats --db-path ./data/rossio.duckdb
```

---

### metrics

Mostra metricas agregadas das auditorias.

```bash
uv run rossio metrics [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados
- `--by-state`: Agrupar metricas por estado
- `--worst N`: Mostrar N piores sites em performance
- `--best N`: Mostrar N melhores sites em acessibilidade
- `--export FILE`: Exportar metricas para arquivo JSON

**Exemplos:**
```bash
# Metricas gerais
uv run rossio metrics

# Por estado
uv run rossio metrics --by-state

# Top 20 piores em performance
uv run rossio metrics --worst 20

# Top 20 melhores em acessibilidade
uv run rossio metrics --best 20

# Exportar para JSON
uv run rossio metrics --export metricas.json
```

---

### quarantine

Gerencia sites em quarentena (sites com falhas persistentes).

```bash
uv run rossio quarantine [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados
- `--update`: Atualizar lista de quarentena
- `--min-days N`: Minimo de dias com falha para quarentena (default: 3)
- `--status STATUS`: Filtrar por status
- `--url URL`: URL para operacoes especificas
- `--set-status STATUS`: Definir status de uma URL
- `--remove`: Remover URL da quarentena
- `--export-json FILE`: Exportar para JSON
- `--export-csv FILE`: Exportar para CSV

**Status disponiveis:**
- `quarantined`: Em quarentena (default)
- `investigating`: Em investigacao
- `resolved`: Resolvido
- `wrong_url`: URL incorreta

**Exemplos:**
```bash
# Listar todos em quarentena
uv run rossio quarantine

# Atualizar quarentena (identifica novos sites com falhas)
uv run rossio quarantine --update --min-days 3

# Filtrar por status
uv run rossio quarantine --status investigating

# Alterar status de um site
uv run rossio quarantine --url "https://site.gov.br" --set-status investigating

# Remover da quarentena
uv run rossio quarantine --url "https://site.gov.br" --remove

# Exportar
uv run rossio quarantine --export-json quarantine.json
uv run rossio quarantine --export-csv quarantine.csv
```

---

### export-dashboard

Exporta JSONs estaticos para o dashboard web.

```bash
uv run rossio export-dashboard [OPCOES]
```

**Opcoes:**
- `--db-path`: Caminho do banco de dados
- `--output-dir`: Diretorio de saida (default: `./docs/data`)

**Arquivos gerados:**
- `summary.json` - Metricas agregadas
- `ranking.json` - Ranking completo de sites
- `top50.json` - Melhores 50 sites (acessibilidade)
- `worst50.json` - Piores 50 sites (acessibilidade)
- `by-state.json` - Metricas agrupadas por estado
- `quarantine.json` - Sites em quarentena

**Exemplo:**
```bash
uv run rossio export-dashboard --output-dir docs/data
```

---

### cleanup

Remove arquivos legados (JavaScript/Node.js).

```bash
uv run rossio cleanup [OPCOES]
```

**Opcoes:**
- `--remove-js`: Remove arquivos JavaScript
- `--remove-node-modules`: Remove node_modules
- `--confirm`: Confirma remocao sem perguntar

**Exemplo:**
```bash
uv run rossio cleanup --remove-js --remove-node-modules --confirm
```

---

### serve

Inicia servidor de visualizacao (em desenvolvimento).

```bash
uv run rossio serve [OPCOES]
```

**Nota:** Para visualizacao, use o MkDocs:
```bash
uv run mkdocs serve
```

## Variaveis de Ambiente

| Variavel | Descricao |
|----------|-----------|
| `PAGESPEED_API_KEY` | Chave da API PageSpeed Insights |
| `PSI_KEY` | Alias para PAGESPEED_API_KEY |

Ambas as variaveis sao aceitas para compatibilidade.

## Exemplos de Uso

### Fluxo Completo de Coleta

```bash
# 1. Configurar API key
export PSI_KEY="sua_chave_aqui"

# 2. Executar coleta incremental
uv run rossio batch sites_das_prefeituras_brasileiras.csv \
  --skip-recent 24 \
  --requests-per-second 3.5

# 3. Ver estatisticas
uv run rossio stats

# 4. Atualizar quarentena
uv run rossio quarantine --update

# 5. Exportar para dashboard
uv run rossio export-dashboard

# 6. Visualizar
uv run mkdocs serve
```

### Analise de Dados

```bash
# Ver metricas gerais
uv run rossio metrics

# Ranking por estado
uv run rossio metrics --by-state

# Sites que precisam de atencao
uv run rossio metrics --worst 50

# Sites em quarentena
uv run rossio quarantine
```
