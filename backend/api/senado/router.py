from fastapi import APIRouter, HTTPException, Query
from datetime import date
import logging

_log = logging.getLogger(__name__)

# Garanta que este import está correto para sua estrutura
import database.db as db
from database.utils import get_maior_legislatura_senado, get_legislatura_atual, periodo_legislatura, get_foto_url_senado, legislatura_anos
from database.cache import ttl_cache

router = APIRouter(
    prefix="/senado",
    tags=["Senado"]
)


@router.get("/legislaturas", summary="Lista todas as legislaturas disponíveis na base")
@ttl_cache(maxsize=1, ttl=3600, cache_name="senado_legislaturas")
def get_legislaturas_senado():
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # Tenta primeiro da tabela senado.mandato
            query = """
                SELECT DISTINCT primeira_legislatura, segunda_legislatura 
                FROM senado.mandato
            """
            cursor.execute(query)
            mandatos = cursor.fetchall()
            legis_set = set()
            for m in mandatos:
                if m[0] and str(m[0]).strip().isdigit():
                    legis_set.add(int(str(m[0]).strip()))
                if m[1] and str(m[1]).strip().isdigit():
                    legis_set.add(int(str(m[1]).strip()))
            
            # Se não encontrou em mandato, busca da tabela senado.legislatura
            if not legis_set:
                cursor.execute("""
                    SELECT numero FROM senado.legislatura
                    WHERE numero IS NOT NULL AND TRIM(numero) != ''
                      AND TRIM(numero) ~ '^\\d+$'
                    ORDER BY numero DESC
                """)
                for row in cursor.fetchall():
                    legis_set.add(int(str(row[0]).strip()))
            
            # Se ainda não encontrou, calcula a partir dos anos das despesas
            if not legis_set:
                cursor.execute("""
                    SELECT MIN(ano), MAX(ano) FROM senado.despesa_ceaps
                """)
                row = cursor.fetchone()
                if row and row[0] and row[1]:
                    min_ano, max_ano = row[0], row[1]
                    # Cada legislatura dura 4 anos. A legislatura 57 começou em 2023.
                    # Calcula quais legislaturas cobrem o intervalo de anos
                    for ano in range(min_ano, max_ano + 1):
                        leg = 57 - (2023 - ano) // 4
                        legis_set.add(leg)
            
            # Filtra apenas legislaturas até a atual (não mostrar futuras)
            legislatura_atual = get_legislatura_atual()
            return sorted([leg for leg in legis_set if leg <= legislatura_atual], reverse=True)
    except Exception as e:
        _log.error(f"Erro ao buscar legislaturas ativas senado: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar legislaturas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/maior-legislatura", summary="Retorna a maior legislatura disponível na base")
@ttl_cache(maxsize=1, ttl=3600, cache_name="senado_maior_legislatura")
def get_maior_legislatura_senado_endpoint():
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        maior_leg = get_maior_legislatura_senado(conn)
        if maior_leg is None:
            return {"maior_legislatura": None, "db_vazio": True}
        
        return {"maior_legislatura": maior_leg, "db_vazio": False}
    except Exception as e:
        _log.error(f"Erro ao buscar maior legislatura: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar maior legislatura")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/lista", summary="Lista todos os senadores ativos")
