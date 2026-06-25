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
    init_db.py             # Cria schemas/tabelas (camara, senado, portal, stats)
    import_data.py         # Importa JSONs cacheados de backend/data/
    stats_refresh.py       # Atualiza materialized views em background
    scraper/               # Scrapers que buscam dados das APIs oficiais
      config.py            # URLs das APIs, rate limits, DATA_DIR
      fetcher.py           # Requisições paginadas com retry
      worker.py            # Loop principal dos scrapers em background
      lifecycle.py         # Gerenciamento de threads (start/stop)
      rate_limiter.py      # Token-bucket por API
      verification.py      # Controle de itens já processados
      camara/              # Scrapers da Câmara (deputados, despesas, proposições, votações, etc.)
      senado/              # Scrapers do Senado (senadores, despesas, processos)
      portal/              # Scrapers do Portal da Transparência (emendas)
frontend/
  src/
    pages/                 # Páginas Vue (Home, Analise, Metodologia, Camara, Senado)
    components/            # Componentes UI (shadcn-vue + custom)
      layout/              # AppHeader, AppFooter
      ui/                  # BaseBadge, BaseButton, BaseCard, BaseSkeleton, etc.
      camara/              # Componentes específicos da Câmara
      senado/              # Componentes específicos do Senado
    stores/                # Pinia stores (camara.ts, senado.ts, loading.ts)
    services/api.ts        # Configuração da URL da API (VITE_API_URL)
    router/                # Vue Router
    lib/foto.ts            # Helper para URLs de fotos dos parlamentares
    utils/format.ts        # Formatação de moeda (R$ Bi/Mi/mil)
    assets/styles/         # CSS global (Tailwind)
```

## Endpoints

A documentação completa está em [README_API.md](README_API.md). O FastAPI também gera Swagger automático em `http://localhost:8000/docs`.

**Câmara:** `/api/camara/legislaturas`, `/api/camara/maior-legislatura`, `/api/camara/resumo-principal`, `/api/camara/{legislatura}/lista`, `/api/camara/{legislatura}/estatisticas`, `/api/camara/{legislatura}/{deputado_id}`, `/api/camara/{legislatura}/{deputado_id}/despesas`, `/api/camara/{legislatura}/{deputado_id}/emendas`, `/api/camara/{legislatura}/comparar`, `/api/camara/{legislatura}/despesas/evolucao`, `/api/camara/{legislatura}/despesas/estatisticas`, `/api/camara/{legislatura}/empresas/estatisticas`, `/api/camara/{legislatura}/emendas`, `/api/camara/{legislatura}/emendas/resumo`, `/api/camara/{legislatura}/proposicoes`, `/api/camara/{legislatura}/proposicoes/{id}/votos`.

**Senado:** `/api/senado/legislaturas`, `/api/senado/maior-legislatura`, `/api/senado/resumo-principal`, `/api/senado/{legislatura}/lista`, `/api/senado/{legislatura}/estatisticas`, `/api/senado/{legislatura}/{senador_codigo}`, `/api/senado/{legislatura}/{senador_codigo}/despesas`, `/api/senado/{legislatura}/{senador_codigo}/emendas/lista`, `/api/senado/{legislatura}/comparar`, `/api/senado/{legislatura}/despesas/evolucao`, `/api/senado/{legislatura}/despesas/estatisticas`, `/api/senado/{legislatura}/empresas/estatisticas`, `/api/senado/{legislatura}/emendas`, `/api/senado/{legislatura}/emendas/resumo`, `/api/senado/{legislatura}/materia/listar`, `/api/senado/{legislatura}/materia/votacao`.

**Outros:** `/health`, `/api/fotos/{casa}/{id}.{ext}` (fotos locais), `/api/scraping-status`, `/api/cache-stats`, `/api/cache-invalidate` (POST), `/api/portal/emendas`, `/api/portal/emendas/resumo`.

## Banco de dados

Quatro schemas no PostgreSQL:

| Schema    | Conteúdo                                          |
|-----------|---------------------------------------------------|
| `camara`  | Deputados, mandatos, despesas, proposições, votos  |
| `senado`  | Senadores, mandatos, despesas, matérias, autorias  |
| `portal`  | Emendas parlamentares do Portal da Transparência   |
| `stats`   | Materialized views com agregações pré-calculadas   |

