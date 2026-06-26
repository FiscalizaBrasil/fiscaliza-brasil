import os
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import DATA_DIR, LEGISLATURAS, SENADO_LEGISLATURAS, SENADO_ANO_INICIO
from .cache import is_cache_valid
from .camara.deputados import fetch_deputados_camara
from .camara.despesas import fetch_despesas_deputado
from .camara.detalhes import fetch_detalhes_deputado
from .camara.historico import fetch_historico_deputado
from .senado.senadores import fetch_senadores_legislatura
from .senado.despesas import fetch_despesas_senado_ano
from database.utils import legislatura_anos_lista

_log = logging.getLogger("PIPELINE")

CAMARA_WORKERS = 6
SENADO_WORKERS = 2


def _carregar_deputados_legislatura(leg: int) -> list:
    filepath = os.path.join(DATA_DIR, "camara", "deputados", f"legislatura_{leg}.json")
    if not is_cache_valid(filepath):
        _log.info("Baixando lista de deputados da legislatura %d...", leg)
        fetch_deputados_camara(legislatura=leg)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("dados", [])


def _carregar_senadores_legislatura(leg: int) -> list:
    filepath = os.path.join(DATA_DIR, "senado", "senadores", f"legislatura_{leg}.json")
    if not is_cache_valid(filepath):
        _log.info("Baixando lista de senadores da legislatura %d...", leg)
        fetch_senadores_legislatura(leg)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    parlamentares = []
    for key in data:
        if isinstance(data[key], dict):
            items = data[key].get("Parlamentares", {}).get("Parlamentar", [])
            if items:
                parlamentares = items
                break
    for par in parlamentares:
        par["idLegislatura"] = leg
    return parlamentares


def _baixar_dados_deputado(dep, leg: int):
    dep_id = dep["id"]
    anos = legislatura_anos_lista(leg)

    desp_dir = os.path.join(DATA_DIR, "camara", "deputados", str(dep_id), "despesas", str(leg))
    existe = os.path.isdir(desp_dir) and all(
        is_cache_valid(os.path.join(desp_dir, f"{ano}.json")) or os.path.isfile(os.path.join(desp_dir, f"{ano}.json"))
        for ano in anos
    )
    if not existe:
        _log.debug("Baixando despesas deputado %d legislatura %d...", dep_id, leg)
        fetch_despesas_deputado(dep_id, anos=anos, id_legislatura=leg)

    detalhes_file = os.path.join(DATA_DIR, "camara", "deputados", str(dep_id), "detalhes.json")
    if not is_cache_valid(detalhes_file):
        _log.debug("Baixando detalhes deputado %d...", dep_id)
        fetch_detalhes_deputado(dep_id)

    historico_file = os.path.join(DATA_DIR, "camara", "deputados", str(dep_id), "historico.json")
    if not is_cache_valid(historico_file):
        _log.debug("Baixando historico deputado %d...", dep_id)
        fetch_historico_deputado(dep_id)


def _baixar_despesas_senado_anos(leg: int):
    anos = legislatura_anos_lista(leg)
    for ano in anos:
        if ano < SENADO_ANO_INICIO:
            continue
        filepath = os.path.join(DATA_DIR, "senado", "despesas", f"{ano}.json")
        if not is_cache_valid(filepath):
            _log.info("Baixando despesas CEAPS ano %d...", ano)
            fetch_despesas_senado_ano(ano)