def get_lista_senadores(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # Verifica se a tabela mandato tem registros
            cursor.execute("SELECT COUNT(*) FROM senado.mandato")
            tem_mandato = cursor.fetchone()[0] > 0

            if tem_mandato:
                # Usa JOIN com mandato para filtrar por legislatura
                query = """
                    SELECT
                        p.codigo,
                        p.nome_parlamentar,
                        p.sigla_partido,
                        COALESCE(
                            NULLIF(TRIM(p.uf::text), ''),
                            NULLIF(TRIM(MAX(m.uf)::text), '')
                        ) AS uf,
                        p.url_foto
                    FROM senado.parlamentar p
                    INNER JOIN senado.mandato m ON p.codigo = m.codigo_parlamentar
                """
                params: list[object] = []
                if legislatura:
                    query += " WHERE m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text"
                    params.extend([str(legislatura), str(legislatura)])
                    
                query += """
                    GROUP BY p.codigo, p.nome_parlamentar, p.sigla_partido, p.uf, p.url_foto
                    ORDER BY p.codigo, p.nome_parlamentar ASC
                """
                cursor.execute(query, tuple(params))
            else:
                # Fallback: lista todos os senadores da tabela parlamentar (sem mandato)
                query = """
                    SELECT
                        codigo,
                        nome_parlamentar,
                        sigla_partido,
                        NULLIF(TRIM(uf::text), '') AS uf,
                        url_foto
                    FROM senado.parlamentar
                    ORDER BY nome_parlamentar ASC
                """
                cursor.execute(query)
            
            resultados = cursor.fetchall()
            
            return {
                "senadores": [
                {
                    "codigo": r[0],
                    "nomeParlamentar": r[1],
                    "siglaPartido": r[2],
                    "uf": r[3],
                    "urlFoto": get_foto_url_senado(r[0], r[4])
                }
                for r in resultados
            ]
        }
    except Exception as e:
        _log.error(f"Erro ao buscar senadores: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar senadores")
    finally:
        if conn:
            db.release_db_connection(conn)






@router.get("/{legislatura}/estatisticas")
@ttl_cache(maxsize=16, ttl=300, cache_name="senado_estatisticas")
def get_estatisticas_senado(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            query_total = "SELECT COUNT(DISTINCT codigo_parlamentar) FROM senado.mandato"
            params: list[object] = []
            if legislatura:
                query_total += " WHERE primeira_legislatura::text = %s::text OR segunda_legislatura::text = %s::text"
                params.extend([str(legislatura), str(legislatura)])
            
            cursor.execute(query_total, tuple(params))
            row = cursor.fetchone()
            total_senadores = row[0] if row else 0

            query_gastos = """
                SELECT COALESCE(SUM(d.valor_reembolsado), 0) 
                FROM senado.despesa_ceaps d
            """
            params_gastos: list[object] = []
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_gastos += """
                    INNER JOIN (
                        SELECT DISTINCT codigo_parlamentar
                        FROM senado.mandato
                        WHERE primeira_legislatura::text = %s::text OR segunda_legislatura::text = %s::text
                    ) m ON d.cod_senador = m.codigo_parlamentar
                    WHERE CAST(d.ano AS INTEGER) BETWEEN %s AND %s
                """
                params_gastos.extend([str(legislatura), str(legislatura), start_year, end_year])
            
            cursor.execute(query_gastos, tuple(params_gastos))
            total_gastos = cursor.fetchone()[0] or 0

            # Distribuição por Região
            query_regiao = """
                WITH base_senadores AS (
                    SELECT
                        p.codigo,
                        COALESCE(
                            NULLIF(TRIM(MAX(p.uf)::text), ''),
                            NULLIF(TRIM(MAX(m.uf)::text), '')
                        ) AS uf_ref
                    FROM senado.parlamentar p
                    INNER JOIN senado.mandato m ON p.codigo = m.codigo_parlamentar
                    WHERE 1=1
            """
            params_reg = []
            if legislatura:
                query_regiao += " AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text)"
                params_reg.extend([legislatura, legislatura])
                
            query_regiao += """
                    GROUP BY p.codigo
                )
                SELECT 
                    CASE
                        WHEN uf_ref IN ('AC','AP','AM','PA','RO','RR','TO') THEN 'Norte'
                        WHEN uf_ref IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
                        WHEN uf_ref IN ('DF','GO','MT','MS') THEN 'Centro-Oeste'
                        WHEN uf_ref IN ('ES','MG','RJ','SP') THEN 'Sudeste'
                        WHEN uf_ref IN ('PR','RS','SC') THEN 'Sul'
                        ELSE 'Outros'
                    END AS regiao,
                    COUNT(*) AS quantidade
                FROM base_senadores
                GROUP BY regiao
                ORDER BY quantidade DESC
            """
            cursor.execute(query_regiao, tuple(params_reg))
            regioes = cursor.fetchall()
            
            return {
                "total_senadores": total_senadores,
                "total_gastos": total_gastos,
                "total_regioes": len(regioes),
                "senadores_por_regiao": [
                    {"name": r[0], "value": int(r[1])}
                    for r in regioes
                ]
            }
    except Exception as e:
        _log.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar estatísticas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/comparar")
def get_comparativo_senadores(legislatura: int, id1: int, id2: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        if id1 == id2:
            raise HTTPException(status_code=400, detail="Os senadores devem ser diferentes")

        with conn.cursor() as cursor:
            query_perfil = """
SELECT 
    codigo, 
    nome_parlamentar, 
    nome_completo, 
    sexo,
    sigla_partido, 
    uf, 
    email,
    url_foto,
    data_nascimento
FROM senado.parlamentar
WHERE codigo IN (%s, %s);
"""             
            cursor.execute(query_perfil, (id1, id2))
            resultado = cursor.fetchall()

            if not resultado:
                raise HTTPException(status_code=404, detail="Senador não encontrado")
            
            query_despesas = """
SELECT 
    d.cod_senador, 
    d.tipo_despesa, 
    SUM(d.valor_reembolsado) as total,
    COUNT(*) as qtd
FROM senado.despesa_ceaps d
WHERE d.cod_senador IN (%s, %s)
            """
            params_stat = [id1, id2]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_despesas += """
                    AND d.cod_senador IN (
                        SELECT DISTINCT codigo_parlamentar
                        FROM senado.mandato
                        WHERE primeira_legislatura::text = %s::text OR segunda_legislatura::text = %s::text
                    )
                    AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s
                """
                params_stat.extend([legislatura, legislatura, start_year, end_year])
                
            query_despesas += " GROUP BY d.cod_senador, d.tipo_despesa"
            cursor.execute(query_despesas, tuple(params_stat))
            resultados_despesas = cursor.fetchall()

            query_despesas_recentes = """SELECT 
    ano, 
    mes, 
    tipo_despesa, 
    valor_reembolsado, 
    data_despesa
FROM senado.despesa_ceaps
WHERE cod_senador = %s
ORDER BY
    COALESCE(
        data_despesa,
        TO_DATE(CAST(ano AS TEXT) || '-' || LPAD(CAST(mes AS TEXT), 2, '0') || '-01', 'YYYY-MM-DD')
    ) DESC,
    CAST(ano AS INTEGER) DESC,
    CAST(mes AS INTEGER) DESC
LIMIT 12;
"""

            cursor.execute(query_despesas_recentes, (id1,))
            despesas_recentes_1 = cursor.fetchall()
            cursor.execute(query_despesas_recentes, (id2,))
            despesas_recentes_2 = cursor.fetchall()

            # Fix mapping to ensure correct IDs map to correct keys regardless of SQL return order
            senador_1_data = next((r for r in resultado if r[0] == id1), None)
            senador_2_data = next((r for r in resultado if r[0] == id2), None)
            
            if not senador_1_data or not senador_2_data:
                raise HTTPException(status_code=404, detail="Um ou ambos os senadores não foram encontrados")

            return{ 
                "senador1": {
                    "codigo": senador_1_data[0],
                    "nomeParlamentar": senador_1_data[1],
                    "nomeCompleto": senador_1_data[2],
                    "sexo": senador_1_data[3],
                    "siglaPartido": senador_1_data[4],
                    "uf": senador_1_data[5],
                    "email": senador_1_data[6],
                    "urlFoto": get_foto_url_senado(senador_1_data[0], senador_1_data[7]),
                    "dataNascimento": senador_1_data[8]
                },
                "senador2": {
                    "codigo": senador_2_data[0],
                    "nomeParlamentar": senador_2_data[1],
                    "nomeCompleto": senador_2_data[2],
                    "sexo": senador_2_data[3],
                    "siglaPartido": senador_2_data[4],
                    "uf": senador_2_data[5],
                    "email": senador_2_data[6],
                    "urlFoto": get_foto_url_senado(senador_2_data[0], senador_2_data[7]),
                    "dataNascimento": senador_2_data[8]
                },
                "despesas": [           
                    {
                        "senador": r[0],
                        "tipoDespesa": r[1],
                        "total": float(r[2]),
                        "qtd": r[3]
                    }
                    for r in resultados_despesas
                ],
                "despesas_recentes_1": [
                    {
                        "ano": r[0],
                        "mes": r[1],
                        "tipoDespesa": r[2],
                        "valor": float(r[3]),
                        "data_despesa": r[4].isoformat() if hasattr(r[4], 'isoformat') else str(r[4])
                    }
                    for r in despesas_recentes_1
                ],
                "despesas_recentes_2": [
                    {
                        "ano": r[0],
                        "mes": r[1],
                        "tipoDespesa": r[2],
                        "valor": float(r[3]),
                        "data_despesa": r[4].isoformat() if hasattr(r[4], 'isoformat') else str(r[4])
                    }
                    for r in despesas_recentes_2
                ]       
            }
    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"Erro ao buscar senador: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar senador")
    finally:
        if conn:
            db.release_db_connection(conn)
                

@router.get("/{legislatura}/{senador_codigo}", summary="Obtém o perfil detalhado de um senador")
def get_perfil_senador(legislatura: int, senador_codigo: int):    
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            query = """SELECT 
    codigo,
    nome_parlamentar,
    nome_completo,
    sexo,
    sigla_partido,
    uf,
    email,
    url_foto,
    url_pagina,
    data_nascimento
FROM senado.parlamentar
WHERE codigo = %s;"""
            cursor.execute(query, (senador_codigo,))
            resultado = cursor.fetchone()

            if not resultado:
                raise HTTPException(status_code=404, detail="Senador não encontrado")

            uf_parlamentar = resultado[5].strip() if resultado[5] and str(resultado[5]).strip() else None
            query_uf_mandato = """
                SELECT NULLIF(TRIM(m.uf::text), '') as uf
                FROM senado.mandato m
                WHERE m.codigo_parlamentar = %s
                  AND NULLIF(TRIM(m.uf::text), '') IS NOT NULL
                ORDER BY
                    CASE
                        WHEN %s <> 0 AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text) THEN 0
                        ELSE 1
                    END,
                    m.primeira_legislatura DESC NULLS LAST,
                    m.segunda_legislatura DESC NULLS LAST
                LIMIT 1
            """
            cursor.execute(query_uf_mandato, (senador_codigo, legislatura, legislatura, legislatura))
            uf_mandato_row = cursor.fetchone()
            uf_mandato = uf_mandato_row[0] if uf_mandato_row and uf_mandato_row[0] else None
            uf_referencia = uf_parlamentar or uf_mandato
            
            # 2. Buscar Resumo de Emendas (Optimized with CTE)
            query_emendas = """
                WITH senadores_nomes AS (
                    SELECT codigo as id, lower(nome_completo) as nome FROM senado.parlamentar
                    UNION
                    SELECT codigo as id, lower(nome_parlamentar) as nome FROM senado.parlamentar
                )
                SELECT SUM(e.valor_pago) as total_emendas
                FROM portal.emendas e
                JOIN senadores_nomes s ON lower(e.nome_autor) = s.nome
                WHERE s.id = %s
            """
            params_emendas = [senador_codigo]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_emendas += """
                    AND CAST(e.ano AS INTEGER) BETWEEN %s AND %s
                    AND EXISTS (
                        SELECT 1 FROM senado.mandato m
                        WHERE m.codigo_parlamentar = s.id
                          AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text)
                    )
                """
             
                params_emendas.extend([start_year, end_year, legislatura, legislatura])
            else:
                query_emendas += """
                    AND EXISTS (
                        SELECT 1 FROM senado.mandato m
                        WHERE m.codigo_parlamentar = s.id
                          AND (
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4 AND 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4 + 3
                              OR
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4 AND 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4 + 3
                          )
                    )
                """

            cursor.execute(query_emendas, tuple(params_emendas))
            emendas_res_row = cursor.fetchone()
            total_emendas = float(emendas_res_row[0]) if emendas_res_row and emendas_res_row[0] else 0.0

            # 3. Legislaturas Ativas
            query_legis = """
                SELECT primeira_legislatura, segunda_legislatura
                FROM senado.mandato
                WHERE codigo_parlamentar = %s
            """
            cursor.execute(query_legis, (senador_codigo,))
            mandatos = cursor.fetchall()
            legis_set = set()
            for m in mandatos:
                if m[0] and str(m[0]).strip().isdigit():
                    legis_set.add(int(str(m[0]).strip()))
                if m[1] and str(m[1]).strip().isdigit():
                    legis_set.add(int(str(m[1]).strip()))
            legislaturas_ativas = sorted(list(legis_set), reverse=True)

            # Determinar Legislatura Exibida (Sempre forçamos uma real, exceto se for 0)
            if legislatura == 0:
                leg_exibida = 0
            elif legislatura and legislatura in legislaturas_ativas:
                leg_exibida = legislatura
            elif legislaturas_ativas:
                leg_exibida = legislaturas_ativas[0]
            else:
                # Fallback: busca a maior legislatura disponível no banco
                maior_leg = get_maior_legislatura_senado(conn)
                leg_exibida = maior_leg if maior_leg else 57

            return {
                "senador": {
                    "codigo": resultado[0],
                    "nomeParlamentar": resultado[1],
                    "nomeCompleto": resultado[2],
                    "sexo": resultado[3],
                    "siglaPartido": resultado[4],
                    "uf": uf_referencia,
                    "email": resultado[6],
                    "urlFoto": get_foto_url_senado(resultado[0], resultado[7]),
                    "urlPagina": resultado[8],
                    "dataNascimento": resultado[9],
                    "total_emendas": total_emendas,
                    "legislaturas_ativas": legislaturas_ativas,
                    "legislatura_exibida": leg_exibida
                }
            }

    except Exception as e:
        _log.error(f"Erro ao buscar senador: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar senador")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/{senador_codigo}/despesas", summary="Obtém o extrato de despesas de um senador")
def get_despesas_senador(legislatura: int, senador_codigo: int, pagina: int = 1):
    itens_per_page = 20
    offset = (pagina - 1) * itens_per_page
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # 1. Buscar o total de despesas para paginação
            query_count = """SELECT COUNT(*) 
                FROM senado.despesa_ceaps d
                WHERE d.cod_senador = %s"""
            params_count = [senador_codigo]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_count += " AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s"
                params_count.extend([start_year, end_year])
            
            cursor.execute(query_count, tuple(params_count))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + itens_per_page - 1) // itens_per_page

            # 2. Buscar as despesas paginadas
            query_recente = """SELECT 
                    d.ano, 
                    d.mes, 
                    d.tipo_despesa, 
                    d.fornecedor, 
                    d.valor_reembolsado, 
                    d.data_despesa
                FROM senado.despesa_ceaps d
                WHERE d.cod_senador = %s 
            """
            params_rec = [senador_codigo]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_recente += " AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s"
                params_rec.extend([start_year, end_year])
                
            query_recente += " ORDER BY d.data_despesa DESC LIMIT %s OFFSET %s"
            params_rec.extend([itens_per_page, offset])
            cursor.execute(query_recente, tuple(params_rec))
            resultado = cursor.fetchall()

            # 3. Buscar o resumo por categoria
            query_categorias = """
                SELECT 
                    d.tipo_despesa, 
                    SUM(d.valor_reembolsado) as total
                FROM senado.despesa_ceaps d
                WHERE d.cod_senador = %s
            """
            params_cat = [senador_codigo]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_categorias += " AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s"
                params_cat.extend([start_year, end_year])
            
            query_categorias += " GROUP BY d.tipo_despesa ORDER BY total DESC"
            cursor.execute(query_categorias, tuple(params_cat))
            categorias_raw = cursor.fetchall()
            
            total_geral = sum(float(c[1]) for c in categorias_raw) if categorias_raw else 0.0
            
            return {
                "despesas": [
                    {
                        "ano": r[0],
                        "mes": r[1],
                        "tipoDespesa": r[2],
                        "fornecedor": r[3],
                        "valorReembolsado": float(r[4]),
                        "dataDespesa": r[5].isoformat() if hasattr(r[5], 'isoformat') else str(r[5]) if r[5] else None
                    }
                    for r in resultado
                ],
                "total_despesas": total_geral,
                "categorias": [
                    {"categoria": c[0], "valor": float(c[1])}
                    for c in categorias_raw
                ],
                "paginacao": {
                    "total": total_items,
                    "pagina": pagina,
                    "total_paginas": total_paginas,
                    "itens_por_pagina": itens_per_page
                }
            }
    except Exception as e:
        _log.error(f"Erro ao buscar despesas do senador: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar despesas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/despesas/evolucao", summary="Obtém a evolução de gastos do Senado (mensal ou anual)")
@ttl_cache(maxsize=16, ttl=300, cache_name="senado_despesas_evolucao")
def get_evolucao_despesas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        with conn.cursor() as cursor:
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                where_leg = " AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s"
                join_mandato = """
                    INNER JOIN (
                        SELECT DISTINCT codigo_parlamentar
                        FROM senado.mandato
                        WHERE primeira_legislatura::text = %s::text OR segunda_legislatura::text = %s::text
                    ) m ON d.cod_senador = m.codigo_parlamentar
                """
                params = [legislatura, legislatura, start_year, end_year]
                cursor.execute(f"""
                    SELECT d.ano, d.mes, SUM(d.valor_reembolsado) as valor
                    FROM senado.despesa_ceaps d
                    {join_mandato}
                    WHERE d.mes BETWEEN 1 AND 12
                      AND make_date(d.ano, d.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
                      {where_leg}
                    GROUP BY 1, 2 ORDER BY 1 ASC, 2 ASC
                """, tuple(params))
            else:
                cursor.execute("""
                    SELECT d.ano, 0 as mes, SUM(d.valor_reembolsado) as valor
                    FROM senado.despesa_ceaps d
                    WHERE d.mes BETWEEN 1 AND 12
                      AND make_date(d.ano, d.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
                    GROUP BY 1 ORDER BY 1 ASC
                """)

            return {
                "evolucao_gastos": [
                    {"ano": r[0], "mes": r[1], "valor": float(r[2])}
                    for r in cursor.fetchall()
                ]
            }
    except Exception as e:
        _log.error(f"Erro ao buscar evolução de gastos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar evolução de gastos")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/despesas/estatisticas")
@ttl_cache(maxsize=16, ttl=300, cache_name="senado_despesas_estatisticas")
def get_despesas_estatisticas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            params = []
            where_leg = ""
            join_mandato = ""
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                where_leg = " AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s"
                join_mandato = """
                    INNER JOIN (
                        SELECT DISTINCT codigo_parlamentar
                        FROM senado.mandato
                        WHERE primeira_legislatura::text = %s::text OR segunda_legislatura::text = %s::text
                    ) m ON d.cod_senador = m.codigo_parlamentar
                """
                params.extend([legislatura, legislatura, start_year, end_year])
            
            # 1. Total de Gastos
            query_total = f"SELECT COALESCE(SUM(d.valor_reembolsado), 0) FROM senado.despesa_ceaps d {join_mandato} WHERE 1=1 {where_leg}"
            cursor.execute(query_total, tuple(params))
            total_gastos = cursor.fetchone()[0] or 0

            # 2. Média por Senador
            query_media = f"""
                SELECT COALESCE(SUM(d.valor_reembolsado) / NULLIF(COUNT(DISTINCT d.cod_senador), 0), 0)
                FROM senado.despesa_ceaps d
                {join_mandato}
                WHERE 1=1 {where_leg}
            """
            cursor.execute(query_media, tuple(params))
            media_por_senador = cursor.fetchone()[0] or 0
            
            # 3. Gastos por Partido
            query_partidos = f"""
                SELECT 
                    p.sigla_partido,
                    SUM(d.valor_reembolsado) AS total_valor,
                    ROUND((SUM(d.valor_reembolsado) / NULLIF({total_gastos}, 0)) * 100, 2) AS percentual
                FROM senado.despesa_ceaps d
                JOIN senado.parlamentar p ON d.cod_senador = p.codigo
                {join_mandato}
                WHERE 1=1 {where_leg}
                GROUP BY p.sigla_partido
                ORDER BY total_valor DESC
            """
            cursor.execute(query_partidos, tuple(params))
            partidos = cursor.fetchall()
            
            # 4. Gastos por Categoria
            query_cat = f"""
                WITH ranking_categorias AS (
                    SELECT 
                        COALESCE(NULLIF(TRIM(d.tipo_despesa), ''), 'Não informado') AS tipo_despesa,
                        SUM(d.valor_reembolsado) AS valor,
                        ROW_NUMBER() OVER (ORDER BY SUM(d.valor_reembolsado) DESC) as rank
                    FROM senado.despesa_ceaps d
                    {join_mandato}
                    WHERE 1=1 {where_leg}
                    GROUP BY COALESCE(NULLIF(TRIM(d.tipo_despesa), ''), 'Não informado')
                )
                SELECT 
                    CASE WHEN rank <= 9 THEN tipo_despesa ELSE 'Outros' END AS categoria,
                    SUM(valor) AS total_valor
                FROM ranking_categorias
                GROUP BY 1
                ORDER BY total_valor DESC
            """
            cursor.execute(query_cat, tuple(params))
            categorias = cursor.fetchall()
            
            # 5. Top 10 Senadores
            query_top = f"""
                SELECT 
                    p.codigo, 
                    p.nome_parlamentar, 
                    p.sigla_partido, 
                    p.uf, 
                    p.url_foto,
                    SUM(d.valor_reembolsado) AS total_valor
                FROM senado.despesa_ceaps d
                JOIN senado.parlamentar p ON d.cod_senador = p.codigo
                {join_mandato}
                WHERE 1=1 {where_leg}
                GROUP BY p.codigo, p.nome_parlamentar, p.sigla_partido, p.uf, p.url_foto
                ORDER BY total_valor DESC
                LIMIT 10
            """
            cursor.execute(query_top, tuple(params))
            top_10 = cursor.fetchall()

            # 6. Evolução Mensal (últimos 12 meses registrados na legislatura ou total)
            query_evolucao = f"""
                SELECT 
                    d.ano AS ano,
                    d.mes AS mes,
                    SUM(d.valor_reembolsado) AS valor
                FROM senado.despesa_ceaps d
                {join_mandato}
                WHERE d.mes BETWEEN 1 AND 12
                  AND make_date(d.ano, d.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
                  {where_leg}
                GROUP BY 1, 2
                ORDER BY 1 DESC, 2 DESC
                LIMIT 12
            """
            cursor.execute(query_evolucao, tuple(params))
            gastos_mensais = cursor.fetchall()

            # 6b. Evolução de Gastos (todos os meses da legislatura ou anual quando legislatura=0)
            if legislatura:
                query_evolucao_gastos = f"""
                    SELECT 
                        d.ano AS ano,
                        d.mes AS mes,
                        SUM(d.valor_reembolsado) AS valor
                    FROM senado.despesa_ceaps d
                    {join_mandato}
                    WHERE d.mes BETWEEN 1 AND 12
                      AND make_date(d.ano, d.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
                      {where_leg}
                    GROUP BY 1, 2
                    ORDER BY 1 ASC, 2 ASC
                """
                cursor.execute(query_evolucao_gastos, tuple(params))
                evolucao_gastos = [{"ano": r[0], "mes": r[1], "valor": float(r[2])} for r in cursor.fetchall()]
            else:
                query_evolucao_gastos = """
                    SELECT 
                        d.ano AS ano,
                        0 AS mes,
                        SUM(d.valor_reembolsado) AS valor
                    FROM senado.despesa_ceaps d
                    WHERE d.mes BETWEEN 1 AND 12
                      AND make_date(d.ano, d.mes, 1) <= date_trunc('month', CURRENT_DATE)::date
                    GROUP BY 1
                    ORDER BY 1 ASC
                """
                cursor.execute(query_evolucao_gastos)
                evolucao_gastos = [{"ano": r[0], "mes": r[1], "valor": float(r[2])} for r in cursor.fetchall()]

            # 7. Total 12 meses (sempre global ou por legislatura?) 
            # Mantendo global para contexto, ou filtrando se legislatura ativa 
            query_12m = f"""
                SELECT COALESCE(SUM(d.valor_reembolsado), 0)
                FROM senado.despesa_ceaps d
                {join_mandato}
                WHERE d.data_despesa >= (CURRENT_DATE - INTERVAL '1 year') {where_leg}
            """
            cursor.execute(query_12m, tuple(params))
            total_12_meses = cursor.fetchone()[0] or 0
            
            return {
                "total_gastos": float(total_gastos),
                "media_por_senador": float(media_por_senador),
                "total_12_meses": float(total_12_meses),
                "gastos_por_mes": [
                    {"ano": r[0], "mes": r[1], "valor": float(r[2])}
                    for r in gastos_mensais
                ],
                "partidos": [
                    {
                        "partido": r[0],
                        "total": float(r[1]),
                        "percentual": float(r[2])
                    }
                    for r in partidos
                ],
                "categorias": [
                    {
                        "categoria": r[0],
                        "total": float(r[1])
                    }
                    for r in categorias
                ],
                "top_10": [
                    {
                        "codigo": r[0],
                        "nome": r[1],
                        "partido": r[2],
                        "uf": r[3],
                        "foto": get_foto_url_senado(r[0], r[4]),
                        "total": float(r[5])
                    }
                    for r in top_10
                ],
                "evolucao_gastos": evolucao_gastos
            }
    except Exception as e:
        _log.error(f"Erro ao buscar estatísticas de despesas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar estatísticas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/materia/listar")
def get_materia_listar(
    legislatura: int,
    siglaTipo: str = Query(None),
    ano: int = Query(None),
    ementa: str = Query(None),
    senador: str = Query(None),
    votadas: bool = Query(False),
    limite: int = Query(15, ge=1, le=200),
    pagina: int = Query(1, ge=1)
):
    offset = (pagina - 1) * limite
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            from_clause = """
                FROM senado.materia m
            """
            if senador:
                from_clause += """
                    INNER JOIN senado.votacao_parlamentar vp ON m.codigo = vp.codigo_materia
                    INNER JOIN senado.parlamentar sv ON vp.codigo_parlamentar = sv.codigo
                """

            filtros = ["1=1"]
            params = []

            if siglaTipo:
                filtros.append("m.sigla = %s")
                params.append(siglaTipo)
            if ano:
                filtros.append("m.ano = %s")
                params.append(ano)
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                filtros.append("m.ano BETWEEN %s AND %s")
                params.extend([start_year, end_year])
            if ementa:
                filtros.append("m.ementa ILIKE %s")
                params.append(f"%{ementa}%")
            if senador:
                filtros.append("(sv.nome_parlamentar ILIKE %s OR sv.nome_completo ILIKE %s)")
                params.extend([f"%{senador}%", f"%{senador}%"])
            if votadas:
                filtros.append("EXISTS (SELECT 1 FROM senado.votacao_parlamentar vp WHERE vp.codigo_materia = m.codigo)")

            where_clause = " WHERE " + " AND ".join(filtros)

            # 1. Total para paginação
            query_count = f"""
                SELECT COUNT(DISTINCT m.codigo)
                {from_clause}
                {where_clause}
            """
            cursor.execute(query_count, tuple(params))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + limite - 1) // limite

            # 2. Distribuição por tipo (sobre todo o conjunto filtrado)
            query_tipos = f"""
                SELECT m.sigla, COUNT(DISTINCT m.codigo) as quantidade
                {from_clause}
                {where_clause}
                GROUP BY m.sigla
                ORDER BY quantidade DESC, m.sigla ASC
            """
            cursor.execute(query_tipos, tuple(params))
            tipos_raw = cursor.fetchall()
            distribuicao_tipos = [
                {"tipo": r[0], "quantidade": int(r[1])}
                for r in tipos_raw
            ]

            # 3. Página de dados
            from_clause_data = from_clause + """
                LEFT JOIN senado.autoria a ON a.codigo_materia = m.codigo AND a.autor_principal = true
                LEFT JOIN senado.parlamentar autor ON a.codigo_parlamentar = autor.codigo
            """
            query = f"""
                WITH materia_filtrada AS (
                    SELECT DISTINCT ON (m.codigo)
                        m.codigo AS id,
                        m.sigla,
                        m.numero,
                        m.ano,
                        m.ementa,
                        m.data,
                        m.situacao_atual,
                        m.tramitando,
                        m.identificacao_processo,
                        m.descricao_identificacao,
                        m.data_situacao_atual,
                        m.url_documento,
                        m.objetivo,
                        m.tipo_conteudo,
                        m.casa_identificadora,
                        m.ente_identificador,
                        m.data_ultima_atualizacao,
                        autor.nome_parlamentar AS autor_principal,
                        a.autor_texto
                    {from_clause_data}
                    {where_clause}
                    ORDER BY m.codigo, m.data DESC NULLS LAST, m.ano DESC
                )
                SELECT id, sigla, numero, ano, ementa, data,
                       situacao_atual, tramitando, identificacao_processo,
                       descricao_identificacao, data_situacao_atual,
                       url_documento, objetivo, tipo_conteudo,
                       casa_identificadora, ente_identificador,
                       data_ultima_atualizacao, autor_principal, autor_texto
                FROM materia_filtrada
                ORDER BY ano DESC, sigla, numero
                LIMIT %s OFFSET %s
            """
            params_data = [*params, limite, offset]
            cursor.execute(query, tuple(params_data))
            resultados = cursor.fetchall()

            return {
                "materia": [
                    {
                        "id": r[0],
                        "siglaTipo": r[1],
                        "numero": r[2],
                        "ano": r[3],
                        "ementa": r[4],
                        "dataApresentacao": r[5].isoformat() if hasattr(r[5], 'isoformat') else str(r[5]) if r[5] else None,
                        "situacaoAtual": r[6],
                        "tramitando": r[7],
                        "identificacao": r[8],
                        "tipoDocumento": r[9],
                        "dataSituacaoAtual": r[10].isoformat() if hasattr(r[10], 'isoformat') else str(r[10]) if r[10] else None,
                        "urlDocumento": r[11],
                        "objetivo": r[12],
                        "tipoConteudo": r[13],
                        "casaIdentificadora": r[14],
                        "enteIdentificador": r[15],
                        "dataUltimaAtualizacao": r[16].isoformat() if hasattr(r[16], 'isoformat') else str(r[16]) if r[16] else None,
                        "autor_principal": r[17] or r[18]
                    }
                    for r in resultados
                ],
                "paginacao": {
                    "total": total_items,
                    "pagina": pagina,
                    "total_paginas": total_paginas,
                    "itens_por_pagina": limite
                },
                "estatisticas": {
                    "total": total_items,
                    "tipos_diferentes": len(distribuicao_tipos),
                    "tipo_mais_frequente": distribuicao_tipos[0]["tipo"] if distribuicao_tipos else None,
                    "distribuicao_tipos": distribuicao_tipos
                }
            }
    except Exception as e:
        _log.error(f"Erro ao buscar matéria: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar matéria")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/emendas", summary="Busca uma lista de emendas parlamentares do Senado")
