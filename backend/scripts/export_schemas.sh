#!/bin/bash


# Script para exportar os schemas do PostgreSQL via Docker (Versão Binária - Custom Format)
# Este script evita erros de versão do pg_dump instalada no Windows

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# bash backend/scripts/export_schemas.sh
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!


CONTAINER_NAME="database"
DATABASE_NAME="fiscaliza_db"
USER_NAME="postgres"
OUTPUT_DIR="./init-db/sql-auto"

# Garante que a pasta de saída
mkdir -p "$OUTPUT_DIR"

declare -A SCHEMAS
SCHEMAS["portal"]="portal_data.dump"
SCHEMAS["senado"]="senado.dump"
SCHEMAS["camara"]="camara.dump"

echo -e "\033[0;36mIniciando exportação BINÁRIA dos schemas do container '$CONTAINER_NAME'...\033[0m"

for schema in "${!SCHEMAS[@]}"; do
    filename=${SCHEMAS[$schema]}
    outputPath="$OUTPUT_DIR/$filename"

    echo -ne "Exportando schema '$schema' para '$filename' (formato binário)..."
    
    # -Fc: Custom Format (Binário comprimido)
    # -v: Verbose (removido daqui para não poluir o terminal, mas pode ser adicionado se quiser detalhes)
    docker exec "$CONTAINER_NAME" pg_dump -U "$USER_NAME" -Fc -n "$schema" "$DATABASE_NAME" > "$outputPath"

    if [ $? -eq 0 ]; then
        echo -e " \033[0;32m[OK]\033[0m"
    else
        echo -e " \033[0;31m[FALHA]\033[0m"
    fi
done

echo -e "\n\033[0;36mExportação concluída! Os arquivos .dump estão em $OUTPUT_DIR\033[0m"
echo -e "\033[0;33mDica: Para restaurar, use o comando 'pg_restore' em vez do 'psql'.\033[0m"
