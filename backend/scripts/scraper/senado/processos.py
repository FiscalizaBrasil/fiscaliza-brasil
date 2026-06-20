import os
import json
import logging
import requests

from ..config import DATA_DIR, ANOS_PADRAO
from ..cache import is_cache_valid, save_json
from ..rate_limiter import senado_legis_limiter

_log = logging.getLogger("SENADO")


def fetch_processos_senado_ano(ano, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "processos")

    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{ano}.json")

    if is_cache_valid(filepath):
        _log.info("Cache válido: %s", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = "https://legis.senado.leg.br/dadosabertos/processo"
    params = {"ano": ano, "siglaEnteIdentificador": "SF", "v": "1"}
    headers = {"accept": "application/json"}

    _log.info("Buscando processos para ano=%s...", ano)
    try:
        senado_legis_limiter.acquire()
        response = requests.get(url, params=params, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            _log.warning("Resposta inesperada para ano=%s: tipo %s", ano, type(data).__name__)
            data = []

        save_json(data, filepath)
        _log.info("  -> %d processos encontrados para %s", len(data), ano)
        return data
    except Exception as e:
        _log.error("Erro ao buscar processos ano=%s: %s", ano, e)
        return []


def fetch_processos_senado_todas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "processos")

    for ano in ANOS_PADRAO:
        _log.info("Baixando processos para ano %s...", ano)
        try:
            fetch_processos_senado_ano(ano, data_dir=data_dir)
        except Exception as e:
            _log.error("Erro ao baixar processos do ano %s: %s", ano, e)
            continue


def fetch_detalhe_processo_senado(processo_id, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "processos", "detalhes")

    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{processo_id}.json")

    if is_cache_valid(filepath):
        _log.info("Cache válido: %s", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://legis.senado.leg.br/dadosabertos/processo/{processo_id}?v=1"
    headers = {"accept": "application/json"}

    _log.info("Buscando detalhes do processo %s...", processo_id)
    try:
        senado_legis_limiter.acquire()
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        save_json(data, filepath)
        return data
    except Exception as e:
        _log.warning("Erro ao buscar detalhes do processo %s: %s", processo_id, e)
        return {}


def fetch_detalhes_processos_senado(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "processos")

    if not os.path.isdir(data_dir):
        _log.warning("Diretório de processos não encontrado.")
        return

    todos_processos = []
    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json") or fname.startswith("detalhes"):
            continue
        filepath = os.path.join(data_dir, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            for proc in data:
                proc_id = proc.get("id")
                if proc_id:
                    todos_processos.append(proc_id)

    _log.info("Buscando detalhes de %d processos...", len(todos_processos))

    detalhes_dir = os.path.join(data_dir, "detalhes")
    os.makedirs(detalhes_dir, exist_ok=True)

    for proc_id in sorted(todos_processos):
        filepath = os.path.join(detalhes_dir, f"{proc_id}.json")
        if os.path.isfile(filepath) and is_cache_valid(filepath):
            continue
        fetch_detalhe_processo_senado(proc_id, data_dir=detalhes_dir)
