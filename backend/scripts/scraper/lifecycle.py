import threading
import logging

from .config import DATA_DIR
from .camara.deputados import fetch_deputados_todas_legislaturas, download_fotos_deputados
from .senado.senadores import fetch_senadores_senado, download_fotos_senadores

_log = logging.getLogger("WORKER")


def start_background_import():
    """Importa dados cacheados em background e inicia os scrapers em paralelo."""

    def _run_import():
        _log.info("Importando dados cacheados do disco em background...")
        conn = None
        try:
            from database import db
            conn = db.get_db_connection()
            if conn:
                from scripts.import_data import import_all_data
                imported = import_all_data(conn)
                if imported:
                    _log.info("Importação de dados cacheados concluída com sucesso.")
                else:
                    _log.info(
                        "Nenhum dado novo para importar (banco já populado ou sem JSONs)."
                    )
        except Exception as e:
            _log.error("Erro na importação inicial: %s", e)
        finally:
            if conn:
                try:
                    from database import db
                    db.release_db_connection(conn)
                except Exception:
                    pass

    threading.Thread(target=_run_import, daemon=True).start()
    _log.info("Importação de dados disparada em thread separada.")

    _log.info("Iniciando scrapers em background (em paralelo com a importação)...")
    start_background_scraper()


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


def ensure_base_data_downloaded():
    """Baixa os arquivos base (deputados.json e senadores.json) de forma
    bloqueante, garantindo que existam antes da importação e scrapers.

    Ambas as funcoes sao cache-aware — se os arquivos ja existirem e
    estiverem validos, pulam o download.
    """
    _log.info("Baixando dados base (deputados e senadores)...")
    try:
        fetch_deputados_todas_legislaturas()
        _log.info("deputados.json pronto.")
    except Exception as e:
        _log.error("Falha ao baixar deputados.json: %s", e)
    try:
        fetch_senadores_senado()
        _log.info("senadores.json pronto.")
    except Exception as e:
        _log.error("Falha ao baixar senadores.json: %s", e)


def start_background_fotos():
    threading.Thread(target=_background_fotos_camara, daemon=True).start()
    threading.Thread(target=_background_fotos_senado, daemon=True).start()
    _log.info("Download de fotos iniciado em background.")


def main():
    _log.info("Iniciando scraping de dados em background...")
    start_background_fotos()
    start_background_scraper()
    _log.info("Scraping inicial concluído. Background scraper rodando...")
