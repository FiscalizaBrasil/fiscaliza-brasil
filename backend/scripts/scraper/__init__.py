from .camara.deputados import (
    fetch_deputados_camara,
    fetch_deputados_todas_legislaturas,
    download_fotos_deputados,
)
from .camara.despesas import fetch_despesas_deputado, fetch_despesas_todas_camara
from .camara.proposicoes import (
    fetch_proposicoes_ano,
    fetch_proposicoes_deputado,
    fetch_detalhe_proposicao,
    fetch_autores_proposicao,
    fetch_proposicoes_todas,
)
from .camara.votacoes import (
    fetch_votacoes_ano,
    fetch_votos_votacao,
    fetch_votacoes_todas,
)
from .camara.historico import fetch_historico_deputado, fetch_historico_todos_deputados
from .camara.detalhes import fetch_detalhes_deputado, fetch_detalhes_todos_deputados

from .senado.senadores import fetch_senadores_senado, download_fotos_senadores
from .senado.despesas import fetch_despesas_senado_ano, fetch_despesas_senado_todas
from .senado.processos import (
    fetch_processos_senado_ano,
    fetch_processos_senado_todas,
    fetch_detalhe_processo_senado,
    fetch_detalhes_processos_senado,
)

from .portal.emendas import fetch_emendas_parlamentar, fetch_emendas_todas

from .lifecycle import (
    start_initial_import,
    start_background_scraper,
    stop_background_scraper,
    start_background_fotos,
    main,
)

from .config import scraping_status
