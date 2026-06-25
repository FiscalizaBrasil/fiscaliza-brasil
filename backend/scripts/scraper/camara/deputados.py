import os
import json
import logging
import requests

from ..config import DATA_DIR, CAMARA_API_BASE, LEGISLATURAS
from ..cache import is_cache_valid, save_json, download_foto
from ..rate_limiter import camara_limiter
from .detalhes import fetch_detalhes_deputado

_log = logging.getLogger("CAMARA")


def fetch_deputados_camara(data_dir=None, legislatura=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara")

    if legislatura:
        filepath = os.path.join(data_dir, "deputados", f"legislatura_{legislatura}.json")
    else:
        filepath = os.path.join(data_dir, "deputados.json")

    if is_cache_valid(filepath):
        _log.info(
            "Cache válido%s. Pulando download.",
            " (leg %s)" % legislatura if legislatura else "",
        )
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"{CAMARA_API_BASE}/deputados"
    headers = {"accept": "application/json"}

    todos_dados = []
    pagina = 1
    total_paginas = 1

    while pagina <= total_paginas:
        params = {"ordem": "ASC", "ordenarPor": "nome", "itens": 1000, "pagina": pagina}
        if legislatura:
            params["idLegislatura"] = legislatura

        _log.info(
            "Buscando deputados%s - página %s...",
            " (legislatura %s)" % legislatura if legislatura else "",
            pagina,
        )
        camara_limiter.acquire()
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

        dados = data.get("dados", [])
        todos_dados.extend(dados)

        links = data.get("links", [])
        for link in links:
            if link.get("rel") == "last":
                href = link.get("href", "")
                if "pagina=" in href:
                    total_paginas = int(href.split("pagina=")[-1].split("&")[0])
                break

        _log.info("  -> Página %s/%s: %d deputados encontrados", pagina, total_paginas, len(dados))
        pagina += 1

    resultado = {"dados": todos_dados}
    if links:
        resultado["links"] = links

    _log.info("Total: %d deputados encontrados em %s página(s).", len(todos_dados), total_paginas)
    save_json(resultado, filepath)
    return resultado


def fetch_deputados_todas_legislaturas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara")

    todos_dados = []
    ids_unicos = set()

    for leg in LEGISLATURAS:
        _log.info("Buscando deputados da legislatura %s...", leg)
        try:
            data = fetch_deputados_camara(data_dir=data_dir, legislatura=leg)
            dados = data.get("dados", [])
            for dep in dados:
                dep_id = dep.get("id")
                nome = dep.get("nome")

                if not nome:
                    if dep_id:
                        try:
                            detail = fetch_detalhes_deputado(dep_id)
                            nome = (
                                detail.get("dados", {}).get("ultimoStatus", {}).get("nomeEleitoral")
                                or detail.get("dados", {}).get("ultimoStatus", {}).get("nome")
                            )
                            if nome:
                                dep["nome"] = nome
                                _log.info("  -> Nome resolvido via API individual para deputado %s: %s", dep_id, nome)
                            else:
                                _log.warning("  -> Deputado %s sem nome (bulk e individual), pulando.", dep_id)
                                continue
                        except Exception as e:
                            _log.warning("  -> Erro ao resolver nome do deputado %s: %s. Pulando.", dep_id, e)
                            continue
                    else:
                        continue

                if dep_id:
                    ids_unicos.add(dep_id)
                dep["idLegislatura"] = leg
                todos_dados.append(dep)
            _log.info("  -> %d registros de deputados na legislatura %s", len(dados), leg)
        except Exception as e:
            _log.error("Erro ao buscar legislatura %s: %s", leg, e)

    combined = {"dados": todos_dados}
    filepath = os.path.join(data_dir, "deputados.json")
    save_json(combined, filepath)

    _log.info(
        "Total combinado: %d registros de %d deputados únicos em %d legislaturas.",
        len(todos_dados), len(ids_unicos), len(LEGISLATURAS),
    )
    return combined


def download_fotos_deputados(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara")

    json_path = os.path.join(data_dir, "deputados.json")
    if not os.path.isfile(json_path):
        _log.warning("Arquivo de deputados não encontrado.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dados = data.get("dados", [])
    fotos_dir = os.path.join(DATA_DIR, "fotos", "camara")

    _log.info("Baixando fotos de %d deputados...", len(dados))
    for dep in dados:
        dep_id = dep["id"]
        url_foto = dep.get("urlFoto", "")
        if not url_foto:
            continue
        ext = os.path.splitext(url_foto.split("?")[0])[1] or ".jpg"
        filepath = os.path.join(fotos_dir, f"{dep_id}{ext}")
        download_foto(url_foto, filepath)
