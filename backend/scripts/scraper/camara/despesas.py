import os
import json
import logging
import random

from ..config import DATA_DIR, ANOS_PADRAO
from ..cache import is_cache_valid
from ..fetcher import fetch_paginated
from ..verification import is_verified

_log = logging.getLogger("CAMARA")


def _anos_legislatura(id_legislatura):
    """Calcula os anos cobertos por uma legislatura."""
    ano_inicio = 2023 - (57 - id_legislatura) * 4
    return list(range(ano_inicio, ano_inicio + 4))


def fetch_despesas_deputado(deputado_id, anos=None, id_legislatura=None, data_dir=None):
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
            params = {
                "ano": ano,
                "itens": 100,
                "ordem": "ASC",
                "ordenarPor": "ano",
                "pagina": pagina,
            }
            if id_legislatura is not None:
                params["idLegislatura"] = id_legislatura
            return params

        if id_legislatura is not None:
            leg_dir = os.path.join(dep_dir, str(id_legislatura))
            os.makedirs(leg_dir, exist_ok=True)
            filepath = os.path.join(leg_dir, f"{ano}.json")
        else:
            filepath = os.path.join(dep_dir, f"{ano}.json")

        ano_resultados = fetch_paginated(
            url=url,
            filepath=filepath,
            params_fn=params_fn,
            timeout=30,
            headers=headers,
            items_field="dados",
            log_label="despesas dep=%s leg=%s ano=%s" % (deputado_id, id_legislatura or "N/A", ano),
            logger=_log,
        )
        resultados[ano] = ano_resultados

    return resultados


def _load_deputados_all():
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


def fetch_despesas_todas_camara(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")

    dados = _load_deputados_all()
    if not dados:
        _log.warning("Nenhum deputado na lista.")
        return

    random.shuffle(dados)

    for dep in dados:
        dep_id = dep["id"]
        id_leg = dep.get("idLegislatura")
        if not id_leg:
            continue

        if is_verified("camara_despesas", f"{dep_id}_{id_leg}"):
            continue

        anos = _anos_legislatura(id_leg)
        dep_dir = os.path.join(data_dir, str(dep_id))
        leg_dir = os.path.join(dep_dir, str(id_leg))

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
            continue

        _log.info("Baixando despesas do deputado %s (%s) legislatura %s", dep_id, dep.get("nome", ""), id_leg)
        try:
            fetch_despesas_deputado(dep_id, anos=anos, id_legislatura=id_leg, data_dir=data_dir)
        except Exception as e:
            _log.error("Erro ao baixar despesas do deputado %s: %s", dep_id, e)
            continue
