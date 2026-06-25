import requests
import logging
import time
import json
import os

_log = logging.getLogger(__name__)

_tipos_camara: dict[str, str] = {}
_tipos_senado: dict[str, str] = {}
_camara_fetched_at: float = 0
_camara_fetched = False
_senado_fetched = False


def fetch_tipos_camara():
    global _tipos_camara, _camara_fetched_at, _camara_fetched
    if _camara_fetched:
        return
    url = "https://dadosabertos.camara.leg.br/api/v2/referencias/tiposProposicao"
    try:
        response = requests.get(url, headers={"accept": "application/json"}, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "dados" in data:
            _tipos_camara = {item["sigla"]: item["nome"].strip() for item in data["dados"]}
        _camara_fetched_at = time.time()
        _camara_fetched = True
        _log.info("Tipos de proposicao da Camara carregados: %d siglas", len(_tipos_camara))
    except Exception as e:
        _log.error("Erro ao buscar tipos de proposicao da Camara: %s", e)


def get_tipos_camara() -> dict[str, str]:
    return _tipos_camara


def fetch_tipos_senado():
    global _tipos_senado, _senado_fetched
    if _senado_fetched:
        return

    try:
        from database.db import db_cursor
        with db_cursor() as cursor:
            cursor.execute("SELECT DISTINCT sigla FROM senado.materia WHERE sigla IS NOT NULL AND sigla != ''")
            siglas = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        _log.warning("Nao foi possivel consultar siglas do Senado no banco: %s", e)
        siglas = []

    sigla_names: dict[str, str] = {}

    if siglas:
        sigla_names = _build_senado_from_detalhes(set(siglas))
    else:
        sigla_names = _build_senado_from_detalhes()

    _tipos_senado = sigla_names
    _senado_fetched = True
    _log.info("Tipos de materia do Senado carregados: %d siglas", len(_tipos_senado))


def _build_senado_from_detalhes(siglas: set[str] | None = None) -> dict[str, str]:
    from scripts.scraper.config import DATA_DIR

    processos_dir = os.path.join(DATA_DIR, "senado", "processos")
    if not os.path.isdir(processos_dir):
        return {}

    names: dict[str, str] = {}
    for fname in sorted(os.listdir(processos_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(processos_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            sigla = (data.get("sigla") or "").strip()
            descricao = (data.get("descricaoSigla") or "").strip()
            if sigla and descricao and sigla not in names:
                if siglas is None or sigla in siglas:
                    names[sigla] = descricao
        except Exception:
            pass

    return names


def get_tipos_senado() -> dict[str, str]:
    return _tipos_senado
