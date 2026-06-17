import sys
import os
import logging
from datetime import datetime

# Add the backend directory to sys.path to import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from database import db
except ImportError as e:
    logging.error(f"Error importing database module: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_tables(cursor):
    logging.info("Creating summary tables if they don't exist...")
    
    # Camara Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.summary_empresas_geral (
            legislatura_id INT PRIMARY KEY,
            total_empresas INT,
            total_pago DECIMAL(20, 2),
            total_contratos INT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS camara.summary_empresas_ranking (
            id SERIAL PRIMARY KEY,
            legislatura_id INT,
            rank INT,
            cnpj_raiz TEXT,
            nome_completo TEXT,
            total_valor DECIMAL(20, 2),
            qtd_contratos INT,
            principais_partidos TEXT,
            percentual DECIMAL(10, 2),
            nome_chave TEXT,
            UNIQUE(legislatura_id, rank)
        );
    """)
    
    # Senado Tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.summary_empresas_geral (
            legislatura INT PRIMARY KEY,
            total_empresas INT,
            total_pago DECIMAL(20, 2),
            total_contratos INT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS senado.summary_empresas_ranking (
            id SERIAL PRIMARY KEY,
            legislatura INT,
            rank INT,
            empresa TEXT,
            partidos TEXT,
            cnpj TEXT,
            valor_total DECIMAL(20, 2),
            contratos INT,
            percentual DECIMAL(10, 2),
            UNIQUE(legislatura, rank)
        );
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_camara_ranking_leg ON camara.summary_empresas_ranking(legislatura_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_senado_ranking_leg ON senado.summary_empresas_ranking(legislatura);")

def update_camara_summaries(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT legislatura_id FROM camara.deputados_mandatos ORDER BY legislatura_id DESC")
        legislaturas = [row[0] for row in cursor.fetchall()]
        
        for leg in legislaturas:
            logging.info(f"Updating Camara summaries for legislatura {leg}...")
            
            # 1. General Stats
            query_gerais = """
                SELECT
                    COUNT(DISTINCT UPPER(TRIM(REGEXP_REPLACE(d.nome_fornecedor, '\\s+(S/A|S\\.A\\.|SA|LTDA|EIRELI|ME|EPP|EI|LIMITADA).*$', '', 'gi')))) as total_empresas,
                    SUM(d.valor_documento) as total_pago,
                    COUNT(*) as total_contratos
                FROM camara.deputados_despesas d
                JOIN camara.deputados_mandatos m ON d.mandato_id = m.id
                WHERE LENGTH(REGEXP_REPLACE(d.cnpj_cpf_fornecedor, '[^0-9]', '', 'g')) > 11
                AND m.legislatura_id = %s
            """
            cursor.execute(query_gerais, (leg,))
            res_stats = cursor.fetchone()
            
            if not res_stats or res_stats[1] is None:
                continue
                
            total_pago = float(res_stats[1])
            
            cursor.execute("""
                INSERT INTO camara.summary_empresas_geral (legislatura_id, total_empresas, total_pago, total_contratos, last_updated)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (legislatura_id) DO UPDATE SET
                    total_empresas = EXCLUDED.total_empresas,
                    total_pago = EXCLUDED.total_pago,
                    total_contratos = EXCLUDED.total_contratos,
                    last_updated = CURRENT_TIMESTAMP;
            """, (leg, res_stats[0], total_pago, res_stats[2]))
            
            # 2. Ranking
            query_top = """
            WITH normalized_data AS (
                SELECT
                    d.cnpj_cpf_fornecedor,
                    d.nome_fornecedor,
                    d.valor_documento,
                    m.legislatura_id,
                    m.sigla_partido,
                    UPPER(TRIM(REGEXP_REPLACE(d.nome_fornecedor, '\\s+(S/A|S\\.A\\.|SA|LTDA|EIRELI|ME|EPP|EI|LIMITADA).*$', '', 'gi'))) as nome_chave
                FROM camara.deputados_despesas d
                JOIN camara.deputados_mandatos m ON d.mandato_id = m.id
                WHERE LENGTH(REGEXP_REPLACE(d.cnpj_cpf_fornecedor, '[^0-9]', '', 'g')) > 11
                AND m.legislatura_id = %s
            ),
            top_fornecedores AS (
                SELECT
                    nome_chave,
                    MAX(nome_fornecedor) as nome_completo,
                    LEFT(REGEXP_REPLACE(MAX(cnpj_cpf_fornecedor), '[^0-9]', '', 'g'), 8) as cnpj_raiz,
                    SUM(valor_documento) as total_valor,
                    COUNT(*) as qtd_contratos
                FROM normalized_data
                GROUP BY nome_chave
            ),
            partidos_pagadores AS (
                SELECT
                    nd.nome_chave,
                    nd.sigla_partido,
                    SUM(nd.valor_documento) as valor
                FROM normalized_data nd
                JOIN top_fornecedores tf ON nd.nome_chave = tf.nome_chave
                GROUP BY nd.nome_chave, nd.sigla_partido
            )
            SELECT
                tf.cnpj_raiz,
                tf.nome_completo,
                tf.total_valor,
                tf.qtd_contratos,
                (
                    SELECT string_agg(sub.sigla_partido, ', ')
                    FROM (
                        SELECT pp.sigla_partido
                        FROM partidos_pagadores pp
                        WHERE pp.nome_chave = tf.nome_chave
                        ORDER BY pp.valor DESC
                        LIMIT 3
                    ) sub
                ) as principais_partidos,
                tf.nome_chave
            FROM top_fornecedores tf
            ORDER BY tf.total_valor DESC
            LIMIT 100; -- Increase limit for summary storage
            """
            cursor.execute(query_top, (leg,))
            res_ranking = cursor.fetchall()
            
            # Clear old ranking for this legislatura
            cursor.execute("DELETE FROM camara.summary_empresas_ranking WHERE legislatura_id = %s", (leg,))
            
            for i, r in enumerate(res_ranking):
                nome_bruto = r[1]
                nome_limpo = nome_bruto.split("-")[0].strip().title() if nome_bruto else "Não Informado"
                valor_empresa = float(r[2])
                percentual = (valor_empresa / total_pago) * 100 if total_pago > 0 else 0
                
                cursor.execute("""
                    INSERT INTO camara.summary_empresas_ranking 
                    (legislatura_id, rank, cnpj_raiz, nome_completo, total_valor, qtd_contratos, principais_partidos, percentual, nome_chave)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (leg, i + 1, r[0], nome_limpo, valor_empresa, int(r[3]), r[4] if r[4] else "N/A", round(percentual, 2), r[5]))

