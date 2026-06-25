import os
import json
import logging
import requests

from ..config import DATA_DIR, SENADO_LEGISLATURAS
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


def fetch_senadores_legislatura(legislatura, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "senadores")

    filepath = os.path.join(data_dir, f"legislatura_{legislatura}.json")

    if is_cache_valid(filepath):
        _log.info("Cache válido para senadores legislatura %s. Pulando download.", legislatura)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"https://legis.senado.leg.br/dadosabertos/senador/lista/legislatura/{legislatura}"
    params = {"participacao": "T", "v": "4"}
    headers = {"accept": "application/json"}

    _log.info("Buscando senadores da legislatura %s...", legislatura)
    senado_legis_limiter.acquire()
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    save_json(data, filepath)
    return data


def _extrair_parlamentares(data):
    """Extrai a lista de parlamentares independente do wrapper da resposta."""
    for key in data:
        if isinstance(data[key], dict):
            parlamentares = (
                data[key]
                .get("Parlamentares", {})
                .get("Parlamentar", [])
            )
            if parlamentares:
                return parlamentares
    return []


def fetch_senadores_todas_legislaturas(data_dir=None):
    """Baixa senadores de todas as legislaturas e aglutina em um único senadores.json."""
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado")

    todos = []
    codigos_unicos = set()

    for leg in SENADO_LEGISLATURAS:
        _log.info("Buscando senadores da legislatura %s...", leg)
        try:
            data = fetch_senadores_legislatura(leg, data_dir=data_dir)
            parlamentares = _extrair_parlamentares(data)
            for par in parlamentares:
                ident = par.get("IdentificacaoParlamentar", {})
                codigo = ident.get("CodigoParlamentar", "")
                if codigo:
                    codigos_unicos.add(str(codigo))
                par["idLegislatura"] = leg
                todos.append(par)
            _log.info("  -> %d registros de senadores na legislatura %s", len(parlamentares), leg)
        except Exception as e:
            _log.error("Erro ao buscar legislatura %s: %s", leg, e)

    resultado = {
        "ListaParlamentarEmExercicio": {
            "Parlamentares": {
                "Parlamentar": todos
            }
        }
    }
    filepath = os.path.join(data_dir, "senadores.json")
    save_json(resultado, filepath)

    _log.info(
        "Total combinado: %d registros de %d senadores únicos em %d legislaturas.",
        len(todos), len(codigos_unicos), len(SENADO_LEGISLATURAS),
    )
    return resultado


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