def _carregar_expenses_cache(leg: int) -> dict:
    cache = {}
    anos = legislatura_anos_lista(leg)
    for ano in anos:
        if ano < SENADO_ANO_INICIO:
            continue
        filepath = os.path.join(DATA_DIR, "senado", "despesas", f"{ano}.json")
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            despesas_lista = data.get("despesas", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            sen_map = {}
            for d in despesas_lista:
                cod = d.get("codSenador")
                if cod:
                    cod = int(cod)
                    if cod not in sen_map:
                        sen_map[cod] = []
                    sen_map[cod].append(d)
            cache[ano] = sen_map
    return cache


def _salvar_falhos(falhos: list, legislatura: int):
    if not falhos:
        return
    failed_dir = os.path.join(DATA_DIR, "failed")
    os.makedirs(failed_dir, exist_ok=True)
    filepath = os.path.join(failed_dir, "mandatos_falhos_import.json")

    existing = []
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing = json.load(f).get("falhos", [])
        except Exception:
            pass

    all_falhos = existing + falhos
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "falhos": all_falhos,
            "total": len(all_falhos),
            "ultima_legislatura": legislatura,
        }, f, ensure_ascii=False, indent=2)
    _log.warning("%d mandato(s) falharam na legislatura %d. Total acumulado: %d.", len(falhos), legislatura, len(all_falhos))


def _agregar_arquivos_legislaturas():
    from .cache import save_json

    camara_dir = os.path.join(DATA_DIR, "camara", "deputados")
    todos = []
    for leg in LEGISLATURAS:
        fpath = os.path.join(camara_dir, f"legislatura_{leg}.json")
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for dep in data.get("dados", []):
                dep["idLegislatura"] = leg
                todos.append(dep)

    if todos:
        filepath = os.path.join(DATA_DIR, "camara", "deputados.json")
        save_json({"dados": todos}, filepath)
        _log.info("deputados.json agregado: %d registros.", len(todos))

    senado_dir = os.path.join(DATA_DIR, "senado", "senadores")
    todos_sen = []
    codigos = set()
    for leg in SENADO_LEGISLATURAS:
        fpath = os.path.join(senado_dir, f"legislatura_{leg}.json")
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            parlamentares = []
            for key in data:
                if isinstance(data[key], dict):
                    items = data[key].get("Parlamentares", {}).get("Parlamentar", [])
                    if items:
                        parlamentares = items
                        break
            for par in parlamentares:
                ident = par.get("IdentificacaoParlamentar", {}).get("CodigoParlamentar", "")
                if ident:
                    codigos.add(str(ident))
                par["idLegislatura"] = leg
                todos_sen.append(par)

    if todos_sen:
        filepath = os.path.join(DATA_DIR, "senado", "senadores.json")
        resultado = {
            "ListaParlamentarEmExercicio": {
                "Parlamentares": {
                    "Parlamentar": todos_sen
                }
            }
        }
        save_json(resultado, filepath)
        _log.info("senadores.json agregado: %d registros de %d senadores.", len(todos_sen), len(codigos))