def get_lista_emendas(
    legislatura: int,
    nome_senador: str = Query(None),
    ano: int = Query(None),
    pagina: int = 1
):
    itens_por_pagina = 15
    offset = (pagina - 1) * itens_por_pagina
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            filtros_base = []
            params_base = []

            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                filtros_base.append("CAST(e.ano AS INTEGER) BETWEEN %s AND %s")
                params_base.extend([start_year, end_year])
                filtros_base.append("""
                    EXISTS (
                        SELECT 1
                        FROM senado.mandato m
                        WHERE m.codigo_parlamentar = p.codigo
                          AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text)
                    )
                """)
                params_base.extend([legislatura, legislatura])
            else:
                filtros_base.append("""
                    EXISTS (
                        SELECT 1
                        FROM senado.mandato m
                        WHERE m.codigo_parlamentar = p.codigo
                          AND (
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4
                                                         AND 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4 + 3
                              OR
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4
                                                         AND 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4 + 3
                          )
                    )
                """)

            if nome_senador:
                filtros_base.append("(p.nome_completo ILIKE %s OR p.nome_parlamentar ILIKE %s)")
                params_base.extend([f"%{nome_senador}%", f"%{nome_senador}%"])

            if ano:
                filtros_base.append("CAST(e.ano AS INTEGER) = %s")
                params_base.append(ano)

            where_clause = " AND ".join(filtros_base)

            # 1. Total para paginação
            query_count = f"""
                WITH senadores_nomes AS (
                    SELECT codigo as id, lower(nome_completo) as nome FROM senado.parlamentar
                    UNION
                    SELECT codigo as id, lower(nome_parlamentar) as nome FROM senado.parlamentar
                )
                SELECT COUNT(*)
                FROM portal.emendas e
                JOIN senadores_nomes s ON lower(e.nome_autor) = s.nome
                JOIN senado.parlamentar p ON p.codigo = s.id
                WHERE {where_clause}
            """

            cursor.execute(query_count, tuple(params_base))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + itens_por_pagina - 1) // itens_por_pagina

            # 2. Dados paginados
            query = f"""
                WITH senadores_nomes AS (
                    SELECT codigo as id, lower(nome_completo) as nome FROM senado.parlamentar
                    UNION
                    SELECT codigo as id, lower(nome_parlamentar) as nome FROM senado.parlamentar
                )
                SELECT 
                    p.nome_parlamentar as senador,
                    e.codigo_emenda as codigo,
                    e.ano,
                    e.tipo_emenda as tipo,
                    e.valor_pago,
                    e.funcao,
                    e.localidade_gasto as localidade
                FROM portal.emendas e
                JOIN senadores_nomes s ON lower(e.nome_autor) = s.nome
                JOIN senado.parlamentar p ON p.codigo = s.id
                WHERE {where_clause}
                ORDER BY CAST(e.ano AS INTEGER) DESC, e.valor_pago DESC
                LIMIT %s OFFSET %s
            """
            params = [*params_base, itens_por_pagina, offset]

            cursor.execute(query, tuple(params))
            res = cursor.fetchall()

            return {
                "emendas": [
                    {
                        "senador": r[0],
                        "codigo": r[1],
                        "ano": r[2],
                        "tipo": r[3],
                        "valorPago": float(r[4]),
                        "funcao": r[5],
                        "localidade": r[6]
                    }
                    for r in res
                ],
                "paginacao": {
                    "total": total_items,
                    "pagina": pagina,
                    "total_paginas": total_paginas,
                    "itens_por_pagina": itens_por_pagina
                }
            }
    except Exception as e:
        _log.error(f"Erro ao buscar emendas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar emendas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/emendas/resumo", summary="Obtém resumo das emendas do Senado")
