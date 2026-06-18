import os
import json
import logging
import time

from ..config import DATA_DIR, ANOS_PADRAO
from ..cache import is_cache_valid, save_json
from ..fetcher import fetch_paginated, fetch_single

_log = logging.getLogger("CAMARA")


def fetch_proposicoes_ano(ano, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes")

    os.makedirs(data_dir, exist_ok=True)

    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"

    def params_fn(pagina):
        return {
            "ano": ano,
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "id",
            "pagina": pagina,
        }

    def filepath_template(pagina):
        return os.path.join(data_dir, f"{ano}_pagina{pagina}.json")

    return fetch_paginated(
        url=url,
        filepath_template=filepath_template,
        params_fn=params_fn,
        rate_limit=0.1,
        timeout=30,
        log_label="proposições ano=%s" % ano,
        logger=_log,
    )


def fetch_proposicoes_deputado(deputado_id, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes", "deputados")

    os.makedirs(data_dir, exist_ok=True)

    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"

    def params_fn(pagina):
        return {
            "idDeputadoAutor": deputado_id,
            "itens": 100,
            "ordem": "ASC",
            "ordenarPor": "id",
            "pagina": pagina,
        }

    def filepath_template(pagina):
        return os.path.join(data_dir, f"{deputado_id}_pagina{pagina}.json")

    return fetch_paginated(
        url=url,
        filepath_template=filepath_template,
        params_fn=params_fn,
        rate_limit=0.1,
        timeout=30,
        log_label="proposições do deputado %s" % deputado_id,
        logger=_log,
    )


def fetch_detalhe_proposicao(proposicao_id, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes", "detalhes")

    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{proposicao_id}.json")

    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao_id}"
    return fetch_single(
        url, filepath, timeout=15,
        log_label="detalhes da proposição %s" % proposicao_id,
        logger=_log,
    )


def fetch_autores_proposicao(proposicao_id, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes", "autores")

    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{proposicao_id}.json")

    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao_id}/autores"
    return fetch_single(
        url, filepath, timeout=15,
        log_label="autores da proposição %s" % proposicao_id,
        logger=_log,
    )


def fetch_proposicoes_todas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "proposicoes")

    for ano in ANOS_PADRAO:
        _log.info("Baixando proposições do ano %s...", ano)
        try:
            fetch_proposicoes_ano(ano, data_dir=data_dir)
        except Exception as e:
            _log.error("Erro ao baixar proposições do ano %s: %s", ano, e)
            continue