O schema `stats` contém materialized views (ex: `camara_despesas_totais`, `camara_despesas_categorias`, `camara_empresas_ranking`) que evitam queries pesadas com JOIN+SUM+GROUP BY em milhões de linhas a cada requisição. As views são atualizadas em background pelo `scripts/stats_refresh.py` a cada `STATS_REFRESH_MINUTES` minutos (padrão: 1). Todas as views incluem uma linha de totais com `legislatura_id = 0` via `GROUP BY GROUPING SETS`, permitindo queries uniformes com `WHERE legislatura_id = %s`.

As tabelas são criadas automaticamente pelo `scripts/init_db.py` (executado na inicialização). Migrações de colunas são feitas via blocos `DO $$` inline — não há framework de migração. As materialized views do schema `stats` também são criadas pelo `init_db.py` (primeira execução leva ~45s).

## Fluxo de dados

1. O backend inicia e roda `init_db.py` para garantir que as tabelas existem.
2. Em seguida, `import_data.py` lê arquivos JSON cacheados em `backend/data/` (gitignorado) e popula o banco.
3. Scrapers em background começam a buscar dados novos das APIs oficiais:
   - Câmara: `dadosabertos.camara.leg.br`
   - Senado: `legis.senado.leg.br` e `adm.senado.gov.br`
   - Portal da Transparência: `api.portaldatransparencia.gov.br`

Os scrapers rodam continuamente com rate limits específicos (Câmara 10 req/s, Senado Legis 5 req/s, Senado ADM 1 req/s, Portal 5 req/s). Itens com falha vão para `backend/data/failed/` e, após 3+ tentativas, são registrados em `needs_review.json`.

### Dados cacheados (`backend/data/`)

O diretório `backend/data/` é gitignorado e contém:

```
data/
  deputados.json              # Lista base de deputados (download inicial)
  senadores.json              # Lista base de senadores (download inicial)
  failed/                     # Requisições que falharam (retry system)
  needs_review.json           # Itens com 3+ falhas
  fotos/camara/               # Fotos dos deputados baixadas localmente
  fotos/senado/               # Fotos dos senadores baixadas localmente
  camara/
    despesas/{dep_id}/{leg}/  # JSONs paginados de despesas
    proposicoes/{ano}/        # JSONs de proposições
    deputados/{id}/           # Detalhes e histórico de deputados
  senado/
    despesas/{ano}/           # JSONs de despesas CEAPS
    processos/{ano}/          # Matérias legislativas
  portal/
    emendas/{ano}/            # JSONs de emendas do Portal
```

## Variáveis de ambiente

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

O `.env` na raiz do projeto contém `API_KEY` (Portal da Transparência) — usado pelo Docker Compose.

**Variáveis adicionais (opcionais):**

| Variável               | Descrição                                      | Padrão |
|------------------------|------------------------------------------------|--------|
| `STATS_REFRESH_MINUTES`| Intervalo de refresh das materialized views    | `1`    |
| `VITE_API_URL`         | URL do backend (frontend)                      | `http://127.0.0.1:8000` |

## Troubleshooting

- **Erro de conexão ao banco**: verifique se o PostgreSQL está rodando e o `.env` está correto.
- **CORS no frontend**: o backend só permite `localhost:5173` e `127.0.0.1:5173`. Se estiver rodando em outra porta, ajuste o `origins` em `main.py`.
- **`ModuleNotFoundError`**: ative o venv e reinstale as dependências (`pip install -r requirements.txt`).
- **Acessar o banco diretamente**: `docker exec database psql -U postgres -d fiscaliza_db -c "SELECT ..."` (ou `\dt camara.*` para listar tabelas).
- **Primeira execução lenta**: a criação inicial das materialized views leva ~45s; durante scraping, o frontend faz polling de 15s e exibe banner de carregamento.
- **Dados desatualizados**: as materialized views são atualizadas a cada `STATS_REFRESH_MINUTES` minutos. Para forçar refresh: `POST /api/cache-invalidate`.
