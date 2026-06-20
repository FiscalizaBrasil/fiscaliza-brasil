import os
import json
import logging
import requests

from ..config import DATA_DIR
from ..cache import is_cache_valid, save_json, download_foto
from ..rate_limiter import senado_legis_limiter

_log = logging.getLogger("SENADO")


def fetch_senadores_senado(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado")

    filepath = os.path.join(data_dir, "senadores.json")

    if is_cache_valid(filepath):
        _log.info("Cache válido para senadores. Pulando download.")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual"
    params = {"participacao": "T", "v": "4"}
    headers = {"accept": "application/json"}

    _log.info("Buscando senadores...")
    senado_legis_limiter.acquire()
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    save_json(data, filepath)
    return data


def download_fotos_senadores(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado")

    json_path = os.path.join(data_dir, "senadores.json")
    if not os.path.isfile(json_path):
        _log.warning("Arquivo de senadores não encontrado.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    parlamentares = (
        data.get("ListaParlamentarEmExercicio", {})
        .get("Parlamentares", {})
        .get("Parlamentar", [])
    )

    fotos_dir = os.path.join(DATA_DIR, "fotos", "senado")

    _log.info("Baixando fotos de %d senadores...", len(parlamentares))
    for par in parlamentares:
        ident = par.get("IdentificacaoParlamentar", {})
        codigo = ident.get("CodigoParlamentar", "")
        url_foto = ident.get("UrlFotoParlamentar", "")
        if not codigo or not url_foto:
            continue

        ext = os.path.splitext(url_foto.split("?")[0])[1] or ".jpg"
        filepath = os.path.join(fotos_dir, f"{codigo}{ext}")
        download_foto(url_foto, filepath)
