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

ANOS_PADRAO = list(range(2026, 2018, -1))
LEGISLATURAS = [57, 56, 55]
