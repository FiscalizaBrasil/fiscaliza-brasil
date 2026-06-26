import threading
import logging

from .config import DATA_DIR
from .camara.deputados import download_fotos_deputados
from .senado.senadores import download_fotos_senadores

_log = logging.getLogger("WORKER")


def start_pipeline():
    """Inicia o pipeline de importação em thread separada."""

    def _run_pipeline():
        try:
            from .pipeline import run_pipeline
            run_pipeline()
        except Exception as e:
            _log.error("Erro fatal no pipeline: %s", e)
            from . import worker as _worker
            _worker.import_complete.set()

    threading.Thread(target=_run_pipeline, daemon=True).start()
    _log.info("Pipeline de importação iniciada em thread separada.")


def start_background_scraper():
    from . import worker as _worker
    if (
        _worker._background_thread_camara
        and _worker._background_thread_camara.is_alive()
    ):
        _log.info("Scraper da Câmara já está rodando.")
    else:
        _worker._stop_camara = False
        _worker._background_thread_camara = threading.Thread(
            target=_worker._background_worker_camara, daemon=True
        )
        _worker._background_thread_camara.start()
        _log.info("Scraper da Câmara iniciado em thread separada.")

    if (
        _worker._background_thread_senado
        and _worker._background_thread_senado.is_alive()
    ):
        _log.info("Scraper do Senado já está rodando.")
    else:
        _worker._stop_senado = False
        _worker._background_thread_senado = threading.Thread(
            target=_worker._background_worker_senado, daemon=True
        )
        _worker._background_thread_senado.start()
        _log.info("Scraper do Senado iniciado em thread separada.")

    if (
        _worker._background_thread_portal
        and _worker._background_thread_portal.is_alive()
    ):
        _log.info("Scraper do Portal já está rodando.")
    else:
        _worker._stop_portal = False
        _worker._background_thread_portal = threading.Thread(
            target=_worker._background_worker_portal, daemon=True
        )
        _worker._background_thread_portal.start()
        _log.info("Scraper do Portal iniciado em thread separada.")

    _worker._background_thread = _worker._background_thread_camara


def stop_background_scraper():
    from . import worker as _worker
    _worker._stop_camara = True
    _worker._stop_senado = True
    _worker._stop_portal = True
    _worker._stop_background = True
    _log.info("Todos os scrapers sinalizados para parar.")


_log_camara_foto = logging.getLogger("CAMARA")
_log_senado_foto = logging.getLogger("SENADO")


def _background_fotos_camara():
    try:
        _log_camara_foto.info("Baixando fotos dos deputados...")
        download_fotos_deputados()
        _log_camara_foto.info("Fotos dos deputados concluído.")
    except Exception as e:
        _log_camara_foto.error("Erro ao baixar fotos: %s", e)


def _background_fotos_senado():
    try:
        _log_senado_foto.info("Baixando fotos dos senadores...")
        download_fotos_senadores()
        _log_senado_foto.info("Fotos dos senadores concluído.")
    except Exception as e:
        _log_senado_foto.error("Erro ao baixar fotos: %s", e)


def start_background_fotos():
    threading.Thread(target=_background_fotos_camara, daemon=True).start()
    threading.Thread(target=_background_fotos_senado, daemon=True).start()
    _log.info("Download de fotos iniciado em background.")


def main():
    _log.info("Iniciando scraping de dados em background...")
    start_background_fotos()
    start_background_scraper()
    _log.info("Scraping inicial concluído. Background scraper rodando...")
