import os
import json
import logging

from ..config import DATA_DIR
from ..cache import is_cache_valid
from ..fetcher import fetch_single

_log = logging.getLogger("CAMARA")


def fetch_historico_deputado(deputado_id, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "deputados", str(deputado_id))

    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, "historico.json")

    url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado_id}/historico"
    return fetch_single(
        url, filepath, timeout=15,
        log_label="histórico do deputado %s" % deputado_id,
        logger=_log,
    )


def fetch_historico_todos_deputados(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "deputados")

    json_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if not os.path.isfile(json_path):
        _log.warning("Lista de deputados não encontrada.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dados = data.get("dados", [])
    if not dados:
        return

    ids_unicos = set()
    for dep in dados:
        dep_id = dep.get("id")
        if dep_id:
            ids_unicos.add(dep_id)

    _log.info("Buscando histórico de %d deputados...", len(ids_unicos))

    for dep_id in sorted(ids_unicos):
        dep_dir = os.path.join(data_dir, str(dep_id))
        filepath = os.path.join(dep_dir, "historico.json")
        if os.path.isfile(filepath) and is_cache_valid(filepath):
            continue
        fetch_historico_deputado(dep_id)
