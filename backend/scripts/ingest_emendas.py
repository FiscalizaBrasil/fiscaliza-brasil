import os
import sys
import time
import logging
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime

# Configurações de Retry e Headers
BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
API_KEY = os.getenv("API_KEY")
HEADERS = {
    "accept": "*/*",
    "chave-api-dados": API_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}
INTERVAL = 0.18 # Delay para se manter dentro do limite de requisicoes por minuto definidos em https://portaldatransparencia.gov.br/api-de-dados
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

try:
    import database.db as db
except ImportError:
    sys.path.append(os.getcwd())
    import database.db as db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def api_get(endpoint, params):
    retries = 0
    while retries < 5:
        try:
            r = requests.get(f"{BASE_URL}{endpoint}", headers=HEADERS, params=params, timeout=30)
            
            if r.status_code == 200:
                return r.json()
            
            if r.status_code == 429 or r.status_code == 403:
                wait_time = (retries + 1) * 10 # Aumenta o tempo a cada Request Limit ou Forbitten
                logging.warning(f"Status {r.status_code} no endpoint {endpoint}. Bloqueio detectado. Dormindo {wait_time}s...")
                time.sleep(wait_time)
                retries += 1
                continue
                
            logging.error(f"Erro inesperado: Status {r.status_code} - {r.text}")
            return None
        except Exception as e:
            logging.error(f"Exception de requisicao: {e}: Dormindo 5 segundos ")
            time.sleep(5)
            retries += 1
    return None

# --- Funcoes Auxiliares ---
def br_money_to_decimal(value):
    if not value or not isinstance(value, str):
        return 0.0
    
    # Remove espaços em branco (resolve o erro '- 5.18')
    # Remove pontos de milhar e troca vírgula decimal por ponto
    clean_value = value.replace(" ", "").replace(".", "").replace(",", ".")
    
    try:
        return float(clean_value)
    except ValueError:
        logging.warning(f"Não foi possível converter o valor: '{value}'")
        return 0.0

def parse_date(date_str):
    # Verifica se o valor é nulo, vazio ou a string de erro da API
    if not date_str or date_str in ["Sem informação", "S/I", ""]:
        return None
        
    try:
        # Tenta converter no formato esperado
        return datetime.strptime(date_str, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        # Se houver qualquer erro de formato, loga o aviso e retorna None
        logging.warning(f"Data inválida ignorada: {date_str}")
        return None

def fetch_all(endpoint, extra_params):
    page = 1
    all_data = []
    while True:
        params = {"pagina": page}
        params.update(extra_params)
        data = api_get(endpoint, params)

        if data is None or len(data) == 0:
            break

        all_data.extend(data)
        logging.info(f"Endpoint {endpoint} | Página {page} - {len(data)} registros")
        page += 1
        time.sleep(INTERVAL) 
    return all_data

# --- Database functions com nomes de colunas explícitos ---

def insert_emendas(conn, emendas):
    if not emendas: return
    sql = """
    INSERT INTO portal.emendas (
        codigo_emenda, ano, tipo_emenda, autor, nome_autor, numero_emenda,
        localidade_gasto, funcao, subfuncao, valor_empenhado, valor_liquidado,
        valor_pago, valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago
    ) VALUES (
        %(codigoEmenda)s, %(ano)s, %(tipoEmenda)s, %(autor)s, %(nomeAutor)s, %(numeroEmenda)s,
        %(localidadeDoGasto)s, %(funcao)s, %(subfuncao)s, %(valorEmpenhado)s, %(valorLiquidado)s,
        %(valorPago)s, %(valorRestoInscrito)s, %(valorRestoCancelado)s, %(valorRestoPago)s
    ) ON CONFLICT (codigo_emenda) DO NOTHING;
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, emendas)
    conn.commit()


def insert_emenda_and_get_pk(conn, e):
    """ Insere uma emenda e retorna o ID gerado pelo banco """
    sql = """
    INSERT INTO portal.emendas (
        codigo_emenda, ano, tipo_emenda, autor, nome_autor, numero_emenda,
        localidade_gasto, funcao, subfuncao, valor_empenhado, valor_liquidado,
        valor_pago, valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago
    ) VALUES (
        %(codigoEmenda)s, %(ano)s, %(tipoEmenda)s, %(autor)s, %(nomeAutor)s, %(numeroEmenda)s,
        %(localidadeDoGasto)s, %(funcao)s, %(subfuncao)s, %(valorEmpenhado)s, %(valorLiquidado)s,
        %(valorPago)s, %(valorRestoInscrito)s, %(valorRestoCancelado)s, %(valorRestoPago)s
    ) RETURNING id;
    """
    with conn.cursor() as cur:
        cur.execute(sql, e)
        return cur.fetchone()[0]

def insert_emenda_documentos(conn, docs, emenda_id):
    if not docs: return
    # Use APENAS o formato %(campo)s para consistência
    sql = """
    INSERT INTO portal.emenda_documentos (
        api_id, emenda_id, data, fase, codigo_documento, 
        codigo_documento_resumido, especie_tipo, tipo_emenda
    ) VALUES (
        %(id)s, %(emenda_id)s, %(data)s, %(fase)s, %(codigoDocumento)s,
        %(codigoDocumentoResumido)s, %(especieTipo)s, %(tipoEmenda)s
    ) ON CONFLICT (api_id) DO NOTHING;
    """
    with conn.cursor() as cur:
        for d in docs:
            # Injetamos o emenda_id no dicionário do documento antes de inserir
            d['emenda_id'] = emenda_id
            cur.execute(sql, d)
    conn.commit()

def ingest():
    conn = db.get_db_connection()
    
    # Intervalo definido para teste com inicio baseado na grande quantidade de emendas sem informação (S/I) de 2014 
    for ano in range(2020, 2027):
        logging.info(f"Iniciando ano {ano}")
        emendas_raw = fetch_all("/emendas", {"ano": ano})

        for e in emendas_raw:
            # 1. Sanitizar valores numéricos
            for field in ["valorEmpenhado", "valorLiquidado", "valorPago", "valorRestoInscrito", "valorRestoCancelado", "valorRestoPago"]:
                e[field] = br_money_to_decimal(e.get(field))

            # 2. Inserir Emenda e pegar ID
            try:
                emenda_internal_id = insert_emenda_and_get_pk(conn, e)
                conn.commit()
            except Exception as ex:
                logging.error(f"Erro ao inserir emenda {e.get('codigoEmenda')}: {ex}")
                conn.rollback()
                continue

            # 3. Buscar Documentos (se o código não for S/I) TODO: usar regex para buscar documentos com codigos de emenda validos
            codigo = e.get("codigoEmenda")
            if codigo and codigo != "S/I" and codigo != "REL. GERAL.":
                logging.info(f"Buscando docs para emenda {codigo}")
                docs_raw = fetch_all(f"/emendas/documentos/{codigo}", {})
                
                if docs_raw:
                    for d in docs_raw:
                        d["data"] = parse_date(d.get("data"))
                    insert_emenda_documentos(conn, docs_raw, emenda_internal_id)
                
                time.sleep(INTERVAL)
            else:
                logging.info(f"Pulando busca de docs: Sem informacao:{codigo})")

    conn.close()

if __name__ == "__main__":
    ingest()
