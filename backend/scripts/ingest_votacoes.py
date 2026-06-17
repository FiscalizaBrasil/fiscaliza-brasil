import requests
import psycopg2
import os
import sys
import logging
import unicodedata
import time
from datetime import datetime, date
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

try:
    import database.db as db
except ImportError:
    sys.path.append(os.getcwd())
    import database.db as db

load_dotenv()

BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
REQUEST_DELAY = 0.3  # delay entre requests para nao sobrecarregar a API

def normalize_name(name):
    if not name:
        return ""
    return "".join(
        c for c in unicodedata.normalize('NFD', name)
        if not unicodedata.category(c).startswith('M')
    ).upper().strip()

def load_deputados_map(conn):
    logging.info("Carregando mapa de deputados (Nome -> ID)...")
    dep_map = {}
    ids_set = set()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, nome_civil FROM camara.deputados;")
            for row in cursor.fetchall():
                db_id, name = row
                ids_set.add(db_id)
                norm_name = normalize_name(name)
                if norm_name:
                    dep_map[norm_name] = db_id
    except Exception as e:
        logging.error(f"Erro ao carregar mapa: {e}")
    logging.info(f"Mapa carregado: {len(ids_set)} deputados por ID, {len(dep_map)} por nome.")
    return dep_map, ids_set

def api_get(url, params=None, timeout=30, retries=3):
    """Request com retry e rate limiting."""
    for attempt in range(retries):
        try:
            time.sleep(REQUEST_DELAY)
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 429:
                wait = min(60, 5 * (attempt + 1))
                logging.warning(f"Rate limited (429). Aguardando {wait}s...")
                time.sleep(wait)
            else:
                logging.warning(f"Status {r.status_code} para {url}")
                return None
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout (tentativa {attempt+1}/{retries}): {url}")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Erro request (tentativa {attempt+1}/{retries}): {e}")
            time.sleep(2)
    return None

def process_votacao(conn, vot_res, dep_map, ids_set):
    original_id = vot_res['id']
    base_id = original_id.split('-')[0]

    try:
        # Tenta buscar detalhes da votacao
        data = api_get(f"{BASE_URL}/votacoes/{original_id}")
        if not data:
            # Tenta com base_id
            data = api_get(f"{BASE_URL}/votacoes/{base_id}")

        with conn.cursor() as cursor:
            if data:
                det = data['dados']
                # Insere/atualiza votacao
                cursor.execute("""
                    INSERT INTO camara.votacoes (id, uri, data, data_hora_registro, sigla_orgao, uri_orgao, descricao)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET descricao = EXCLUDED.descricao;
                """, (
                    original_id,
                    det.get('uri'),
                    det.get('data'),
                    det.get('dataHoraRegistro'),
                    det.get('siglaOrgao'),
                    det.get('uriOrgao'),
                    det.get('descricao')
                ))

                # Vincula proposicoes afetadas
                for p in det.get('proposicoesAfetadas', []):
                    pid = p.get('id')
                    if pid:
                        cursor.execute("SELECT 1 FROM camara.proposicoes WHERE id = %s", (pid,))
                        if cursor.fetchone():
                            cursor.execute(
                                "INSERT INTO camara.votacoes_proposicoes (votacao_id, proposicao_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;",
                                (original_id, pid)
                            )
            else:
                # Sem detalhes, mas garante que a votacao exista no banco para o FK
                cursor.execute("""
                    INSERT INTO camara.votacoes (id, data, descricao)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                """, (
                    original_id,
                    vot_res.get('data'),
                    vot_res.get('descricao', 'Sem detalhes disponíveis')
                ))

            # Busca votos desta votacao
            v_url = f"{BASE_URL}/votacoes/{original_id}/votos"
            votos_vinc_count = 0
            votos_skip_count = 0

            while v_url:
                vdata = api_get(v_url)
                if not vdata:
                    break

                for v in vdata['dados']:
                    # A API usa 'deputado_' (com underscore) OU 'deputado'
                    dep = v.get('deputado_') or v.get('deputado', {})
                    api_id = dep.get('id')
                    api_name = dep.get('nome')
                    tipo_voto = v.get('tipoVoto')
                    # A API usa 'dataRegistroVoto' OU 'dataHoraVoto'
                    data_hora_voto = v.get('dataRegistroVoto') or v.get('dataHoraVoto')

                    # Pula votos sem tipo_voto (NOT NULL no banco)
                    if not tipo_voto:
                        votos_skip_count += 1
                        continue

                    # PRIORIDADE: Match por ID
                    if api_id in ids_set:
                        target_id = api_id
                    # FALLBACK: Match por Nome
                    else:
                        norm_api_name = normalize_name(api_name)
                        target_id = dep_map.get(norm_api_name)

                    if target_id:
                        try:
                            cursor.execute("""
                                INSERT INTO camara.votacoes_votos (votacao_id, deputado_id, tipo_voto, data_registro_voto)
                                VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;
                            """, (original_id, target_id, tipo_voto, data_hora_voto))
                            votos_vinc_count += 1
                        except Exception as e:
                            logging.debug(f"Erro inserindo voto: {e}")
                            conn.rollback()

                v_url = next(
                    (l['href'] for l in vdata.get('links', []) if l['rel'] == 'next'),
                    None
                )

            conn.commit()

            if votos_vinc_count > 0:
                logging.info(f"  Votacao {original_id}: {votos_vinc_count} votos vinculados" +
                             (f" ({votos_skip_count} ignorados)" if votos_skip_count else ""))
            return votos_vinc_count

    except Exception as e:
        conn.rollback()
        logging.error(f"Erro no ID {original_id}: {e}")
        return 0

