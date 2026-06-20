import logging
import requests

from .cache import load_json_if_valid, save_json
from .rate_limiter import get_limiter_for_url


def _parse_total_paginas_from_last_link(links, current_total):
    for link in (links or []):
        if link.get("rel") == "last":
            href = link.get("href", "")
            if "pagina=" in href:
                return int(href.split("pagina=")[-1].split("&")[0])
    return current_total


def fetch_paginated(
    url,
    filepath_template,
    params_fn,
    timeout=30,
    headers=None,
    items_field="dados",
    log_label="dados",
    logger=None,
):
    if headers is None:
        headers = {"accept": "application/json"}

    if logger is None:
        logger = logging.getLogger()

    limiter = get_limiter_for_url(url)
    resultados = {}
    pagina = 1
    total_paginas = 1

    while pagina <= total_paginas:
        filepath = filepath_template(pagina)
        cached = load_json_if_valid(filepath)
        if cached is not None:
            resultados[pagina] = cached
            total_paginas = _parse_total_paginas_from_last_link(
                cached.get("links", []), total_paginas
            )
            pagina += 1
            continue

        params = params_fn(pagina)
        logger.info("Buscando %s pagina=%s...", log_label, pagina)
        try:
            limiter.acquire()
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            save_json(data, filepath)
            resultados[pagina] = data

            total_paginas = _parse_total_paginas_from_last_link(
                data.get("links", []), total_paginas
            )
            pagina += 1
        except Exception as e:
            logger.error("Erro ao buscar %s pagina=%s: %s", log_label, pagina, e)
            break

    return resultados


def fetch_single(
    url,
    filepath,
    headers=None,
    timeout=15,
    log_label="dados",
    logger=None,
):
    if headers is None:
        headers = {"accept": "application/json"}

    if logger is None:
        logger = logging.getLogger()

    cached = load_json_if_valid(filepath)
    if cached is not None:
        return cached

    logger.info("Buscando %s...", log_label)
    try:
        limiter = get_limiter_for_url(url)
        limiter.acquire()
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        save_json(data, filepath)
        return data
    except Exception as e:
        logger.warning("Erro ao buscar %s: %s", log_label, e)
        return {}
