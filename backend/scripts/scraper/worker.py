import os
import json
import time
import random
import shutil
import logging
import threading
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import DATA_DIR, ANOS_PADRAO, SENADO_ULTIMO_ANO_CACHE_SECONDS, SENADO_ANO_INICIO, scraping_status, _status_lock
from .cache import is_cache_valid, load_json_if_valid, remover_acentos
from .verification import is_verified, clean_expired

from .camara.despesas import fetch_despesas_deputado
from .camara.proposicoes import fetch_proposicoes_ano, fetch_proposicoes_deputado
from .camara.votacoes import fetch_votacoes_ano
from .camara.historico import fetch_historico_deputado
from .camara.detalhes import fetch_detalhes_deputado

from .senado.despesas import fetch_despesas_senado_ano

from .portal.emendas import fetch_emendas_parlamentar

try:
    from database import db
    from scripts.import_data import (
        import_despesas_camara,
        import_despesas_senado,
        import_emendas,
        import_proposicoes_camara,
        import_autores_proposicoes,
        import_historico_deputados,
        import_detalhes_deputados,
        import_processos_senado,
        import_proposicoes_deputado,
        import_votacoes_camara,
        _buscar_e_inserir_senador_api,
    )
except ImportError:
    logging.exception("Falha ao importar módulos de dados:")
    db = None
    import_despesas_camara = None
    import_despesas_senado = None
    import_emendas = None
    import_proposicoes_camara = None
    import_autores_proposicoes = None
    import_historico_deputados = None
    import_detalhes_deputados = None
    import_processos_senado = None
    import_proposicoes_deputado = None
    import_votacoes_camara = None
    _buscar_e_inserir_senador_api = None

# ---------------------------------------------------------------------------
# Named loggers so each scraper emits prefixed messages automatically
# ---------------------------------------------------------------------------
_log = logging.getLogger("WORKER")

log_camara = logging.getLogger("CAMARA")
log_senado = logging.getLogger("SENADO")
log_portal = logging.getLogger("PORTAL")

# ---------------------------------------------------------------------------
# Thread handles and stop flags
# ---------------------------------------------------------------------------
_background_thread = None
_background_thread_camara = None
_background_thread_senado = None
_background_thread_portal = None

_stop_background = False
_stop_camara = False
_stop_senado = False
_stop_portal = False


# ---------------------------------------------------------------------------
# Retry tracking – rebaixa arquivos em vez de deletar, registra itens com
# 3+ tentativas para análise manual.
# ---------------------------------------------------------------------------
RETRY_DIR = os.path.join(DATA_DIR, "failed")
RETRY_TRACKER_PATH = os.path.join(RETRY_DIR, "retry_tracker.json")
NEEDS_REVIEW_PATH = os.path.join(RETRY_DIR, "needs_review.json")
MAX_RETRIES = 3


def _load_json(path):
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _increment_retry(item_key, error_msg, source):
    tracker = _load_json(RETRY_TRACKER_PATH)
    now = datetime.datetime.now().isoformat()
    if item_key not in tracker:
        tracker[item_key] = {
            "count": 0,
            "first_failure": now,
            "source": source,
        }
    tracker[item_key]["count"] += 1
    tracker[item_key]["last_failure"] = now
    tracker[item_key]["last_error"] = error_msg
    _save_json(RETRY_TRACKER_PATH, tracker)
    return tracker[item_key]["count"]


def _move_to_failed(source_path, failed_subpath, is_dir=False):
    dest = os.path.join(RETRY_DIR, failed_subpath)
    if is_dir:
        dest_parent = os.path.join(RETRY_DIR, os.path.dirname(failed_subpath))
        os.makedirs(dest_parent, exist_ok=True)
        if os.path.exists(dest):
            shutil.rmtree(dest)
        if os.path.isdir(source_path):
            shutil.move(source_path, dest)
    else:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest):
            os.remove(dest)
        if source_path is not None and os.path.isfile(source_path):
            shutil.move(source_path, dest)


