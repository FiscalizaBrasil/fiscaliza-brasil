#!/bin/bash
set -e

# Script para configurar o banco fiscaliza_db com os schemas camara, senado e portal
# e importar os respectivos arquivos SQL ou DUMP (binário).

DB_NAME="$POSTGRES_DB"
USER_NAME="$POSTGRES_USER"
SQL_DIR="/docker-entrypoint-initdb.d/sql-auto"

echo ">>> Iniciando a configuração do banco: $DB_NAME"

# 1. Criação dos Schemas básicos
echo ">>> Criando schemas de trabalho (camara, senado, portal)..."
psql -v ON_ERROR_STOP=1 --username "$USER_NAME" --dbname "$DB_NAME" <<-EOSQL
    CREATE SCHEMA IF NOT EXISTS camara;
    CREATE SCHEMA IF NOT EXISTS senado;
    CREATE SCHEMA IF NOT EXISTS portal;
EOSQL


# 3. Função de Importação
import_schema() {
    local schema=$1
    local file_base=$2

    if [ -f "$SQL_DIR/$file_base.dump" ]; then
        echo ">>> Importando schema '$schema' via pg_restore (arquivo binário)..."
        pg_restore -v --clean --if-exists --no-owner --no-privileges --username "$USER_NAME" --dbname "$DB_NAME" "$SQL_DIR/$file_base.dump"
    elif [ -f "$SQL_DIR/$file_base.sql" ]; then
        echo ">>> Importando schema '$schema' via psql (arquivo SQL)..."
        # Transforma public. em schema. para garantir que os dados caiam no schema correto
        sed "s/public\./$schema./g" "$SQL_DIR/$file_base.sql" | psql -v ON_ERROR_STOP=1 --username "$USER_NAME" --dbname "$DB_NAME" --set search_path="$schema"
    else
        echo ">>> Aviso: Nenhum arquivo ($file_base.dump ou $file_base.sql) encontrado para o schema '$schema'."
    fi
}

# 4. Execução das importações
import_schema "camara" "camara"
import_schema "senado" "senado"
import_schema "portal" "portal_data"

echo ">>> Configuração do fiscaliza_db concluída com sucesso."