def _processar_legislatura(deputados: list, senadores: list, leg: int) -> list:
    from scripts.import_data import _importar_mandato_camara, _importar_mandato_senado

    falhos_lock = threading.Lock()
    falhos = []

    def _add_falho(f):
        with falhos_lock:
            falhos.append(f)

    camara_pronto = threading.Event()
    senado_pronto = threading.Event()

    def _camara_producer():
        _log.info("Camara legislatura %d: baixando e importando %d deputados (%d workers)...", leg, len(deputados), CAMARA_WORKERS)
        with ThreadPoolExecutor(max_workers=CAMARA_WORKERS) as camara_pool:
            camara_futures = []
            for dep in deputados:
                dep_id = dep.get("id")
                if not dep_id:
                    continue
                dep["idLegislatura"] = leg
                try:
                    _baixar_dados_deputado(dep, leg)
                except Exception as e:
                    _log.error("Falha ao baixar dados deputado %d: %s", dep_id, e)
                    _add_falho({
                        "tipo": "camara",
                        "deputado_id": dep_id,
                        "legislatura_id": leg,
                        "nome": dep.get("nome", ""),
                        "erro": str(e)[:500],
                    })
                    continue
                fut = camara_pool.submit(_importar_mandato_camara, dep)
                camara_futures.append((fut, dep))

            for fut, dep in camara_futures:
                try:
                    result = fut.result()
                    if result:
                        _log.debug("OK deputado %d leg %d", result["deputado_id"], result["legislatura_id"])
                except Exception as e:
                    dep_id = dep.get("id", 0)
                    _log.error("FALHA deputado %d legislatura %d: %s", dep_id, leg, e)
                    _add_falho({
                        "tipo": "camara",
                        "deputado_id": dep_id,
                        "legislatura_id": leg,
                        "nome": dep.get("nome", ""),
                        "erro": str(e)[:500],
                    })
        camara_pronto.set()

    def _senado_producer():
        _log.info("Senado legislatura %d: baixando CEAPS...", leg)
        try:
            _baixar_despesas_senado_anos(leg)
        except Exception as e:
            _log.error("Falha ao baixar CEAPS legislatura %d: %s", leg, e)
        expenses_cache = _carregar_expenses_cache(leg)

        senadores_para_submeter = []
        for sen in senadores:
            codigo = int(sen.get("IdentificacaoParlamentar", {}).get("CodigoParlamentar", 0))
            if codigo:
                sen["idLegislatura"] = leg
                senadores_para_submeter.append(sen)

        _log.info("Senado legislatura %d: importando %d senadores (%d workers)...", leg, len(senadores_para_submeter), SENADO_WORKERS)
        with ThreadPoolExecutor(max_workers=SENADO_WORKERS) as senado_pool:
            senado_futures = []
            for sen in senadores_para_submeter:
                fut = senado_pool.submit(_importar_mandato_senado, sen, expenses_cache)
                senado_futures.append((fut, sen))

            for fut, sen in senado_futures:
                try:
                    result = fut.result()
                    if result:
                        _log.debug("OK senador %d leg %d", result["codigo_parlamentar"], result["legislatura_id"])
                except Exception as e:
                    codigo = int(sen.get("IdentificacaoParlamentar", {}).get("CodigoParlamentar", 0))
                    _log.error("FALHA senador %d legislatura %d: %s", codigo, leg, e)
                    _add_falho({
                        "tipo": "senado",
                        "codigo_parlamentar": codigo,
                        "legislatura_id": leg,
                        "nome": sen.get("IdentificacaoParlamentar", {}).get("NomeParlamentar", ""),
                        "erro": str(e)[:500],
                    })
        senado_pronto.set()

    t_camara = threading.Thread(target=_camara_producer, daemon=True, name=f"camara-leg-{leg}")
    t_senado = threading.Thread(target=_senado_producer, daemon=True, name=f"senado-leg-{leg}")
    t_camara.start()
    t_senado.start()

    t_camara.join()
    t_senado.join()

    return falhos


def run_pipeline():
    _log.info("=== PIPELINE INICIADA ===")

    for leg in LEGISLATURAS:
        _log.info("--- Legislatura %d ---", leg)

        try:
            deputados = _carregar_deputados_legislatura(leg)
            _log.info("%d deputados na legislatura %d.", len(deputados), leg)
        except Exception as e:
            _log.error("Falha ao carregar deputados legislatura %d: %s", leg, e)
            continue

        try:
            senadores = _carregar_senadores_legislatura(leg)
            _log.info("%d senadores na legislatura %d.", len(senadores), leg)
        except Exception as e:
            _log.error("Falha ao carregar senadores legislatura %d: %s", leg, e)
            continue

        try:
            falhos = _processar_legislatura(deputados, senadores, leg)
            if falhos:
                _salvar_falhos(falhos, leg)
        except Exception as e:
            _log.error("Falha ao processar legislatura %d: %s", leg, e)

    _log.info("Agregando arquivos de todas as legislaturas...")
    try:
        _agregar_arquivos_legislaturas()
    except Exception as e:
        _log.error("Falha ao agregar arquivos: %s", e)

    _log.info("Importando dados complementares (proposicoes, votacoes, emendas, processos)...")
    from database import db
    conn = None
    try:
        conn = db.get_db_connection()
        if conn:
            from scripts.import_data import _importar_dados_complementares
            _importar_dados_complementares(conn)
    except Exception as e:
        _log.error("Falha ao importar dados complementares: %s", e)
    finally:
        if conn:
            try:
                db.release_db_connection(conn)
            except Exception:
                pass

    from . import worker as _worker
    _worker.import_complete.set()
    _log.info("=== PIPELINE CONCLUIDA ===")
