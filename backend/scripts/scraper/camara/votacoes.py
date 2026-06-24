import os
import logging
from datetime import datetime

from ..config import DATA_DIR, ANOS_PADRAO
from ..cache import load_json_if_valid, save_json
from ..fetcher import fetch_paginated

_log = logging.getLogger("CAMARA")

QUADRIMESTERS = [
    ("{ano}-01-01", "{ano}-04-30"),
    ("{ano}-05-01", "{ano}-08-31"),
    ("{ano}-09-01", "{ano}-12-31"),
]


def fetch_votacoes_ano(ano, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "votacoes")

    os.makedirs(data_dir, exist_ok=True)

    ano_atual = datetime.now().year
    merged_path = os.path.join(data_dir, f"{ano}.json")

    # Anos passados: cache do consolidado bate direto
    if ano < ano_atual:
        cached = load_json_if_valid(merged_path)
        if cached is not None:
            return cached

    url = "https://dadosabertos.camara.leg.br/api/v2/votacoes"
    all_items = []
    all_failed = True

    for i, (data_inicio_fmt, data_fim_fmt) in enumerate(QUADRIMESTERS, 1):
        data_inicio = data_inicio_fmt.format(ano=ano)
        data_fim = data_fim_fmt.format(ano=ano)

        q_filepath = os.path.join(data_dir, f"{ano}_Q{i}.json")

        def params_fn(pagina, _di=data_inicio, _df=data_fim):
            return {
                "dataInicio": _di,
                "dataFim": _df,
                "itens": 100,
                "ordem": "ASC",
                "ordenarPor": "data",
                "pagina": pagina,
            }

        result = fetch_paginated(
            url=url,
            filepath=q_filepath,
            params_fn=params_fn,
            timeout=30,
            log_label="votações %s Q%d" % (ano, i),
            logger=_log,
            max_retries=10,
        )

        items = result.get("dados", [])
        all_items.extend(items)

        if items or not result.get("_error", False):
            all_failed = False

    if all_items or not all_failed:
        result = {"dados": all_items}

        if ano < ano_atual:
            save_json(result, merged_path)
            for i in range(1, 4):
                q_filepath = os.path.join(data_dir, f"{ano}_Q{i}.json")
                if os.path.isfile(q_filepath):
                    os.remove(q_filepath)

        return result

    return {"dados": []}


def fetch_votos_votacao(votacao_id, data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "votacoes", "votos")

    os.makedirs(data_dir, exist_ok=True)

    url = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{votacao_id}/votos"

    filepath = os.path.join(data_dir, f"{votacao_id}.json")

    return fetch_paginated(
        url=url,
        filepath=filepath,
        params_fn=lambda pagina: {"pagina": pagina, "itens": 100},
        timeout=30,
        log_label="votos da votação %s" % votacao_id,
        logger=_log,
    )


def fetch_votacoes_todas(data_dir=None):
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "votacoes")

    for ano in ANOS_PADRAO:
        _log.info("Baixando votações do ano %s...", ano)
        try:
            fetch_votacoes_ano(ano, data_dir=data_dir)
        except Exception as e:
            _log.error("Erro ao baixar votações do ano %s: %s", ano, e)
            continue