@ttl_cache(maxsize=32, ttl=300, cache_name="senado_emendas_resumo")
def get_resumo_emendas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            params_base = []
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                where_base = """
                    CAST(e.ano AS INTEGER) BETWEEN %s AND %s
                    AND EXISTS (
                        SELECT 1
                        FROM senado.mandato m
                        WHERE m.codigo_parlamentar = p.codigo
                          AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text)
                    )
                """
                params_base.extend([start_year, end_year, legislatura, legislatura])
            else:
                where_base = """
                    EXISTS (
                        SELECT 1
                        FROM senado.mandato m
                        WHERE m.codigo_parlamentar = p.codigo
                          AND (
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4
                                                         AND 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4 + 3
                              OR
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4
                                                         AND 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4 + 3
                          )
                    )
                """

            base_cte = f"""
                WITH senadores_nomes AS (
                    SELECT codigo as id, lower(nome_completo) as nome FROM senado.parlamentar
                    UNION
                    SELECT codigo as id, lower(nome_parlamentar) as nome FROM senado.parlamentar
                ),
                emendas_base AS (
                    SELECT
                        e.valor_pago,
                        e.localidade_gasto,
                        e.funcao,
                        p.codigo,
                        p.nome_parlamentar,
                        p.sigla_partido,
                        p.uf,
                        p.url_foto
                    FROM portal.emendas e
                    JOIN senadores_nomes s ON lower(e.nome_autor) = s.nome
                    JOIN senado.parlamentar p ON s.id = p.codigo
                    WHERE {where_base}
                )
            """

            # 1. Totais gerais
            query_totais = base_cte + """
                SELECT
                    COUNT(DISTINCT codigo) as total_senadores,
                    COUNT(DISTINCT localidade_gasto) as total_municipios,
                    COUNT(DISTINCT funcao) as total_areas,
                    COALESCE(SUM(valor_pago), 0) as valor_total
                FROM emendas_base
            """
            cursor.execute(query_totais, tuple(params_base))
            totais_row = cursor.fetchone()

            valor_total_real = float(totais_row[3]) if totais_row and totais_row[3] else 0.0
            base_percentual = valor_total_real if valor_total_real > 0 else 1.0

            # 2. Distribuição por área
            query_areas = base_cte + """
                SELECT funcao, SUM(valor_pago) as valor_total
                FROM emendas_base
                GROUP BY funcao
                ORDER BY valor_total DESC
            """
            cursor.execute(query_areas, tuple(params_base))
            areas_raw = cursor.fetchall()
            areas_formatadas = [
                {
                    "nome": r[0] if r[0] else "Outros",
                    "valor": float(r[1]),
                    "percentual": round((float(r[1]) / base_percentual) * 100, 1)
                }
                for r in areas_raw
            ]

            # 3. Top 10 senadores
            query_top = base_cte + """
                SELECT
                    codigo, nome_parlamentar, sigla_partido, uf, url_foto,
                    SUM(valor_pago) as total_valor
                FROM emendas_base
                GROUP BY codigo, nome_parlamentar, sigla_partido, uf, url_foto
                ORDER BY total_valor DESC
                LIMIT 10
            """
            cursor.execute(query_top, tuple(params_base))
            top_senadores = cursor.fetchall()

            return {
                "totais": {
                    "senadores": totais_row[0],
                    "municipios": totais_row[1],
                    "areas": totais_row[2],
                    "valor_total": valor_total_real
                },
                "areas": areas_formatadas,
                "ranking": [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "partido": r[2] if r[2] else "S/P",
                        "estado": r[3] if r[3] else "BR",
                        "emendasTotal": float(r[5]),
                        "foto": get_foto_url_senado(r[0], r[4]) if r[4] and str(r[4]).strip() else "/placeholder-user.svg"
                    }
                    for r in top_senadores
                ]
            }
    except Exception as e:
        _log.error(f"Erro ao buscar resumo emendas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar emendas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/materia/votacao", summary="Obtém o histórico de votações de um projeto legislativo")
