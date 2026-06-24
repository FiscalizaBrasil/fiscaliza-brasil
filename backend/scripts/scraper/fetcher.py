import logging
import time
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


def _fetch_page(url, params, headers, timeout, limiter):
    limiter.acquire()
    response = requests.get(url, params=params, headers=headers, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _fetch_page_with_retry(url, params, headers, timeout, limiter, max_retries,
                           logger, log_label, pagina):
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return _fetch_page(url, params, headers, timeout, limiter)
        except requests.exceptions.Timeout as e:
            last_error = e
        except requests.exceptions.ConnectionError as e:
            last_error = e
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if 500 <= code < 600:
                last_error = e
            else:
                raise

        if attempt < max_retries:
            wait = min(2 ** attempt, 60)
            logger.warning(
                "Retry %d/%d para %s pagina=%s apos %ds: %s",
                attempt + 1, max_retries, log_label, pagina, wait, last_error,
            )
            time.sleep(wait)

    raise last_error


def fetch_paginated(
    url,
    filepath,
    params_fn,
    timeout=30,
    headers=None,
    items_field="dados",
    log_label="dados",
    logger=None,
    max_retries=0,
):
    if headers is None:
        headers = {"accept": "application/json"}

    if logger is None:
        logger = logging.getLogger()

    cached = load_json_if_valid(filepath)
    if cached is not None:
        if cached.get("_incomplete"):
            logger.info("Cache incompleto em %s. Retomando da pagina %s...",
                        filepath, cached.get("_pagina", 0) + 1)
            all_items = cached.get(items_field, [])
            pagina = cached.get("_pagina", 0) + 1
            total_paginas = cached.get("_total_paginas", 1)
            got_any_page = True
        else:
            return cached
    else:
        all_items = []
        pagina = 1
        total_paginas = 1
        got_any_page = False

    limiter = get_limiter_for_url(url)

    while pagina <= total_paginas:
        params = params_fn(pagina)
        logger.info("Buscando %s pagina=%s...", log_label, pagina)
        try:
            if max_retries > 0:
                data = _fetch_page_with_retry(
                    url, params, headers, timeout, limiter,
                    max_retries, logger, log_label, pagina,
                )
            else:
                data = _fetch_page(url, params, headers, timeout, limiter)

            items = data.get(items_field, [])
            all_items.extend(items)
            got_any_page = True

            if pagina == 1:
                total_paginas = _parse_total_paginas_from_last_link(
                    data.get("links", []), total_paginas
                )

            save_json({
                items_field: all_items,
                "_incomplete": True,
                "_pagina": pagina,
                "_total_paginas": total_paginas,
            }, filepath)

            pagina += 1
        except Exception as e:
            logger.error("Erro ao buscar %s pagina=%s: %s", log_label, pagina, e)
            break

    if got_any_page:
        result = {items_field: all_items}
        save_json(result, filepath)

    return {items_field: all_items, "_error": not got_any_page}


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