def _register_for_review(item_key, source, retry_count, error_msg, failed_path):
    reviews = _load_json(NEEDS_REVIEW_PATH)
    if isinstance(reviews, dict):
        reviews = list(reviews.values())
    reviews.append({
        "item_key": item_key,
        "source": source,
        "retry_count": retry_count,
        "last_error": error_msg,
        "failed_path": failed_path,
        "registered_at": datetime.datetime.now().isoformat(),
    })
    _save_json(NEEDS_REVIEW_PATH, reviews)


def _handle_import_failure(logger, item_key, source_path, failed_subpath,
                           error_msg, source_name, is_dir=False):
    retry_count = _increment_retry(item_key, error_msg, source_name)
    _move_to_failed(source_path, failed_subpath, is_dir=is_dir)

    if retry_count >= MAX_RETRIES:
        _register_for_review(item_key, source_name, retry_count,
                            error_msg, failed_subpath)
        logger.error(
            "RETRY_LIMIT: %s atingiu %d tentativas. "
            "Registrado em %s para analise manual. Ultimo erro: %s",
            item_key, retry_count, NEEDS_REVIEW_PATH, error_msg
        )
        return "RETRY_LIMIT"

    logger.warning("%s IMPORT_FAIL (tentativa %d/%d): %s",
                   item_key, retry_count, MAX_RETRIES, error_msg)
    return "IMPORT_FAIL"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MSG_DB_CONN_FAILED = "Falha ao conectar ao banco de dados"
_MSG_IMPORT_FALSE = "Importacao retornou False (verificar logs do import_data.py)"
_MSG_DOWNLOAD_ERROR = "Erro no download: "


def _sanitize_nome(nome):
    return remover_acentos(nome).replace(" ", "_").replace("/", "_")


def _load_deputados_dados():
    """Carrega dados de todos os arquivos de deputados (todas as legislaturas)."""
    dados = []
    camara_dir = os.path.join(DATA_DIR, "camara")
    if not os.path.isdir(camara_dir):
        return []
    for fname in sorted(os.listdir(camara_dir)):
        if fname.startswith("deputados") and fname.endswith(".json"):
            json_path = os.path.join(camara_dir, fname)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                dados.extend(data.get("dados", []))
            except Exception:
                pass
    return dados


def _load_deputados_ids():
    dados = _load_deputados_dados()
    return {dep["id"] for dep in dados if dep.get("id")}


def _move_matching_files(directory, prefix, failed_subpath_dir):
    if not os.path.isdir(directory):
        return
    for fname in list(os.listdir(directory)):
        if fname.startswith(prefix) and fname.endswith(".json"):
            _move_to_failed(
                os.path.join(directory, fname),
                f"{failed_subpath_dir}/{fname}",
            )


# ===================================================================
# Utility functions – unchanged
# ===================================================================

def _anos_legislatura(id_legislatura):
    """Calcula os anos cobertos por uma legislatura."""
    ano_inicio = 2023 - (57 - id_legislatura) * 4
    return list(range(ano_inicio, ano_inicio + 4))


def _get_deputados_pendentes(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")

    dados = _load_deputados_dados()
    if not dados:
        return []

    seen = set()
    pendentes = []

    db_com_legislatura = set()

    if db is not None:
        try:
            conn = db.get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT dm.deputado_id, dm.legislatura_id "
                            "FROM camara.deputados_despesas dd "
                            "JOIN camara.deputados_mandatos dm ON dm.id = dd.mandato_id "
                            "GROUP BY dm.deputado_id, dm.legislatura_id"
                        )
                        db_com_legislatura = {(row[0], row[1]) for row in cur.fetchall()}
                finally:
                    db.release_db_connection(conn)
        except Exception:
            pass

    for dep in dados:
        dep_id = dep["id"]
        id_leg = dep.get("idLegislatura")
        if not id_leg:
            continue

        chave = (dep_id, id_leg)
        if chave in seen:
            continue
        seen.add(chave)

        if is_verified("camara_despesas", f"{dep_id}_{id_leg}"):
            continue

        if chave in db_com_legislatura:
            continue

        dep_dir = os.path.join(data_dir, str(dep_id))
        leg_dir = os.path.join(dep_dir, str(id_leg))
        anos = _anos_legislatura(id_leg)

        completo = True
        for ano in anos:
            ano_tem_dados = False
            if os.path.isdir(leg_dir):
                for fname in os.listdir(leg_dir):
                    if fname == f"{ano}.json":
                        ano_tem_dados = True
                        break
            if not ano_tem_dados:
                completo = False
                break

        if completo:
            # Arquivos existem, mas verifica se dados estão no banco
            if chave not in db_com_legislatura:
                # Arquivos baixados mas não importados -> marcar como pendente para reimportação
                pendentes.append(dep)
            continue

        pendentes.append(dep)

    return pendentes