def get_votacoes_periodo(data_inicio, data_fim):
    votacoes = []
    url = f"{BASE_URL}/votacoes"
    params = {
        "dataInicio": data_inicio,
        "dataFim": data_fim,
        "itens": 100,
        "ordem": "ASC",
        "ordenarPor": "dataHoraRegistro"
    }
    page = 1
    while url:
        try:
            data = api_get(url, params=params, timeout=30)
            if not data:
                break
            votacoes.extend(data['dados'])
            url = next(
                (l['href'] for l in data.get('links', []) if l['rel'] == 'next'),
                None
            )
            params = None  # proximas paginas usam a URL completa
            page += 1
        except Exception as e:
            logging.error(f"Erro na lista (pagina {page}): {e}")
            break
    return votacoes

def main():
    logging.info("=" * 60)
    logging.info("Iniciando ingestao de votacoes e votos (2007-2025)")
    logging.info("=" * 60)

    conn = db.get_db_connection()
    if not conn:
        logging.error("Nao foi possivel conectar ao banco!")
        return

    try:
        dep_map, ids_set = load_deputados_map(conn)

        if not ids_set:
            logging.error("Nenhum deputado encontrado no banco! Abortando.")
            return

        # Verifica progresso existente
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM camara.votacoes_votos;")
            existing = cur.fetchone()[0]
            logging.info(f"Votos ja existentes no banco: {existing}")

            # Descobre a data mais recente para continuar de onde parou
            cur.execute("""
                SELECT MAX(v.data) FROM camara.votacoes v
                INNER JOIN camara.votacoes_votos vv ON vv.votacao_id = v.id;
            """)
            last_date_row = cur.fetchone()
            last_date = last_date_row[0] if last_date_row and last_date_row[0] else None

        # Calcula ano e trimestre de inicio
        start_year = 2007
        start_quarter = 0  # indice 0-3

        if last_date:
            if isinstance(last_date, str):
                last_date = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
            elif isinstance(last_date, datetime):
                last_date = last_date.date()
            start_year = last_date.year
            month = last_date.month
            if month <= 3:
                start_quarter = 0
            elif month <= 6:
                start_quarter = 1
            elif month <= 9:
                start_quarter = 2
            else:
                start_quarter = 3
            logging.info(f"Continuando de onde parou: {last_date} (ano {start_year}, Q{start_quarter+1})")
        else:
            logging.info("Nenhum voto encontrado, iniciando do zero (2007-Q1)")

        periodos = [
            ("-01-01", "-03-31"),
            ("-04-01", "-06-30"),
            ("-07-01", "-09-30"),
            ("-10-01", "-12-31")
        ]

        total_votos_inseridos = 0

        for ano in range(start_year, 2026):
            logging.info(f"{'=' * 20} Ano: {ano} {'=' * 20}")

            for q_idx, (p_inicio, p_fim) in enumerate(periodos):
                # Pula trimestres anteriores ao ponto de retomada
                if ano == start_year and q_idx < start_quarter:
                    logging.info(f"  Pulando periodo Q{q_idx+1}/{ano} (ja processado)")
                    continue

                inicio = f"{ano}{p_inicio}"
                fim = f"{ano}{p_fim}"

                # Pula periodos futuros
                if datetime.strptime(inicio, "%Y-%m-%d").date() > date.today():
                    continue

                lista = get_votacoes_periodo(inicio, fim)
                logging.info(f"Periodo {inicio} a {fim}: {len(lista)} votacoes encontradas")

                if not lista:
                    continue

                votos_periodo = 0
                processadas = 0
                puladas = 0

                for i, v in enumerate(lista):
                    v_id = v['id']

                    # Pula votacoes que ja tem votos no banco
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1 FROM camara.votacoes_votos WHERE votacao_id = %s LIMIT 1", (v_id,))
                        if cur.fetchone():
                            puladas += 1
                            continue

                    count = process_votacao(conn, v, dep_map, ids_set)
                    votos_periodo += count
                    processadas += 1

                    if (processadas) % 25 == 0:
                        logging.info(f"  Progresso {inicio}: {processadas} processadas, {puladas} puladas, {votos_periodo} votos inseridos")

                total_votos_inseridos += votos_periodo
                logging.info(f"  Periodo {inicio} concluido: {processadas} processadas, {puladas} puladas, {votos_periodo} votos")

            # Log de progresso por ano
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM camara.votacoes_votos;")
                total_agora = cur.fetchone()[0]
            logging.info(f"  Total acumulado apos {ano}: {total_agora} votos no banco")

        logging.info("=" * 60)
        logging.info(f"CONCLUIDO! Total de votos inseridos nesta execucao: {total_votos_inseridos}")
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM camara.votacoes_votos;")
            logging.info(f"Total de votos no banco: {cur.fetchone()[0]}")
        logging.info("=" * 60)

    finally:
        conn.close()
        logging.info("Conexao fechada.")

if __name__ == "__main__":
    main()