def get_votacao_materia(legislatura: int, codigo_materia: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    m.sigla || ' ' || m.numero || '/' || m.ano AS materia,
                    m.ementa,
                    p.nome_parlamentar,
                    p.sigla_partido,
                    p.uf,
                    vp.sigla_descricao_voto AS voto,
                    vp.descricao_resultado AS resultado,
                    p.codigo,
                    p.url_foto
                FROM senado.votacao_parlamentar vp
                JOIN senado.materia m ON vp.codigo_materia = m.codigo
                JOIN senado.parlamentar p ON vp.codigo_parlamentar = p.codigo
                WHERE vp.codigo_materia = %s
                  AND vp.sigla_descricao_voto NOT IN ('P-NRV', 'AP', 'Presidente (art. 51 RISF)', 'LS', 'NCom')
            """
            params = [codigo_materia]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query += " AND m.ano BETWEEN %s AND %s"
                params.extend([start_year, end_year])

            query += " ORDER BY m.ano DESC, m.sigla, m.numero, p.nome_parlamentar"
            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            return {
                "votacao": [
                    {
                        "materia": r[0],
                        "ementa": r[1],
                        "nomeParlamentar": r[2],
                        "siglaPartido": r[3],
                        "uf": r[4],
                        "voto": r[5],
                        "resultado": r[6],
                        "codigo": r[7],
                        "foto": get_foto_url_senado(r[7], r[8])
                    }
                    for r in resultados
                ]
            }
    except Exception as e:
        _log.error(f"Erro ao buscar votação: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar votação")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/{senador_codigo}/emendas/lista", summary="Obtém a lista de emendas parlamentares de um senador")
def get_emendas_lista_senador(legislatura: int, senador_codigo: int, pagina: int = 1):
    itens_per_page = 15
    offset = (pagina - 1) * itens_per_page
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            filtros_base = []
            params_base = [senador_codigo]

            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                filtros_base.append("CAST(e.ano AS INTEGER) BETWEEN %s AND %s")
                params_base.extend([start_year, end_year])
                filtros_base.append("""
                    EXISTS (
                        SELECT 1
                        FROM senado.mandato m
                        WHERE m.codigo_parlamentar = s.codigo
                          AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text)
                    )
                """)
                params_base.extend([legislatura, legislatura])
            else:
                filtros_base.append("""
                    EXISTS (
                        SELECT 1
                        FROM senado.mandato m
                        WHERE m.codigo_parlamentar = s.codigo
                          AND (
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4
                                                         AND 2023 - (57 - CAST(m.primeira_legislatura AS INTEGER)) * 4 + 3
                              OR
                              CAST(e.ano AS INTEGER) BETWEEN 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4
                                                         AND 2023 - (57 - CAST(m.segunda_legislatura AS INTEGER)) * 4 + 3
                          )
                    )
                """)

            where_clause = " AND ".join(filtros_base)

            # 1. Total para paginação
            query_count = f"""
                SELECT COUNT(*)
                FROM portal.emendas e
                JOIN senado.parlamentar s 
                   ON (lower(e.nome_autor) = lower(s.nome_completo) 
                       OR lower(e.nome_autor) = lower(s.nome_parlamentar))
                WHERE s.codigo = %s
                  AND {where_clause}
            """

            cursor.execute(query_count, tuple(params_base))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + itens_per_page - 1) // itens_per_page

            # 2. Dados paginados (Seleção Seletiva)
            query = f"""
                SELECT 
                    e.codigo_emenda as codigo,
                    e.ano,
                    e.tipo_emenda as tipo,
                    e.valor_pago,
                    e.funcao,
                    e.localidade_gasto as localidade
                FROM portal.emendas e
                JOIN senado.parlamentar s 
                  ON (lower(e.nome_autor) = lower(s.nome_completo) 
                      OR lower(e.nome_autor) = lower(s.nome_parlamentar))
                WHERE s.codigo = %s
                  AND {where_clause}
            """
            query += " ORDER BY CAST(e.ano AS INTEGER) DESC, e.valor_pago DESC LIMIT %s OFFSET %s"
            params = [*params_base, itens_per_page, offset]
            cursor.execute(query, tuple(params))
            res = cursor.fetchall()
            
            return {
                "emendas": [
                    {
                        "codigo": r[0],
                        "ano": r[1],
                        "tipo": r[2],
                        "valorPago": float(r[3]),
                        "funcao": r[4],
                        "localidade": r[5]
                    }
                    for r in res
                ],
                "paginacao": {
                    "total": total_items,
                    "pagina": pagina,
                    "total_paginas": total_paginas,
                    "itens_por_pagina": itens_per_page
                }
            }
    except Exception as e:
        _log.error(f"Erro ao buscar emendas do senador: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar emendas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/empresas/estatisticas", summary="Obtém estatísticas gerais das empresas")
def get_estatisticas_empresas(legislatura: int):
    """
    Retorna estatísticas de empresas fornecedoras dos senadores.
    Calcula os dados em tempo real a partir da tabela de despesas CEAPS.
    """
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # Determinar o período da legislatura
            if legislatura and legislatura > 0:
                start_year, end_year = legislatura_anos(legislatura)
                filtro_ano = "AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s"
                params_ano = [start_year, end_year]
            else:
                filtro_ano = ""
                params_ano = []
            
            # 1. Estatísticas Gerais - calculadas em tempo real
            query_gerais = f"""
                SELECT 
                    COUNT(DISTINCT d.cpf_cnpj) as total_empresas,
                    COALESCE(SUM(d.valor_reembolsado), 0) as total_pago,
                    COUNT(*) as total_contratos
                FROM senado.despesa_ceaps d
                WHERE d.cpf_cnpj IS NOT NULL AND TRIM(d.cpf_cnpj) != ''
                  {filtro_ano}
            """
            cursor.execute(query_gerais, tuple(params_ano))
            res_stats = cursor.fetchone()
            
            total_empresas = res_stats[0] if res_stats else 0
            total_pago = float(res_stats[1]) if res_stats else 0.0
            total_contratos = res_stats[2] if res_stats else 0
            
            if total_empresas == 0:
                return {
                    "total_empresas": 0,
                    "total_pago": 0.0,
                    "total_contratos": 0,
                    "top_10_empresas": [],
                    "top_20_empresas": []
                }

            # 2. Ranking - agrupado por CPF/CNPJ apenas (consolidando variações de nome)
            query_ranking = f"""
                SELECT 
                    d.cpf_cnpj,
                    MAX(d.fornecedor) as fornecedor,
                    COALESCE(SUM(d.valor_reembolsado), 0) as valor_total,
                    COUNT(*) as qtd_contratos,
                    STRING_AGG(DISTINCT p.sigla_partido, ', ' ORDER BY p.sigla_partido) as partidos
                FROM senado.despesa_ceaps d
                LEFT JOIN senado.parlamentar p ON d.cod_senador = p.codigo
                WHERE d.cpf_cnpj IS NOT NULL AND TRIM(d.cpf_cnpj) != ''
                  {filtro_ano}
                GROUP BY d.cpf_cnpj
                ORDER BY valor_total DESC
                LIMIT 20
            """
            cursor.execute(query_ranking, tuple(params_ano))
            res_ranking = cursor.fetchall()
            
            total_pago_real = total_pago if total_pago > 0 else 1.0
            
            top_20 = [
                {
                    "rank": idx + 1,
                    "empresa": r[1] or f"CNPJ/CPF {r[0]}",
                    "partidos": r[4] or "N/A",
                    "cnpj": r[0],
                    "valor_total": float(r[2]),
                    "contratos": int(r[3]),
                    "percentual": round((float(r[2]) / total_pago_real) * 100, 2)
                }
                for idx, r in enumerate(res_ranking)
            ]

            return {
                "total_empresas": total_empresas,
                "total_pago": total_pago,
                "total_contratos": total_contratos,
                "top_10_empresas": [
                    {"empresa": r["empresa"], "valor_total": r["valor_total"]}
                    for r in top_20[:10]
                ],
                "top_20_empresas": top_20
            }
    except Exception as e:
        _log.error(f"Erro ao buscar estatísticas de empresas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar estatísticas de empresas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/resumo-principal", summary="Resumo otimizado para a página principal (Senado)")
def get_resumo_principal_senado(legislatura: int = 0):
    """
    Retorna apenas o total de senadores e o total de gastos dos últimos 12 meses.
    Ideal para dashboards e página inicial.
    Se legislatura não for informada, usa a maior legislatura disponível no banco.
    """
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        usar_legislatura = legislatura if (legislatura and legislatura > 0) else None
        
        if not usar_legislatura:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM senado.mandato")
                total_mandatos = cursor.fetchone()[0]
            
            if total_mandatos == 0:
                return {
                    "total_parlamentares": 0,
                    "gastos_12_meses": 0.0,
                    "db_vazio": True
                }
        
        with conn.cursor() as cursor:
            # 1. Total de senadores
            query_total = "SELECT COUNT(DISTINCT codigo_parlamentar) FROM senado.mandato"
            params_total: list[object] = []
            if usar_legislatura:
                query_total += " WHERE primeira_legislatura::text = %s::text OR segunda_legislatura::text = %s::text"
                params_total.extend([str(usar_legislatura), str(usar_legislatura)])
            
            cursor.execute(query_total, tuple(params_total))
            total_senadores = cursor.fetchone()[0] or 0

            # 2. Gastos dos últimos 12 meses
            # Usa COALESCE para considerar data_despesa OU ano/mes quando data_despesa for NULL
            query_gastos = """
                SELECT COALESCE(SUM(d.valor_reembolsado), 0)
                FROM senado.despesa_ceaps d
                WHERE COALESCE(
                    d.data_despesa,
                    TO_DATE(CAST(d.ano AS TEXT) || '-' || LPAD(CAST(d.mes AS TEXT), 2, '0') || '-01', 'YYYY-MM-DD')
                ) >= (CURRENT_DATE - INTERVAL '12 months')
            """
            params_gastos: list[object] = []
            if usar_legislatura:
                # Para filtrar por legislatura, é necessário garantir que o senador
                # estava em exercício no período da despesa (baseado no ano)
                start_year, end_year = legislatura_anos(usar_legislatura)
                query_gastos = """
                    SELECT COALESCE(SUM(d.valor_reembolsado), 0)
                    FROM senado.despesa_ceaps d
                    WHERE COALESCE(
                        d.data_despesa,
                        TO_DATE(CAST(d.ano AS TEXT) || '-' || LPAD(CAST(d.mes AS TEXT), 2, '0') || '-01', 'YYYY-MM-DD')
                    ) >= (CURRENT_DATE - INTERVAL '12 months')
                      AND CAST(d.ano AS INTEGER) BETWEEN %s AND %s
                      AND EXISTS (
                          SELECT 1 FROM senado.mandato m
                          WHERE m.codigo_parlamentar = d.cod_senador
                            AND (m.primeira_legislatura::text = %s::text OR m.segunda_legislatura::text = %s::text)
                      )
                """
                params_gastos.extend([start_year, end_year, str(usar_legislatura), str(usar_legislatura)])
            else:
                # Sem filtro de legislatura: busca gastos de todos os senadores
                query_gastos = """
                    SELECT COALESCE(SUM(d.valor_reembolsado), 0)
                    FROM senado.despesa_ceaps d
                    WHERE COALESCE(
                        d.data_despesa,
                        TO_DATE(CAST(d.ano AS TEXT) || '-' || LPAD(CAST(d.mes AS TEXT), 2, '0') || '-01', 'YYYY-MM-DD')
                    ) >= (CURRENT_DATE - INTERVAL '12 months')
                """
            
            cursor.execute(query_gastos, tuple(params_gastos))
            gastos_12_meses = float(cursor.fetchone()[0] or 0)

            db_vazio = total_senadores == 0

            return {
                "total_parlamentares": total_senadores,
                "gastos_12_meses": gastos_12_meses,
                "db_vazio": db_vazio
            }
    except Exception as e:
        _log.error(f"Erro no resumo principal do Senado: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar resumo")
    finally:
        if conn:
            db.release_db_connection(conn)