def _get_anos_senado_pendentes(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "despesas")

    ano_atual = datetime.datetime.now().year
    anos = list(range(ano_atual, SENADO_ANO_INICIO - 1, -1))
    pendentes = []
    for ano in anos:
        filepath = os.path.join(data_dir, f"{ano}.json")
        if not os.path.isfile(filepath):
            pendentes.append(ano)
            continue

        if is_verified("senado_despesas", str(ano)):
            continue

        if db is not None:
            try:
                conn = db.get_db_connection()
                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT COUNT(*) FROM senado.despesa_ceaps WHERE ano = %s",
                                (ano,),
                            )
                            if cur.fetchone()[0] == 0:
                                pendentes.append(ano)
                    finally:
                        db.release_db_connection(conn)
            except Exception:
                pass

        if ano == datetime.datetime.now().year and os.path.isfile(filepath):
            idade = time.time() - os.path.getmtime(filepath)
            if idade > SENADO_ULTIMO_ANO_CACHE_SECONDS:
                pendentes.append(ano)

    return pendentes


def _get_anos_proposicoes_pendentes(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes")

    anos = list(ANOS_PADRAO)
    pendentes = []
    for ano in anos:
        ano_tem_dados = False
        if os.path.isdir(data_dir):
            for fname in os.listdir(data_dir):
                if fname == f"{ano}.json":
                    ano_tem_dados = True
                    break
        if not ano_tem_dados:
            pendentes.append(ano)
    return pendentes


def _get_anos_votacoes_pendentes(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "votacoes")

    ano_atual = datetime.datetime.now().year
    anos = list(ANOS_PADRAO)
    pendentes = []

    if not os.path.isdir(data_dir):
        return anos

    for ano in anos:
        if ano < ano_atual:
            merged = os.path.join(data_dir, f"{ano}.json")
            if not os.path.isfile(merged) or not is_cache_valid(merged):
                pendentes.append(ano)
        else:
            # Ano corrente: verifica 3 quadrimestres, todos sem _incomplete
            ok = True
            for i in (1, 2, 3):
                q_path = os.path.join(data_dir, f"{ano}_Q{i}.json")
                cached = load_json_if_valid(q_path)
                if cached is None or cached.get("_incomplete"):
                    ok = False
                    break
            if not ok:
                pendentes.append(ano)

    return pendentes


def _get_parlamentares_sem_emendas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "portal", "emendas")

    nomes_parlamentares = set()

    dep_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if os.path.isfile(dep_path):
        with open(dep_path, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
        for dep in dep_data.get("dados", []):
            nome = dep.get("nome", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)

    sen_path = os.path.join(DATA_DIR, "senado", "senadores.json")
    if os.path.isfile(sen_path):
        with open(sen_path, "r", encoding="utf-8") as f:
            sen_data = json.load(f)
        parlamentares = (
            sen_data.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        for par in parlamentares:
            ident = par.get("IdentificacaoParlamentar", {})
            nome = ident.get("NomeParlamentar", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)

    sem_emendas = []
    ano_atual = datetime.datetime.now().year

    for nome in nomes_parlamentares:
        nome_sanitizado = _sanitize_nome(nome)

        if is_verified("portal_emendas", nome_sanitizado.upper()):
            continue

        merged_path = os.path.join(data_dir, f"{nome_sanitizado}_{ano_atual}.json")
        if os.path.isfile(merged_path) and is_cache_valid(merged_path):
            continue

        sem_emendas.append(nome)

    return sem_emendas


def _get_deputados_sem_historico(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "historico")

    ids_unicos = _load_deputados_ids()
    if not ids_unicos:
        return []

    sem_historico = []
    for dep_id in sorted(ids_unicos):
        if is_verified("camara_historico", str(dep_id)):
            continue
        filepath = os.path.join(data_dir, f"{dep_id}.json")
        if not os.path.isfile(filepath) or not is_cache_valid(filepath):
            sem_historico.append(dep_id)
    return sem_historico


def _get_deputados_sem_detalhes(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "detalhes")

    ids_unicos = _load_deputados_ids()
    if not ids_unicos:
        return []

    sem_detalhes = []
    for dep_id in sorted(ids_unicos):
        if is_verified("camara_detalhes", str(dep_id)):
            continue
        filepath = os.path.join(data_dir, f"{dep_id}.json")
        if not os.path.isfile(filepath) or not is_cache_valid(filepath):
            sem_detalhes.append(dep_id)
    return sem_detalhes


def _get_deputados_sem_proposicoes(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes", "deputados")

    ids_unicos = _load_deputados_ids()
    if not ids_unicos:
        return []

    sem_proposicoes = []
    for dep_id in sorted(ids_unicos):
        tem_dados = False
        if os.path.isdir(data_dir):
            for fname in os.listdir(data_dir):
                if fname == f"{dep_id}.json":
                    tem_dados = True
                    break
        if not tem_dados:
            sem_proposicoes.append(dep_id)
    return sem_proposicoes


# ===================================================================
# Generic process function – all _processar_* are thin wrappers
# ===================================================================

def _processar_com_importacao(config):
    logger = config['logger']
    fetch_fn = config['fetch']
    import_fn = config['import_fn']
    import_kwargs = config['import_kwargs']
    item_key = config['item_key']
    label = config['label']
    failed_subpath = config['failed_subpath']
    source_name = config['source_name']
    source_path = config.get('source_path')
    is_dir = config.get('is_dir', False)
    move_mm = config.get('move_matching')

    log_msg = config.get('log_msg')
    if log_msg:
        logger.info(log_msg, *config.get('log_msg_args', ()))

    try:
        fetch_fn()

        import_ok = None
        conn_failed = False
        if import_fn is not None:
            conn = db.get_db_connection()
            if conn:
                try:
                    import_ok = import_fn(conn, **import_kwargs)
                    if import_ok:
                        logger.info(config['success_msg'],
                                    *config.get('success_msg_args', ()))
                finally:
                    db.release_db_connection(conn)
            else:
                import_ok = False
                conn_failed = True

        if import_ok is False:
            error_msg = _MSG_DB_CONN_FAILED if conn_failed else _MSG_IMPORT_FALSE
            if move_mm:
                _move_matching_files(move_mm['dir'], move_mm['prefix'],
                                    move_mm['failed_subpath_dir'])
            result = _handle_import_failure(
                logger=logger,
                item_key=item_key,
                source_path=source_path,
                failed_subpath=failed_subpath,
                error_msg=error_msg,
                source_name=source_name,
                is_dir=is_dir,
            )
            return f"{label} {result}"

        if import_ok is True:
            return f"{label} OK"

        return f"{label} NO_DATA"
    except Exception as e:
        logger.error(config['error_prefix'],
                    *config.get('error_prefix_args', ()), e)
        if move_mm:
            _move_matching_files(move_mm['dir'], move_mm['prefix'],
                                move_mm['failed_subpath_dir'])
        error_msg = f"{_MSG_DOWNLOAD_ERROR}{e}"
        result = _handle_import_failure(
            logger=logger,
            item_key=item_key,
            source_path=source_path,
            failed_subpath=failed_subpath,
            error_msg=error_msg,
            source_name=source_name,
            is_dir=is_dir,
        )
        return f"{label} ERRO ({result})"


def _processar_deputado(dep):
    dep_id = dep["id"]
    id_leg = dep.get("idLegislatura")
    anos = _anos_legislatura(id_leg) if id_leg else list(ANOS_PADRAO)
    return _processar_com_importacao({
        'logger': log_camara,
        'log_msg': "Baixando despesas do deputado %s (%s) legislatura %s",
        'log_msg_args': (dep_id, dep.get("nome", ""), id_leg or "N/A"),
        'fetch': lambda: fetch_despesas_deputado(dep_id, anos=anos, id_legislatura=id_leg),
        'import_fn': import_despesas_camara,
        'import_kwargs': {'deputado_id': dep_id},
        'item_key': f'deputado/{dep_id}',
        'label': f'deputado {dep_id}',
        'source_path': os.path.join(DATA_DIR, "camara", "despesas", str(dep_id)),
        'failed_subpath': f'camara/despesas/{dep_id}',
        'source_name': 'camara',
        'is_dir': True,
        'success_msg': "Despesas do deputado %s importadas.",
        'success_msg_args': (dep_id,),
        'error_prefix': "Erro no deputado %s: %s",
        'error_prefix_args': (dep_id,),
    })


def _processar_ano_senado(ano):
    return _processar_com_importacao({
        'logger': log_senado,
        'log_msg': "Baixando despesas CEAPS de %s",
        'log_msg_args': (ano,),
        'fetch': lambda: fetch_despesas_senado_ano(ano),
        'import_fn': import_despesas_senado,
        'import_kwargs': {'ano': ano},
        'item_key': f'senado/{ano}',
        'label': f'senado {ano}',
        'source_path': os.path.join(DATA_DIR, "senado", "despesas", f"{ano}.json"),
        'failed_subpath': f'senado/despesas/{ano}.json',
        'source_name': 'senado',
        'success_msg': "Despesas de %s importadas.",
        'success_msg_args': (ano,),
        'error_prefix': "Erro no ano %s: %s",
        'error_prefix_args': (ano,),
    })


def _processar_emendas_parlamentar(nome):
    def _fetch():
        ano_atual = datetime.datetime.now().year
        for ano in range(2015, ano_atual + 1):
            fetch_emendas_parlamentar(nome, ano=ano)

    nome_sanitizado = _sanitize_nome(nome)
    return _processar_com_importacao({
        'logger': log_portal,
        'log_msg': "Buscando emendas de %s",
        'log_msg_args': (nome,),
        'fetch': _fetch,
        'import_fn': import_emendas,
        'import_kwargs': {'arquivo': nome},
        'item_key': f'emendas/{nome}',
        'label': f'emendas {nome}',
        'failed_subpath': f'portal/emendas/{nome_sanitizado}',
        'source_name': 'portal',
        'move_matching': {
            'dir': os.path.join(DATA_DIR, "portal", "emendas"),
            'prefix': nome_sanitizado,
            'failed_subpath_dir': 'portal/emendas',
        },
        'success_msg': "Dados de %s importados.",
        'success_msg_args': (nome,),
        'error_prefix': "Erro em %s: %s",
        'error_prefix_args': (nome,),
    })


def _processar_ano_proposicoes(ano):
    return _processar_com_importacao({
        'logger': log_camara,
        'log_msg': "Baixando proposicoes de %s",
        'log_msg_args': (ano,),
        'fetch': lambda: fetch_proposicoes_ano(ano),
        'import_fn': import_proposicoes_camara,
        'import_kwargs': {'ano': ano},
        'item_key': f'proposicoes/{ano}',
        'label': f'proposicoes {ano}',
        'failed_subpath': f'camara/proposicoes/{ano}',
        'source_name': 'camara',
        'move_matching': {
            'dir': os.path.join(DATA_DIR, "camara", "proposicoes"),
            'prefix': f'{ano}',
            'failed_subpath_dir': 'camara/proposicoes',
        },
        'success_msg': "Proposicoes de %s importadas.",
        'success_msg_args': (ano,),
        'error_prefix': "Erro em proposicoes de %s: %s",
        'error_prefix_args': (ano,),
    })


def _processar_ano_votacoes(ano):
    return _processar_com_importacao({
        'logger': log_camara,
        'log_msg': "Baixando votacoes de %s",
        'log_msg_args': (ano,),
        'fetch': lambda: fetch_votacoes_ano(ano),
        'import_fn': import_votacoes_camara,
        'import_kwargs': {'ano': ano},
        'item_key': f'votacoes/{ano}',
        'label': f'votacoes {ano}',
        'failed_subpath': f'camara/votacoes/{ano}',
        'source_name': 'camara',
        'success_msg': "Votacoes de %s importadas.",
        'success_msg_args': (ano,),
        'error_prefix': "Erro em votacoes de %s: %s",
        'error_prefix_args': (ano,),
    })


def _processar_historico_deputado(dep_id):
    return _processar_com_importacao({
        'logger': log_camara,
        'log_msg': "Baixando historico do deputado %s",
        'log_msg_args': (dep_id,),
        'fetch': lambda: fetch_historico_deputado(dep_id),
        'import_fn': import_historico_deputados,
        'import_kwargs': {'deputado_id': dep_id},
        'item_key': f'historico/{dep_id}',
        'label': f'historico {dep_id}',
        'source_path': os.path.join(DATA_DIR, "camara", "historico", f"{dep_id}.json"),
        'failed_subpath': f'camara/historico/{dep_id}.json',
        'source_name': 'camara',
        'success_msg': "Historico do deputado %s importado.",
        'success_msg_args': (dep_id,),
        'error_prefix': "Erro no historico do deputado %s: %s",
        'error_prefix_args': (dep_id,),
    })


def _processar_detalhes_deputado(dep_id):
    return _processar_com_importacao({
        'logger': log_camara,
        'log_msg': "Baixando detalhes do deputado %s",
        'log_msg_args': (dep_id,),
        'fetch': lambda: fetch_detalhes_deputado(dep_id),
        'import_fn': import_detalhes_deputados,
        'import_kwargs': {'deputado_id': dep_id},
        'item_key': f'detalhes/{dep_id}',
        'label': f'detalhes {dep_id}',
        'source_path': os.path.join(DATA_DIR, "camara", "detalhes", f"{dep_id}.json"),
        'failed_subpath': f'camara/detalhes/{dep_id}.json',
        'source_name': 'camara',
        'success_msg': "Detalhes do deputado %s importados.",
        'success_msg_args': (dep_id,),
        'error_prefix': "Erro nos detalhes do deputado %s: %s",
        'error_prefix_args': (dep_id,),
    })


def _processar_proposicoes_deputado(dep_id):
    return _processar_com_importacao({
        'logger': log_camara,
        'log_msg': "Baixando proposicoes do deputado %s",
        'log_msg_args': (dep_id,),
        'fetch': lambda: fetch_proposicoes_deputado(dep_id),
        'import_fn': import_proposicoes_deputado,
        'import_kwargs': {'deputado_id': dep_id},
        'item_key': f'proposicoes_dep/{dep_id}',
        'label': f'proposicoes_deputado {dep_id}',
        'failed_subpath': f'camara/proposicoes/deputados/{dep_id}',
        'source_name': 'camara',
        'move_matching': {
            'dir': os.path.join(DATA_DIR, "camara", "proposicoes", "deputados"),
            'prefix': f'{dep_id}',
            'failed_subpath_dir': 'camara/proposicoes/deputados',
        },
        'success_msg': "Proposicoes do deputado %s importadas.",
        'success_msg_args': (dep_id,),
        'error_prefix': "Erro nas proposicoes do deputado %s: %s",
        'error_prefix_args': (dep_id,),
    })


def _garantir_senadores_despesas():
    """
    Garante que todo cod_senador presente em despesa_ceaps tenha
    registro em parlamentar + mandato no banco.
    Utiliza cache em disco (data/senado/detalhes/{codigo}.json) para
    evitar chamadas repetidas à API.
    """
    if _buscar_e_inserir_senador_api is None:
        return

    conn = db.get_db_connection() if db is not None else None
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            # 1. Senadores em despesas sem registro em parlamentar
            cur.execute("""
                SELECT DISTINCT d.cod_senador
                FROM senado.despesa_ceaps d
                WHERE NOT EXISTS (
                    SELECT 1 FROM senado.parlamentar p WHERE p.codigo = d.cod_senador
                )
            """)
            sem_parlamentar = [row[0] for row in cur.fetchall()]

            for cod in sem_parlamentar:
                _buscar_e_inserir_senador_api(cur, cod)
                conn.commit()

            # 2. Senadores em parlamentar sem mandato
            cur.execute("""
                SELECT p.codigo
                FROM senado.parlamentar p
                WHERE NOT EXISTS (
                    SELECT 1 FROM senado.mandato m WHERE m.codigo_parlamentar = p.codigo
                )
            """)
            sem_mandato = [row[0] for row in cur.fetchall()]

            for cod in sem_mandato:
                _buscar_e_inserir_senador_api(cur, cod)
                conn.commit()

            if sem_parlamentar or sem_mandato:
                log_senado.info(
                    "Integridade de senadores: %d sem parlamentar, %d sem mandato.",
                    len(sem_parlamentar), len(sem_mandato),
                )
    except Exception as e:
        log_senado.error("Erro ao garantir integridade de senadores: %s", e)
    finally:
        db.release_db_connection(conn)


# ===================================================================
# Background workers – one per source
# ===================================================================

# Camara rate limits (per cycle)
CAMARA_LIMIT_DESPESAS = 5
CAMARA_LIMIT_PROPOSICOES = 3
CAMARA_LIMIT_HISTORICO = 5
CAMARA_LIMIT_DETALHES = 5
CAMARA_LIMIT_PROPOSICOES_DEP = 5
CAMARA_LIMIT_VOTACOES = 3
CAMARA_CYCLE_SLEEP = 5  # seconds between cycles
CAMARA_IDLE_SLEEP = 30  # seconds when everything is complete

# Senado rate limits
SENADO_LIMIT_ANOS = 4
SENADO_CYCLE_SLEEP = 5
SENADO_IDLE_SLEEP = 30

# Portal rate limits
PORTAL_LIMIT_PARLAMENTARES = 3
PORTAL_CYCLE_SLEEP = 2
PORTAL_IDLE_SLEEP = 30


def _background_worker_generico(logger, name, stop_flag_attr, perfil_fn,
                                 build_tasks_fn, cycle_sleep, idle_sleep,
                                 max_workers, wait_precondition=None):
    stop_flag = globals()[stop_flag_attr]
    logger.info("Scraper %s iniciado.", name)

    if wait_precondition:
        waited = False
        while not stop_flag:
            if wait_precondition():
                break
            if not waited:
                logger.info(
                    "Aguardando dados base de Camara e Senado estarem prontos..."
                )
                waited = True
            time.sleep(10)

    while not stop_flag:
        try:
            clean_expired()

            if perfil_fn:
                perfil_fn()

            tasks, complete = build_tasks_fn()

            if complete:
                logger.info(
                    "Todos os dados do %s importados. Aguardando %ds...",
                    name, idle_sleep,
                )
                for _ in range(idle_sleep):
                    if stop_flag:
                        break
                    time.sleep(1)
                continue

            if not tasks:
                time.sleep(5)
                continue

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(fn, item): (fn, item)
                    for fn, item in tasks
                }
                for future in as_completed(futures):
                    fn, item = futures[future]
                    try:
                        result = future.result(timeout=600)
                        logger.info("Tarefa concluida: %s", result)
                    except Exception as e:
                        logger.error(
                            "Tarefa %s falhou: %s",
                            getattr(fn, '__name__', str(fn)), e,
                        )

            time.sleep(cycle_sleep)

        except Exception as e:
            logger.error("Erro no scraper %s: %s", name, e)
            time.sleep(60)


def _build_camara_tasks():
    despesas = _get_deputados_pendentes()
    proposicoes = _get_anos_proposicoes_pendentes()
    votacoes = _get_anos_votacoes_pendentes()
    historicos = _get_deputados_sem_historico()
    detalhes = _get_deputados_sem_detalhes()
    proposicoes_dep = _get_deputados_sem_proposicoes()

    complete = (
        len(despesas) == 0
        and len(proposicoes) == 0
        and len(votacoes) == 0
        and len(historicos) == 0
        and len(detalhes) == 0
        and len(proposicoes_dep) == 0
    )

    with _status_lock:
        scraping_status["camara_pendentes"] = len(despesas)
        scraping_status["camara_completa"] = complete
        scraping_status["proposicoes_pendentes"] = len(proposicoes)
        scraping_status["proposicoes_completa"] = len(proposicoes) == 0
        scraping_status["votacoes_pendentes"] = len(votacoes)
        scraping_status["votacoes_completa"] = len(votacoes) == 0

    if complete:
        return [], True

    random.shuffle(despesas)
    random.shuffle(proposicoes)
    random.shuffle(votacoes)
    random.shuffle(historicos)
    random.shuffle(detalhes)
    random.shuffle(proposicoes_dep)

    tasks = []
    for dep in despesas[:CAMARA_LIMIT_DESPESAS]:
        tasks.append((_processar_deputado, dep))
    for ano in proposicoes[:CAMARA_LIMIT_PROPOSICOES]:
        tasks.append((_processar_ano_proposicoes, ano))
    for ano in votacoes[:CAMARA_LIMIT_VOTACOES]:
        tasks.append((_processar_ano_votacoes, ano))
    for dep_id in historicos[:CAMARA_LIMIT_HISTORICO]:
        tasks.append((_processar_historico_deputado, dep_id))
    for dep_id in detalhes[:CAMARA_LIMIT_DETALHES]:
        tasks.append((_processar_detalhes_deputado, dep_id))
    for dep_id in proposicoes_dep[:CAMARA_LIMIT_PROPOSICOES_DEP]:
        tasks.append((_processar_proposicoes_deputado, dep_id))

    n_desp = min(len(despesas), CAMARA_LIMIT_DESPESAS)
    n_anos = min(len(proposicoes), CAMARA_LIMIT_PROPOSICOES)
    n_vot = min(len(votacoes), CAMARA_LIMIT_VOTACOES)
    n_hist = min(len(historicos), CAMARA_LIMIT_HISTORICO)
    n_det = min(len(detalhes), CAMARA_LIMIT_DETALHES)
    n_prop = min(len(proposicoes_dep), CAMARA_LIMIT_PROPOSICOES_DEP)
    log_camara.info(
        "Ciclo: Despesas=%d Proposicoes=%d Votacoes=%d Historico=%d Detalhes=%d "
        "ProposDep=%d (total=%d)",
        n_desp, n_anos, n_vot, n_hist, n_det, n_prop, len(tasks),
    )

    return tasks, complete


def _background_worker_camara():
    _background_worker_generico(
        logger=log_camara,
        name="Camara",
        stop_flag_attr="_stop_camara",
        perfil_fn=None,
        build_tasks_fn=_build_camara_tasks,
        cycle_sleep=CAMARA_CYCLE_SLEEP,
        idle_sleep=CAMARA_IDLE_SLEEP,
        max_workers=6,
    )


def _build_senado_tasks():
    # Garantir integridade de senadores históricos (parlamentar + mandato)
    _garantir_senadores_despesas()

    pendentes = _get_anos_senado_pendentes()
    complete = len(pendentes) == 0

    with _status_lock:
        scraping_status["senado_pendentes"] = len(pendentes)
        scraping_status["senado_completo"] = complete

    if complete:
        return [], True

    random.shuffle(pendentes)
    batch = pendentes[:SENADO_LIMIT_ANOS]

    log_senado.info(
        "Ciclo: %d anos (total pendentes: %d)", len(batch), len(pendentes)
    )

    return [(_processar_ano_senado, ano) for ano in batch], complete


def _background_worker_senado():
    _background_worker_generico(
        logger=log_senado,
        name="Senado",
        stop_flag_attr="_stop_senado",
        perfil_fn=None,
        build_tasks_fn=_build_senado_tasks,
        cycle_sleep=SENADO_CYCLE_SLEEP,
        idle_sleep=SENADO_IDLE_SLEEP,
        max_workers=2,
    )


def _build_portal_tasks():
    pendentes = _get_parlamentares_sem_emendas()
    complete = len(pendentes) == 0

    with _status_lock:
        scraping_status["em_andamento"] = not complete

    if complete:
        return [], True

    random.shuffle(pendentes)
    batch = pendentes[:PORTAL_LIMIT_PARLAMENTARES]

    log_portal.info(
        "Ciclo: %d parlamentares (total pendentes: %d)",
        len(batch), len(pendentes),
    )

    return [(_processar_emendas_parlamentar, nome) for nome in batch], complete


def _background_worker_portal():
    _background_worker_generico(
        logger=log_portal,
        name="Portal da Transparencia",
        stop_flag_attr="_stop_portal",
        perfil_fn=None,
        build_tasks_fn=_build_portal_tasks,
        cycle_sleep=PORTAL_CYCLE_SLEEP,
        idle_sleep=PORTAL_IDLE_SLEEP,
        max_workers=3,
    )
