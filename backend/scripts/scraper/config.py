import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

CACHE_DURATION_SECONDS = 3600
SENADO_ULTIMO_ANO_CACHE_SECONDS = 86400

CAMARA_API_BASE = "https://dadosabertos.camara.leg.br/api/v2"
SENADO_LEGIS_API_BASE = "https://legis.senado.leg.br/dadosabertos"
SENADO_ADM_API_BASE = "https://adm.senado.gov.br/adm-dadosabertos/api/v1"
PORTAL_API_BASE = "https://api.portaldatransparencia.gov.br/api-de-dados"

ANOS_PADRAO = list(range(2026, 1986, -1))
LEGISLATURAS = [57, 56, 55]

# Senado despesas: ano mais antigo disponível na API
SENADO_ANO_INICIO = 2008

# Rate limits globais (requisições/segundo, soma de todas as threads)
CAMARA_RATE_LIMIT = 10         # dadosabertos.camara.leg.br
SENADO_LEGIS_RATE_LIMIT = 5    # legis.senado.leg.br
SENADO_ADM_RATE_LIMIT = 1      # adm.senado.gov.br (API lenta, ~10MB/resposta)
PORTAL_RATE_LIMIT = 5          # api.portaldatransparencia.gov.br

# Status global de scraping (compartilhado entre worker e API)
import threading
_status_lock = threading.Lock()
scraping_status = {
    "em_andamento": False,
    "camara_pendentes": 0,
    "senado_pendentes": 0,
    "camara_completa": False,
    "senado_completo": False,
    "proposicoes_pendentes": 0,
    "proposicoes_completa": False,
    "deputados_perfil_pendente": True,
    "senadores_perfil_pendente": True,
}
