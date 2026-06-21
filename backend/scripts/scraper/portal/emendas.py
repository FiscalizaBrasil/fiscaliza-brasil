import os
import json
import time
import logging
import requests
from datetime import datetime

from ..config import DATA_DIR
from ..cache import is_cache_valid, save_json, remover_acentos
from ..rate_limiter import portal_limiter

_log = logging.getLogger("PORTAL")


def fetch_emendas_parlamentar(nome_autor, ano=None, pagina=1, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "portal", "emendas")

    os.makedirs(data_dir, exist_ok=True)

    nome_sem_acento = remover_acentos(nome_autor)
    nome_sanitizado = nome_sem_acento.replace(" ", "_").replace("/", "_").upper()

    if ano is not None:
        filepath = os.path.join(data_dir, f"{nome_sanitizado}_{ano}_pagina{pagina}.json")
    else:
        filepath = os.path.join(data_dir, f"{nome_sanitizado}_pagina{pagina}.json")

    if is_cache_valid(filepath):
        _log.info("Cache válido: %s", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        _log.warning("API_KEY não configurada. Defina a variável de ambiente API_KEY.")
        return {"emendas": []}

    url = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    params = {"nomeAutor": nome_sem_acento.upper(), "pagina": pagina}
    if ano is not None:
        params["ano"] = ano
    headers = {"accept": "*/*", "chave-api-dados": api_key}

    _log.info("Buscando emendas de %s (ano=%s, página %s)...",
              nome_autor.upper(), ano or "todos", pagina)

    max_retries = 3
    for attempt in range(max_retries):
        portal_limiter.acquire()
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            if not isinstance(data, list) or len(data) == 0:
                return {"emendas": []}

            result = {"emendas": data}
            save_json(result, filepath)
            return result
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code if response is not None else 0
            if status_code == 403 and attempt < max_retries - 1:
                wait = 2 ** attempt * 5
                _log.warning("403 para %s (ano=%s), tentativa %d/%d, aguardando %ds...",
                             nome_autor, ano or "todos", attempt + 1, max_retries, wait)
                time.sleep(wait)
                continue
            _log.error("Erro ao buscar emendas de %s: %s", nome_autor, e)
            return {"emendas": [], "_error_403": status_code == 403}
        except Exception as e:
            _log.error("Erro ao buscar emendas de %s: %s", nome_autor, e)
            return {"emendas": []}

    return {"emendas": [], "_error_403": True}


def fetch_emendas_todas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "portal", "emendas")

    nomes_parlamentares = set()

    dep_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if os.path.isfile(dep_path):
        with open(dep_path, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
        for dep in dep_data.get("dados", []):
            nome = dep.get("nome", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)

    sen_path = os.path.join(DATA_DIR, "senado", "senadores.json")
    if os.path.isfile(sen_path):
        with open(sen_path, "r", encoding="utf-8") as f:
            sen_data = json.load(f)
        parlamentares = (
            sen_data.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        for par in parlamentares:
            ident = par.get("IdentificacaoParlamentar", {})
            nome = ident.get("NomeParlamentar", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)

    _log.info("Buscando emendas para %d parlamentares...", len(nomes_parlamentares))

    ano_atual = datetime.now().year

    for nome in sorted(nomes_parlamentares):
        nome_sem_acento = remover_acentos(nome)
        nome_sanitizado = nome_sem_acento.replace(" ", "_").replace("/", "_")

        for ano in range(2015, ano_atual + 1):
            pagina1_path = os.path.join(data_dir, f"{nome_sanitizado}_{ano}_pagina1.json")

            if os.path.isfile(pagina1_path) and is_cache_valid(pagina1_path):
                continue

            _log.info("Buscando dados de %s ano=%s", nome, ano)
            pagina = 1
            while True:
                result = fetch_emendas_parlamentar(nome, ano=ano, pagina=pagina, data_dir=data_dir)
                emendas = result.get("emendas", [])
                if not emendas:
                    break
                pagina += 1
                if pagina > 50:
                    break
