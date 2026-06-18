import os
import json
import logging
import random

from ..config import DATA_DIR, ANOS_PADRAO
from ..cache import is_cache_valid
from ..fetcher import fetch_paginated

_log = logging.getLogger("CAMARA")


def fetch_despesas_deputado(deputado_id, anos=None, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")

    if anos is None:
        anos = list(ANOS_PADRAO)

    dep_dir = os.path.join(data_dir, str(deputado_id))
    os.makedirs(dep_dir, exist_ok=True)

    headers = {"accept": "application/json"}
    resultados = {}

    for ano in anos:
        url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado_id}/despesas"

        def params_fn(pagina):
            return {
                "ano": ano,
                "itens": 100,
                "ordem": "ASC",
                "ordenarPor": "ano",
                "pagina": pagina,
            }

        def filepath_template(pagina):
            return os.path.join(dep_dir, f"{ano}_pagina{pagina}.json")

        ano_resultados = fetch_paginated(
            url=url,
            filepath_template=filepath_template,
            params_fn=params_fn,
            rate_limit=0.05,
            timeout=30,
            headers=headers,
            items_field="dados",
            log_label="despesas dep=%s ano=%s" % (deputado_id, ano),
            logger=_log,
        )
        resultados[ano] = ano_resultados

    return resultados


def fetch_despesas_todas_camara(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")

    json_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if not os.path.isfile(json_path):
        _log.warning("Lista de deputados não encontrada.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dados = data.get("dados", [])
    if not dados:
        _log.warning("Nenhum deputado na lista.")
        return

    random.shuffle(dados)
    anos = list(ANOS_PADRAO)

    for dep in dados:
        dep_id = dep["id"]
        dep_dir = os.path.join(data_dir, str(dep_id))

        completo = True
        for ano in anos:
            ano_tem_dados = False
            if os.path.isdir(dep_dir):
                for fname in os.listdir(dep_dir):
                    if fname.startswith(f"{ano}_pagina") and fname.endswith(".json"):
                        ano_tem_dados = True
                        break
            if not ano_tem_dados:
                completo = False
                break

        if completo:
            continue

        _log.info("Baixando despesas do deputado %s (%s)", dep_id, dep.get("nome", ""))
        try:
            fetch_despesas_deputado(dep_id, anos=anos, data_dir=data_dir)
        except Exception as e:
            _log.error("Erro ao baixar despesas do deputado %s: %s", dep_id, e)
            continue
