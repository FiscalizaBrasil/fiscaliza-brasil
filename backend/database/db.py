from dotenv import load_dotenv
import psycopg2.pool
import os
from contextlib import contextmanager

load_dotenv()

db_url = os.getenv("DATABASE_URL")
        
if db_url:
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        5,
        100,
        dsn=db_url
    )
else:
    db_pool = psycopg2.pool.ThreadedConnectionPool(
        5,
        100,
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "fiscaliza_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres")
    )

def get_db_connection():
    conn = db_pool.getconn()
    conn.autocommit = False
    return conn

def release_db_connection(conn):
    """
    Devolve a conexão ao pool, garantindo que não fique em estado de transação abortada.
    """
    try:
        # Rollback para limpar qualquer transação pendente/abortada
        conn.rollback()
    except Exception:
        pass  # Se a conexão já estiver fechada, ignora
    db_pool.putconn(conn)


@contextmanager
def db_connection():
    """Context manager que obtém e libera uma conexão do pool automaticamente."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)


@contextmanager
def db_cursor():
    """Context manager que obtém conexão + cursor e libera tudo automaticamente."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        release_db_connection(conn)

      
