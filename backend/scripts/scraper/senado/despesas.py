import os
import json
import logging
import requests
from datetime import datetime

from ..config import DATA_DIR, SENADO_ANO_INICIO
from ..cache import is_cache_valid, save_json
from ..rate_limiter import senado_adm_limiter

_log = logging.getLogger("SENADO")


def fetch_despesas_senado_ano(ano, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "despesas")

    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{ano}.json")

    if is_cache_valid(filepath):
        _log.info("Cache válido: %s", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"
    headers = {"accept": "application/json"}

    _log.info("Buscando despesas CEAPS para %s...", ano)
    try:
        senado_adm_limiter.acquire()
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        save_json(data, filepath)
        return data
    except Exception as e:
        _log.error("Erro ao buscar despesas CEAPS %s: %s", ano, e)
        return {}


def fetch_despesas_senado_todas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "despesas")

    ano_atual = datetime.now().year
    for ano in range(ano_atual, SENADO_ANO_INICIO - 1, -1):
        fetch_despesas_senado_ano(ano, data_dir=data_dir)
