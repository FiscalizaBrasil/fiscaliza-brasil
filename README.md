# Fiscaliza Brasil

Plataforma de transparência de dados do Congresso Nacional: Câmara dos Deputados e Senado Federal.

Backend em Python (FastAPI) + frontend em TypeScript (Vue 3) + PostgreSQL.

## Como executar

### Com Docker (recomendado)

```bash
docker compose up -d
```

Isso sobe o PostgreSQL, executa `init_db.py` (cria as tabelas), inicia o backend na porta `8000` e o frontend na `5173`.

A primeira execução pode demorar alguns minutos: o backend baixa fotos, importa dados cacheados e inicia os scrapers em background.

### Sem Docker (desenvolvimento local)

**Backend:**

```bash
cd backend
pip install -r ../requirements.txt
python scripts/init_db.py
python main.py
```

**Frontend:**

```bash
cd frontend
pnpm install
pnpm dev
```

### Variáveis de ambiente

O `db.py` usa `load_dotenv()` e lê o `.env` do diretório de trabalho atual.

- **Com Docker**: o compose injeta `DATABASE_URL` diretamente.
- **Local**: crie um `.env` dentro de `backend/` com:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=fiscaliza_db
DB_USER=postgres
DB_PASSWORD=postgres
```

O `.env` na raiz do projeto contém apenas `API_KEY` (Portal da Transparência) — usado pelo Docker Compose.

## Estrutura

```
backend/
  main.py                  # FastAPI app, CORS, lifespan (scrapers)
  api/
    camara/router.py       # Endpoints da Câmara (/api/camara)
    senado/router.py       # Endpoints do Senado (/api/senado)
    portal/router.py       # Emendas do Portal da Transparência (/api/portal)
  database/
    db.py                  # Pool de conexões PostgreSQL (ThreadedConnectionPool)
    cache.py               # Cache TTL em memória
    utils.py               # Funções auxiliares (legislatura, fotos)
  scripts/
    init_db.py             # Cria schemas/tabelas (camara, senado, portal)
    import_data.py         # Importa JSONs cacheados de backend/data/
    scraper/               # Scrapers que buscam dados das APIs oficiais
frontend/
  src/
    pages/                 # Páginas Vue (Home, Camara, Senado, etc.)
    stores/                # Pinia stores (camara.ts, senado.ts)
    services/api.ts        # Configuração da URL da API
    router/                # Vue Router
```

## Endpoints

A documentação completa está em [README_API.md](README_API.md). O FastAPI também gera Swagger automático em `http://localhost:8000/docs`.

**Câmara:** `/api/camara/{legislatura}/lista`, `/api/camara/{legislatura}/estatisticas`, `/api/camara/{id}`, `/api/camara/comparar`, etc.

**Senado:** `/api/senado/{legislatura}/lista`, `/api/senado/{legislatura}/estatisticas`, `/api/senado/{codigo}`, `/api/senado/comparar`, etc.

**Outros:** `/api/scraping-status`, `/api/cache-stats`, `/api/cache-invalidate`.

## Banco de dados

Três schemas no PostgreSQL:

| Schema    | Conteúdo                                          |
|-----------|---------------------------------------------------|
| `camara`  | Deputados, mandatos, despesas, proposições, votos  |
| `senado`  | Senadores, mandatos, despesas, matérias, autorias  |
| `portal`  | Emendas parlamentares do Portal da Transparência   |

As tabelas são criadas automaticamente pelo `scripts/init_db.py` (executado na inicialização). Migrações de colunas são feitas via blocos `DO $$` inline — não há framework de migração.

## Fluxo de dados

1. O backend inicia e roda `init_db.py` para garantir que as tabelas existem.
2. Em seguida, `import_data.py` lê arquivos JSON cacheados em `backend/data/` (gitignorado) e popula o banco.
3. Scrapers em background começam a buscar dados novos das APIs oficiais:
   - Câmara: `dadosabertos.camara.leg.br`
   - Senado: `legis.senado.leg.br` e `adm.senado.gov.br`
   - Portal da Transparência: `api.portaldatransparencia.gov.br`

Os scrapers rodam continuamente com rate limits específicos (Câmara 10 req/s, Senado Legis 5 req/s, Senado ADM 1 req/s, Portal 5 req/s).

## Troubleshooting

- **Erro de conexão ao banco**: verifique se o PostgreSQL está rodando e o `.env` está correto.
- **CORS no frontend**: o backend só permite `localhost:5173`. Verifique se o frontend está rodando nessa porta.
- **`ModuleNotFoundError`**: ative o venv e reinstale as dependências (`pip install -r requirements.txt`).