def update_senado_summaries(conn):
    with conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT primeira_legislatura FROM senado.mandato UNION SELECT DISTINCT segunda_legislatura FROM senado.mandato")
        legislaturas = [row[0] for row in cursor.fetchall() if row[0]]
        
        for leg in legislaturas:
            logging.info(f"Updating Senado summaries for legislatura {leg}...")
            
            # 1. General Stats
            query_gerais = """
                 SELECT
                      COUNT(DISTINCT UPPER(TRIM(REGEXP_REPLACE(d.fornecedor, '\\s+(S/A|S\\.A\\.|SA|LTDA|EIRELI|ME|EPP|EI|LIMITADA).*$', '', 'gi')))) as total_empresas,
                      SUM(d.valor_reembolsado) as total_pago,
                      COUNT(*) as total_contratos
                  FROM senado.despesa_ceaps d
                  LEFT JOIN senado.parlamentar p ON d.cod_senador = p.codigo
                  JOIN senado.mandato m ON p.codigo = m.codigo_parlamentar
                  WHERE LENGTH(REGEXP_REPLACE(d.cpf_cnpj, '[^0-9]', '', 'g')) > 11
                  AND (m.primeira_legislatura = %s OR m.segunda_legislatura = %s)
            """
            cursor.execute(query_gerais, (str(leg), str(leg)))
            res_stats = cursor.fetchone()
            
            if not res_stats or res_stats[1] is None:
                continue
                
            total_pago = float(res_stats[1])
            
            cursor.execute("""
                INSERT INTO senado.summary_empresas_geral (legislatura, total_empresas, total_pago, total_contratos, last_updated)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (legislatura) DO UPDATE SET
                    total_empresas = EXCLUDED.total_empresas,
                    total_pago = EXCLUDED.total_pago,
                    total_contratos = EXCLUDED.total_contratos,
                    last_updated = CURRENT_TIMESTAMP;
            """, (leg, res_stats[0], total_pago, res_stats[2]))
            
            # 2. Ranking
            query_top_20 = """
              WITH normalized_data AS (
                  SELECT
                      d.fornecedor,
                      d.cpf_cnpj,
                      p.sigla_partido,
                      d.valor_reembolsado,
                      m.primeira_legislatura,
                      m.segunda_legislatura,
                      UPPER(TRIM(REGEXP_REPLACE(d.fornecedor, '\\s+(S/A|S\\.A\\.|SA|LTDA|EIRELI|ME|EPP|EI|LIMITADA).*$', '', 'gi'))) as nome_chave
                  FROM senado.despesa_ceaps d
                  LEFT JOIN senado.parlamentar p ON d.cod_senador = p.codigo
                  JOIN senado.mandato m ON p.codigo = m.codigo_parlamentar
                  WHERE LENGTH(REGEXP_REPLACE(d.cpf_cnpj, '[^0-9]', '', 'g')) > 11
                  AND (m.primeira_legislatura = %s OR m.segunda_legislatura = %s)
              ),
              EmpresaStats AS (
                  SELECT
                      nome_chave,
                      MAX(fornecedor) as fornecedor,
                      LEFT(REGEXP_REPLACE(MAX(cpf_cnpj), '[^0-9]', '', 'g'), 8) as cpf_cnpj_raiz,
                      SUM(valor_reembolsado) as valor_total,
                      COUNT(*) as contratos
                  FROM normalized_data
                  GROUP BY nome_chave
              ),
              EmpresaPartidos AS (
                  SELECT
                      nome_chave,
                      STRING_AGG(DISTINCT sigla_partido, ', ') as partidos
                  FROM normalized_data
                  GROUP BY nome_chave
              )
              SELECT
                  es.fornecedor as empresa,
                  COALESCE(ep.partidos, 'N/A') as partidos,
                  es.cpf_cnpj_raiz as cnpj,
                  es.valor_total,
                  es.contratos,
                  ROUND((es.valor_total / %s) * 100, 2) as percentual
              FROM EmpresaStats es
              JOIN EmpresaPartidos ep ON es.nome_chave = ep.nome_chave
              ORDER BY es.valor_total DESC
              LIMIT 100;
            """
            # Pass total_pago to avoid re-calculating inside the query for every row
            cursor.execute(query_top_20, (str(leg), str(leg), total_pago))
            res_ranking = cursor.fetchall()
            
            cursor.execute("DELETE FROM senado.summary_empresas_ranking WHERE legislatura = %s", (leg,))
            
            for i, r in enumerate(res_ranking):
                cursor.execute("""
                    INSERT INTO senado.summary_empresas_ranking
                    (legislatura, rank, empresa, partidos, cnpj, valor_total, contratos, percentual)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (leg, i + 1, r[0], r[1], r[2], float(r[3]), int(r[4]), float(r[5])))

def main():
    conn = None
    try:
        conn = db.get_db_connection()
        conn.autocommit = False # Use transaction
        with conn.cursor() as cursor:
            create_tables(cursor)
        
        update_camara_summaries(conn)
        update_senado_summaries(conn)
        
        conn.commit()
        logging.info("All summaries updated successfully!")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error updating summaries: {e}")
    finally:
        if conn:
            db.release_db_connection(conn)

if __name__ == "__main__":
    main()
