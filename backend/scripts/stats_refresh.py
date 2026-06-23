import os
import time
import threading
import logging

import database.db as db

_log = logging.getLogger(__name__)

_stop_refresh = False

REFRESH_INTERVAL_MINUTES = int(os.getenv("STATS_REFRESH_MINUTES", "1"))
REFRESH_INTERVAL = max(REFRESH_INTERVAL_MINUTES, 1) * 60

_MVS = [
    "stats.camara_despesas_totais",
    "stats.camara_despesas_categorias",
    "stats.camara_despesas_partidos",
    "stats.camara_despesas_deputados",
    "stats.camara_despesas_estados",
    "stats.camara_despesas_evolucao",
    "stats.camara_empresas_ranking",
]


def _refresh_loop():
    _log.info("Thread de refresh das materialized views iniciada (intervalo: %d min).", REFRESH_INTERVAL_MINUTES)

    while not _stop_refresh:
        conn = None
        try:
            conn = db.get_db_connection()
            if not conn:
                _log.warning("MV refresh: banco indisponivel, tentando novamente em 30s...")
                time.sleep(30)
                continue

            conn.autocommit = True
            with conn.cursor() as cursor:
                for mv in _MVS:
                    try:
                        cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {mv}")
                        _log.debug("MV %s atualizada com sucesso.", mv)
                    except Exception as mv_err:
                        _log.error("Falha ao atualizar MV %s: %s", mv, mv_err)

        except Exception as e:
            _log.error("Erro no ciclo de refresh das MVs: %s", e)
        finally:
            if conn:
                db.release_db_connection(conn)

        for _ in range(REFRESH_INTERVAL):
            if _stop_refresh:
                break
            time.sleep(1)

    _log.info("Thread de refresh das MVs encerrada.")


def start_stats_refresh():
    threading.Thread(target=_refresh_loop, daemon=True).start()
