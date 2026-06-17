#!/usr/bin/env python
import time
import psycopg2
import os

def wait_for_db():
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/fiscaliza_db")
    while True:
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print("PostgreSQL está pronto!")
            break
        except psycopg2.OperationalError:
            print("PostgreSQL não está pronto - aguardando...")
            time.sleep(2)

if __name__ == "__main__":
    wait_for_db()