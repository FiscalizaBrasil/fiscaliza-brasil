# tcc-I

Projeto de TCC: API de Deputados (backend) e frontend em Vite + Vue.

Este repositório contém um backend em Python (FastAPI) e um frontend em TypeScript (Vite + Vue).

Este README descreve como configurar e executar o backend localmente, como preparar o banco de dados e exemplos de uso dos endpoints.

## Sumário

- Requisitos
- Estrutura do repositório
- Configuração (.env)
- Instalação e execução (Windows / PowerShell)
- Endpoints principais
- Testes rápidos (PowerShell)
- Notas sobre o banco de dados
- Sugestões e melhorias

---

## Requisitos

- Python 3.8+ (recomendado 3.10+)
- PostgreSQL (com a base de dados e tabela `deputados` criada)
- Git (opcional)

Dependências Python principais (instaladas via pip):

- python-dotenv
- psycopg2-binary
- fastapi
- uvicorn
- APScheduler

O arquivo `requirements.txt` na raiz do projeto já inclui todas as dependências necessárias, incluindo `fastapi`, `uvicorn` e `APScheduler`.


## Estrutura do repositório

Estrutura relevante:

- `backend/`
	- `main.py` - instância FastAPI e configuração CORS
	- `api/deputados/router.py` - endpoints relacionados a deputados
	- `database/db.py` - conexão com PostgreSQL (usa python-dotenv)
- `frontend/` - app frontend (Vite + Vue)
- `requirements.txt` - dependências Python listadas

## Configuração (.env)

Crie um arquivo `.env` na pasta `backend/` com as seguintes variáveis (exemplo):

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pgdb
DB_USER=postgres
DB_PASSWORD=pgpwd
```

Altere os valores conforme sua instalação do PostgreSQL.

## Instalação e execução (Windows / PowerShell)

Abra um PowerShell na pasta do projeto e siga estes passos (exemplo assume que você está dentro de `backend\`):

1. Criar e ativar virtualenv

```powershell
Set-Location -Path 'C:\Users\Bene\Desktop\Codes\tcc-I\backend'
python -m venv .venv
.venv\Scripts\Activate.ps1
# Se a política de execução bloquear, rode (uma vez):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

2. Instalar dependências

```powershell
pip install -r ..\requirements.txt
```

3. Criar `.env` conforme mostrado na seção anterior (na pasta `backend/`).

4. Rodar o servidor (modo desenvolvimento com reload)

```powershell
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

O servidor deve ficar acessível em `http://127.0.0.1:8000`.

### Comandos rápidos (resumo)

Backend (PowerShell):

```powershell
# entrar na pasta backend
Set-Location -Path 'C:\Users\Bene\Desktop\Codes\tcc-I\backend'

# criar e ativar venv
python -m venv .venv
.venv\Scripts\Activate.ps1

# instalar deps
pip install -r ..\requirements.txt

# criar .env (editar valores conforme necessário)
# New-Item -Path . -Name '.env' -ItemType 'file' -Value 'DB_HOST=localhost`nDB_PORT=5432`nDB_NAME=pgdb`nDB_USER=postgres`nDB_PASSWORD=pgpwd'

# rodar servidor
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend (dentro da pasta `frontend/`):

```powershell
# entrar na pasta frontend
Set-Location -Path 'C:\Users\Bene\Desktop\Codes\tcc-I\frontend'

# instalar dependências (escolha um gerenciador)
# npm
npm install
# ou pnpm
pnpm install
# ou yarn
yarn install

# rodar em modo dev (Vite)
# npm
npm run dev
# ou pnpm
pnpm dev
# ou yarn
yarn dev
```

> Nota: o frontend por padrão espera o backend rodando em http://localhost:5173 no CORS do backend há uma configuração que já permite `http://localhost:5173`.

## Endpoints principais

- GET `/` — rota raiz; retorna: `{ "message": "API de Deputados em funcionamento" }`
- GET `/api/deputados/buscar?nome=...` — busca deputados pelo nome (parâmetro `nome`, min_length=2). Retorna `{ "resultados": [...] }`.
- GET `/api/deputados/{id}` — retorna perfil detalhado do deputado com o `id` informado.

Observação: os endpoints dependem de uma conexão válida ao banco de dados configurado no `.env`.

## Testes rápidos (PowerShell)

Com o servidor rodando, você pode testar com `Invoke-RestMethod`:

```powershell
# checar raiz
Invoke-RestMethod -Uri http://127.0.0.1:8000/ -Method Get

# buscar deputados por nome
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/deputados/buscar?nome=Silva" -Method Get

# obter perfil por id
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/deputados/1" -Method Get
```

## Notas sobre o banco de dados

- `backend/database/db.py` usa `python-dotenv` para ler variáveis de ambiente do `.env` e `psycopg2` para conectar ao PostgreSQL.
- A API assume que existe uma tabela `deputados` com colunas como `id`, `nome_civil`, `uf_nascimento`, `email`, `data_nascimento`, `escolaridade`, `municipio_nascimento`.
- Se você não tiver a tabela, as requisições retornarão arrays vazios ou 404 para IDs não existentes.

Exemplo mínimo de DDL (só referência — ajuste tipos e restrições conforme necessário):

```sql
CREATE TABLE deputados (
	id SERIAL PRIMARY KEY,
	nome_civil TEXT,
	email TEXT,
	data_nascimento DATE,
	escolaridade TEXT,
	uf_nascimento TEXT,
	municipio_nascimento TEXT
);
```

## Sugestões e melhorias

- Adicionar `fastapi` e `uvicorn` ao `requirements.txt` para facilitar instalação.
- Adicionar `README` específico dentro de `backend/` e `frontend/` com instruções separadas.
- Criar um arquivo `backend/.env.example` com as variáveis necessárias.
- Adicionar scripts automatizados (ex.: `run-backend.ps1`) que ativem o venv e iniciem o uvicorn.

## Ajuda / Troubleshooting

- **ModuleNotFoundError: No module named 'apscheduler'**:
  - **No Docker**: Certifique-se de que o venv está ativo e rode `pip install -r ..\requirements.txt`.
  - **No Docker**: Rode `docker compose build backend` seguido de `docker compose up -d` para garantir que a imagem foi construída com as novas dependências.
- Erro de conexão ao banco: verifique `.env`, se o PostgreSQL está em execução e se o usuário/ senha/ host/ porta estão corretos.
- Erro de import (psycopg2): execute `pip install psycopg2-binary` no venv.
- Se houver mensagens de CORS no frontend, verifique `origins` em `backend/main.py` e ajuste conforme o `host:port` do frontend.

Se quiser, eu posso:
- adicionar `backend/.env.example` automaticamente,
- inserir `fastapi` e `uvicorn` no `requirements.txt`,
- criar um script `run-backend.ps1` para rodar tudo automaticamente.

---

Obrigado — me diga se quer que eu gere os arquivos auxiliares (`.env.example`, `run-backend.ps1`) agora.
