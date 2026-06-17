from dotenv import load_dotenv
import psycopg2.pool
import os

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
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool.putconn(conn)
    
      
