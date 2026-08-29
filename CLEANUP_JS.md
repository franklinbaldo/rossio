# 🧹 Limpeza de Arquivos JavaScript

Este documento lista os arquivos JavaScript e Node.js que devem ser removidos durante a migração para Python.

## ❌ Arquivos a serem removidos

### Arquivos JavaScript principais
- `collector/collect-psi.js` - Coletor Node.js (substituído por `collector.py`)
- `package.json` - Dependências Node.js
- `package-lock.json` - Lock file do npm
- `.nvmrc` - Versão do Node.js

### Arquivos de frontend estático
- `index.html` - Interface web estática (será substituída por MkDocs + DuckDB-wasm)
- Qualquer arquivo `.js` na raiz do projeto

### Diretórios
- `node_modules/` - Dependências Node.js instaladas
- `collector/` - Diretório do coletor Node.js (se vazio após remoção do .js)

## ✅ Arquivos que permanecem

### Configuração Python
- `pyproject.toml` - Configuração Python/UV
- `src/rossio/` - Código Python
- `tests/` - Testes Python

### Documentação
- `docs/` - Documentação MkDocs
- `mkdocs.yml` - Configuração MkDocs
- `README.md` - Documentação principal

### Dados
- `sites_das_prefeituras_brasileiras.csv` - Lista de URLs
- `data/` - Banco de dados DuckDB

## 🚀 Como executar a limpeza

### Automática (recomendado)
```bash
# Remover apenas arquivos JavaScript
uv run rossio cleanup --remove-js --confirm

# Remover tudo (JS + node_modules)
uv run rossio cleanup --remove-js --remove-node-modules --confirm
```

### Manual
```bash
# Remover arquivos JavaScript
rm -f collector/collect-psi.js
rm -f package.json package-lock.json .nvmrc
rm -f index.html

# Remover node_modules
rm -rf node_modules/

# Remover diretório collector se vazio
rmdir collector/ 2>/dev/null || true
```

## 📋 Checklist pós-limpeza

- [ ] Arquivos JavaScript removidos
- [ ] `node_modules/` removido
- [ ] `package.json` removido
- [ ] Funcionalidade Python testada
- [ ] CLI funcionando: `uv run rossio --help`
- [ ] Testes passando: `uv run pytest`
- [ ] Documentação servindo: `uv run mkdocs serve`

## 🔄 Equivalências

| Antes (Node.js) | Agora (Python) |
|-----------------|----------------|
| `collector/collect-psi.js` | `src/rossio/collector.py` |
| `npm install` | `uv sync` |
| `node collector/collect-psi.js` | `uv run rossio batch` |
| `package.json` | `pyproject.toml` |
| HTML estático | MkDocs + DuckDB-wasm (futuro) |

## ⚠️ Backup

Antes de executar a limpeza, considere fazer backup:

```bash
# Backup dos arquivos JavaScript
mkdir -p backup/js-files
cp collector/collect-psi.js backup/js-files/ 2>/dev/null || true
cp package.json backup/js-files/ 2>/dev/null || true
cp index.html backup/js-files/ 2>/dev/null || true

# Criar commit antes da limpeza
git add .
git commit -m "backup: arquivos JavaScript antes da migração"
```