# Fiscaliza Brasil

![Logo do Fiscaliza Brasil](fiscaliza_brasil.svg)

Portal de transparência política que consolida e analisa dados públicos da **Câmara dos Deputados** e do **Senado Federal**: parlamentares, despesas (CEAP/CEAPS), emendas parlamentares, empresas fornecedoras, proposições legislativas e votações nominais.

Projeto de TCC com backend em **Python/FastAPI**, frontend em **Vue 3 + Vite + TypeScript** e banco de dados **PostgreSQL**.

## Sumário

- [Sobre o projeto](#sobre-o-projeto)
- [Funcionalidades](#funcionalidades)
- [Requisitos](#requisitos)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Configuração](#configuração)
- [Execução com Docker Compose](#execução-com-docker-compose)
- [Execução local](#execução-local)
- [Banco de dados](#banco-de-dados)
- [API](#api)
- [Scripts e coleta de dados](#scripts-e-coleta-de-dados)
- [Testes rápidos](#testes-rápidos)
- [Notas](#notas)

## Sobre o projeto

O backend expõe uma API REST com consultas sobre os dados da Câmara e do Senado, usando `psycopg2` com um pool de conexões e SQL direto sobre os schemas `camara`, `senado` e `portal`. O frontend é uma SPA Vue 3 com Pinia para estado, Vue Router para navegação e Tailwind CSS para estilização.

A documentação interativa (Swagger) fica disponível em `http://localhost:8000/docs`. A referência detalhada das rotas está em [`README_API.md`](README_API.md).

## Funcionalidades

- **Início**: totais de deputados/senadores e gastos dos últimos 12 meses.
- **Legislatura**: seletor global (da 57ª à 50ª, mais "todas") que recarrega os dados das páginas.
- **Câmara**: lista de deputados, perfil detalhado, despesas CEAP, emendas, ranking de empresas, projetos legislativos com votações nominais e comparação entre deputados.
- **Senado**: lista de senadores, perfil detalhado, despesas CEAPS, emendas, ranking de empresas, matérias legislativas com votações e comparação entre senadores.
- **Metodologia**: fontes dos dados, explicação das funcionalidades e perguntas frequentes.
- Rotas antigas (`/deputados`, `/despesas`, `/emendas`, `/rankings`) redirecionam para as páginas atuais.

## Requisitos

Forma recomendada:

- Docker e Docker Compose

Para executar sem Docker:

- Python 3.11+
- PostgreSQL 18
- Node.js 22 e npm
- Chave de API do Portal da Transparência (apenas para a coleta de emendas)

As dependências Python estão listadas em `requirements.txt` e as do frontend em `frontend/package.json`.

## Estrutura do repositório

```text
fiscaliza-brasil/
├── backend/
│   ├── main.py                     # FastAPI, CORS, routers e agendador
│   ├── api/
│   │   ├── camara/router.py        # endpoints /api/camara
│   │   └── senado/router.py        # endpoints /api/senado
│   ├── database/db.py              # pool de conexões PostgreSQL
│   ├── scripts/
│   │   ├── esperar_postgres.py     # espera o banco ficar pronto no Docker
│   │   ├── create_indexes.py       # criação de índices
│   │   ├── export_schemas.sh       # exporta dumps dos schemas
│   │   ├── ingest_emendas.py       # coleta emendas (Portal da Transparência)
│   │   ├── ingest_votacoes.py      # coleta votações (Câmara)
│   │   └── update_company_summaries.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/                  # páginas por casa legislativa
│   │   ├── components/             # componentes de layout, home e casa
│   │   ├── stores/                 # Pinia (camara, senado, loading)
│   │   ├── router/index.ts         # rotas e redirecionamentos
│   │   └── services/api.ts         # helper da URL da API
│   ├── public/
│   └── Dockerfile
├── init-db/
│   └── 01-setup-fiscaliza-db.sh    # cria schemas e restaura dumps na primeira inicialização
├── docker-compose.yml              # backend, frontend e postgres
├── requirements.txt
├── README_API.md
├── fiscaliza_brasil.svg
└── README.md
```

## Configuração

Crie um arquivo `.env` na raiz do projeto com a chave usada pelo coletor de emendas:

```dotenv
API_KEY=sua_chave_do_portal_da_transparencia
```

Variáveis utilizadas:

| Variável | Onde é usada | Observação |
| --- | --- | --- |
| `API_KEY` | `backend/scripts/ingest_emendas.py`, `docker-compose.yml` | Obtida no Portal da Transparência; enviada no cabeçalho `chave-api-dados`. |
| `DATABASE_URL` | `backend/database/db.py`, `docker-compose.yml` | DSN completo. No Compose já é definido como `postgresql://postgres:postgres@postgres:5432/fiscaliza_db`. |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | `backend/database/db.py` | Usados se `DATABASE_URL` não existir. Padrões: `localhost`, `5432`, `fiscaliza_db`, `postgres`, `postgres`. |
| `VITE_API_URL` | frontend | URL base da API. Padrão no código: `http://127.0.0.1:8000`. |

Para execução local sem Docker, crie `backend/.env` com:

```dotenv
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fiscaliza_db
```

E, se desejar explicitar a URL no frontend, `frontend/.env`:

```dotenv
VITE_API_URL=http://localhost:8000
```

O backend aceita requisições GET de `http://localhost:5173` e `http://127.0.0.1:5173` (CORS).

## Execução com Docker Compose

Na raiz do projeto:

```powershell
docker compose up --build
```

| Serviço | URL / porta | Descrição |
| --- | --- | --- |
| `backend` | `http://localhost:8000` | API FastAPI; Swagger em `/docs`, health-check em `/health`. |
| `frontend` | `http://localhost:5173` | Servidor de desenvolvimento do Vite. |
| `postgres` | `localhost:5432` | Banco `fiscaliza_db` (usuário/senha `postgres`). |

Para parar os contêineres:

```powershell
docker compose down
```

Para parar e remover também o volume do banco:

```powershell
docker compose down -v
```

Antes da primeira inicialização com volume vazio, os dumps dos schemas devem estar em `init-db/sql-auto/` (veja [Banco de dados](#banco-de-dados)). Sem eles, os schemas são criados, mas as tabelas ficam vazias e a API não terá dados para consultar.

## Execução local

Backend (em `backend/`):

```powershell
Set-Location -Path '.\backend'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r ..\requirements.txt
```

Se a ativação do virtualenv for bloqueada pela política de execução:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Crie `backend/.env` conforme a seção [Configuração](#configuração) e inicie o servidor:

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend (em outra sessão, a partir da raiz):

```powershell
Set-Location -Path '.\frontend'
npm install
npm run dev
```

Para verificar tipos e gerar o build de produção do frontend:

```powershell
npm run build
```

## Banco de dados

O banco `fiscaliza_db` usa três schemas:

- `camara`: deputados, mandatos, despesas, proposições e votações.
- `senado`: parlamentares, mandatos, despesas CEAPS, matérias e votações.
- `portal`: emendas do Portal da Transparência.

O script `init-db/01-setup-fiscaliza-db.sh` é executado pelo PostgreSQL na primeira inicialização do volume e cria os schemas. Em seguida, restora os arquivos `init-db/sql-auto/camara.dump`, `senado.dump` e `portal_data.dump` (ou alternativas `.sql`).

Para gerar esses dumps a partir de um banco já populado, com o contêiner `database` em execução:

```bash
bash backend/scripts/export_schemas.sh
```

Outros utilitários:

```powershell
python backend/scripts/create_indexes.py
python backend/scripts/update_company_summaries.py
```

`update_company_summaries.py` cria as tabelas de resumo de empresas e é executado automaticamente pelo backend uma vez na inicialização (após 5 segundos) e diariamente às 03:00.

## API

Base URL: `http://localhost:8000`

| Grupo | Exemplos de rotas |
| --- | --- |
| Geral | `GET /`, `GET /health` |
| Resumo da home | `GET /api/camara/resumo-principal`, `GET /api/senado/resumo-principal` |
| Câmara | `GET /api/camara/legislaturas`, `/api/camara/{legislatura}/lista`, `/estatisticas`, `/comparar`, `/{deputado_id}`, `/{deputado_id}/despesas`, `/{deputado_id}/emendas`, `/emendas`, `/emendas/resumo`, `/despesas/estatisticas`, `/empresas/estatisticas`, `/proposicoes`, `/proposicoes/{id}/votos` |
| Senado | `GET /api/senado/legislaturas`, `/api/senado/{legislatura}/lista`, `/estatisticas`, `/comparar`, `/{senador_codigo}`, `/{senador_codigo}/despesas`, `/{senador_codigo}/emendas/lista`, `/emendas`, `/emendas/resumo`, `/despesas/estatisticas`, `/empresas/estatisticas`, `/materia/listar`, `/materia/votacao` |

Os caminhos com `{legislatura}` usam o número da legislatura (por exemplo, `57`). Detalhes de parâmetros e respostas estão em [`README_API.md`](README_API.md) e, de forma sempre atualizada, em `http://localhost:8000/docs`.

## Scripts e coleta de dados

| Script | Função |
| --- | --- |
| `backend/scripts/ingest_emendas.py` | Busca emendas na API do Portal da Transparência (2020–2026) e grava em `portal.emendas` / `portal.emenda_documentos`. Requer `API_KEY`. |
| `backend/scripts/ingest_votacoes.py` | Busca votações na API aberta da Câmara (2007–2025) e grava em `camara.votacoes*`. |
| `backend/scripts/update_company_summaries.py` | Recalcula os resumos e rankings de empresas contratadas. |
| `backend/scripts/create_indexes.py` | Cria índices para acelerar as consultas. |
| `backend/scripts/export_schemas.sh` | Exporta os schemas para `init-db/sql-auto/`. |
| `backend/scripts/esperar_postgres.py` | Aguarda o PostgreSQL ficar disponível antes de iniciar o backend no Docker. |

Os coletores usam `DATABASE_URL` (ou as variáveis `DB_*`) e podem ser demorados por causa do limite de requisições das APIs públicas.

## Testes rápidos

Com o backend rodando:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/ -Method Get
Invoke-RestMethod -Uri http://localhost:8000/health -Method Get
Invoke-RestMethod -Uri http://localhost:8000/api/camara/legislaturas -Method Get
Invoke-RestMethod -Uri http://localhost:8000/api/camara/0/resumo-principal -Method Get
Invoke-RestMethod -Uri http://localhost:8000/api/senado/0/resumo-principal -Method Get
Invoke-RestMethod -Uri "http://localhost:8000/api/camara/57/lista" -Method Get
```

## Notas

- A API depende dos dados restaurados no banco; sem os dumps, as rotas retornam listas vazias ou erros.
- As rotas `/api/camara/resumo-principal` e `/api/senado/resumo-principal` recebem `legislatura` como parâmetro de consulta; as demais usam `legislatura` no caminho da URL.
- Em `/api/senado/{legislatura}/emendas`, a rota genérica de perfil pode capturar a requisição; use `/docs` para conferir os caminhos disponíveis.
- `README_API.md` descreve os endpoints, mas alguns caminhos lá refletem versões antigas; o Swagger em `/docs` é a fonte mais confiável.
- O frontend contém redirecionamentos para URLs antigas e um arquivo de configuração Vite transitório gerado automaticamente, que pode ser ignorado.
