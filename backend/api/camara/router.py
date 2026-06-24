
from fastapi import APIRouter, HTTPException, Query
from datetime import date
import logging

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fragmentos SQL reutilizáveis para mapear deputado_id → nome (lower)
# ---------------------------------------------------------------------------

_NOMES_DEPUTADOS = (
    "SELECT id, lower(nome_civil) as nome FROM camara.deputados\n"
    "UNION\n"
    "SELECT deputado_id as id, lower(nome_eleitoral) as nome FROM camara.deputados_mandatos"
)

_NOMES_DEPUTADOS_COM_CIVIL = (
    "SELECT d.id, lower(d.nome_civil) as nome, d.nome_civil\n"
    "FROM camara.deputados d\n"
    "UNION\n"
    "SELECT m.deputado_id as id, lower(m.nome_eleitoral) as nome, m.nome_eleitoral as nome_civil\n"
    "FROM camara.deputados_mandatos m"
)

_IDS_DEPUTADOS = (
    "SELECT id FROM camara.deputados\n"
    "UNION\n"
    "SELECT deputado_id as id FROM camara.deputados_mandatos"
)

# Garanta que este import está correto para sua estrutura
import database.db as db
from database.utils import get_maior_legislatura_camara, get_legislatura_atual, periodo_legislatura, get_foto_url_camara, legislatura_anos
from database.cache import ttl_cache

router = APIRouter(
    prefix="/camara",
    tags=["Câmara"]
)


@router.get("/legislaturas", summary="Lista todas as legislaturas disponíveis na base")
def get_legislaturas_camara():
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            query = """
                SELECT DISTINCT legislatura_id
                FROM camara.deputados_mandatos
                ORDER BY legislatura_id DESC
            """
            cursor.execute(query)
            todas = [row[0] for row in cursor.fetchall()]
            # Filtra apenas legislaturas até a atual (não mostrar futuras)
            legislatura_atual = get_legislatura_atual()
            return [leg for leg in todas if leg <= legislatura_atual]
    except Exception as e:
        _log.error(f"Erro ao buscar legislaturas ativas camara: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar legislaturas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/maior-legislatura", summary="Retorna a maior legislatura disponível na base")
@ttl_cache(maxsize=1, ttl=3600, cache_name="camara_maior_legislatura")
def get_maior_legislatura_camara_endpoint():
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        maior_leg = get_maior_legislatura_camara(conn)
        if maior_leg is None:
            return {"maior_legislatura": None, "db_vazio": True}
        
        return {"maior_legislatura": maior_leg, "db_vazio": False}
    except Exception as e:
        _log.error(f"Erro ao buscar maior legislatura: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar maior legislatura")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/emendas", summary="Busca uma lista de emendas parlamentares")
def get_lista_emendas(
    legislatura: int,
    nome_deputado: str = Query(None),
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
            # 1. Total para paginação
            query_count = f"""
                WITH parlamentares_nomes AS (
{_NOMES_DEPUTADOS}
                )
                SELECT COUNT(*)
                FROM portal.emendas e
                JOIN parlamentares_nomes p ON lower(e.autor) = p.nome
            """
            
            # Adicionar filtro de legislatura se especificado
            where_conditions = []
            params_count = []
            
            if legislatura:
                query_count += """
                    JOIN camara.deputados_mandatos m ON p.id = m.deputado_id
                """
                where_conditions.append("m.legislatura_id = %s")
                params_count.append(legislatura)
            
            if nome_deputado:
                where_conditions.append("""p.id IN (
                    SELECT id FROM camara.deputados WHERE nome_civil ILIKE %s
                )""")
                params_count.append(f"%{nome_deputado}%")
            
            if ano:
                where_conditions.append("e.ano = %s")
                params_count.append(ano)
            
            if where_conditions:
                query_count += " WHERE " + " AND ".join(where_conditions)
            
            cursor.execute(query_count, tuple(params_count))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + itens_por_pagina - 1) // itens_por_pagina

            # 2. Dados paginados
            query = f"""
                WITH parlamentares_nomes AS (
{_NOMES_DEPUTADOS_COM_CIVIL}
                )
                SELECT 
                    p.nome_civil as deputado,
                    e.codigo_emenda as codigo,
                    e.ano,
                    e.tipo_emenda as tipo,
                    e.valor_pago,
                    e.funcao,
                    e.localidade_gasto as localidade,
                    p.id as deputado_id
                FROM portal.emendas e
                JOIN parlamentares_nomes p ON lower(e.autor) = p.nome
            """
            
            # Adicionar JOIN e filtros
            where_conditions_data = []
            params = []
            
            if legislatura:
                query += """
                    JOIN camara.deputados_mandatos m ON p.id = m.deputado_id
                """
                where_conditions_data.append("m.legislatura_id = %s")
                params.append(legislatura)
            
            if nome_deputado:
                where_conditions_data.append("p.nome_civil ILIKE %s")
                params.append(f"%{nome_deputado}%")
            
            if ano:
                where_conditions_data.append("e.ano = %s")
                params.append(ano)
            
            if where_conditions_data:
                query += " WHERE " + " AND ".join(where_conditions_data)
                
            query += " ORDER BY e.ano DESC, e.valor_pago DESC LIMIT %s OFFSET %s"
            params.extend([itens_por_pagina, offset])

            cursor.execute(query, tuple(params))
            res = cursor.fetchall()

            return {
                "emendas": [
                    {
                        "deputado": r[0],
                        "codigo": r[1],
                        "ano": r[2],
                        "tipo": r[3],
                        "valorPago": float(r[4]),
                        "funcao": r[5],
                        "localidade": r[6],
                        "deputadoId": r[7]
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

@router.get("/{legislatura}/emendas/resumo", summary="Obtém resumo das emendas")
@ttl_cache(maxsize=16, ttl=300, cache_name="camara_emendas_resumo")
def get_resumo_emendas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # Base query components
            leg_join = ""
            leg_where = ""
            leg_params = []
            
            if legislatura:
                leg_join = ""
                start_year, end_year = legislatura_anos(legislatura)
                leg_where = "WHERE CAST(e.ano AS INTEGER) BETWEEN %s AND %s"
                leg_params = [start_year, end_year]
            else:
                leg_join = ""
                leg_where = ""
                leg_params = []
            
            # 1. Totais Gerais
            query_totais = f"""
                WITH parlamentares_nomes AS (
{_IDS_DEPUTADOS}
                ),
                deputados_emendas AS (
                    SELECT e.id, e.valor_pago, e.localidade_gasto, e.funcao, p.id as deputado_id
                    FROM portal.emendas e
                    JOIN (
{_NOMES_DEPUTADOS}
                    ) p ON lower(e.autor) = p.nome
                    {leg_join}
                    {leg_where}
                )
                SELECT 
                    COUNT(DISTINCT deputado_id) as total_deputados,
                    COUNT(DISTINCT localidade_gasto) as total_municipios,
                    COUNT(DISTINCT funcao) as total_areas,
                    COALESCE(SUM(valor_pago), 0) as valor_total
                FROM deputados_emendas
            """
            cursor.execute(query_totais, tuple(leg_params))
            totais_row = cursor.fetchone()
            valor_total_global = float(totais_row[3]) if totais_row[3] else 1.0
            
            # 2. Distribuição por Área
            query_areas = f"""
                WITH deputados_emendas AS (
                    SELECT e.valor_pago, e.funcao, p.id as deputado_id
                    FROM portal.emendas e
                    JOIN (
{_NOMES_DEPUTADOS}
                    ) p ON lower(e.autor) = p.nome
                    {leg_join}
                    {leg_where}
                )
                SELECT funcao, SUM(valor_pago) as valor_total
                FROM deputados_emendas
                GROUP BY funcao
                ORDER BY valor_total DESC
            """
            cursor.execute(query_areas, tuple(leg_params))
            areas_raw = cursor.fetchall()
            
            areas_formatadas = [
                {
                    "nome": r[0] if r[0] else "Outros",
                    "valor": float(r[1]),
                    "percentual": round((float(r[1]) / (valor_total_global or 1)) * 100, 1)
                }
                for r in areas_raw
            ]
            
            # 3. Top 10 Deputados
            query_top = f"""
                WITH deputados_emendas AS (
                    SELECT e.valor_pago, p.id as deputado_id
                    FROM portal.emendas e
                    JOIN (
{_NOMES_DEPUTADOS}
                    ) p ON lower(e.autor) = p.nome
                    {leg_join}
                    {leg_where}
                )
                SELECT 
                    d.id, d.nome_civil, m.sigla_partido, m.sigla_uf,
                    SUM(de.valor_pago) as total_valor
                FROM deputados_emendas de
                JOIN camara.deputados d ON de.deputado_id = d.id
                LEFT JOIN (
                    SELECT DISTINCT ON (deputado_id) deputado_id, sigla_partido, sigla_uf
                    FROM camara.deputados_mandatos
                    ORDER BY deputado_id, id DESC
                ) m ON d.id = m.deputado_id
                GROUP BY d.id, d.nome_civil, m.sigla_partido, m.sigla_uf
                ORDER BY total_valor DESC
                LIMIT 10
            """
            cursor.execute(query_top, tuple(leg_params))
            top_deputados = cursor.fetchall()

            return {
                "totais": {
                    "deputados": totais_row[0],
                    "municipios": totais_row[1],
                    "areas": totais_row[2],
                    "valor_total": valor_total_global
                },
                "areas": areas_formatadas,
                "ranking": [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "partido": r[2] if r[2] else "S/P",
                        "estado": r[3] if r[3] else "BR",
                        "emendasTotal": float(r[4]),
                        "foto": get_foto_url_camara(r[0], f"https://www.camara.leg.br/internet/deputado/bandep/{r[0]}.jpg")
                    }
                    for r in top_deputados
                ]
            }
    except Exception as e:
        _log.error(f"Erro ao obter resumo de emendas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar resumo de emendas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/proposicoes", summary="Busca uma lista de projetos legislativos")
def get_lista_proposicoes(
    legislatura: int,
    siglaTipo: str = Query(None), 
    ano: int = Query(None), 
    ementa: str = Query(None), 
    deputado: str = Query(None),
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
                FROM camara.proposicoes p
            """
            if deputado:
                from_clause += """
                    INNER JOIN camara.votacoes_proposicoes vp ON p.id = vp.proposicao_id
                    INNER JOIN camara.votacoes_votos vv ON vp.votacao_id = vv.votacao_id
                    INNER JOIN camara.deputados d ON vv.deputado_id = d.id
                """

            filtros = ["1=1"]
            params = []

            if siglaTipo:
                filtros.append("p.sigla_tipo = %s")
                params.append(siglaTipo)
            if ano:
                filtros.append("p.ano = %s")
                params.append(ano)
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                filtros.append("p.ano BETWEEN %s AND %s")
                params.extend([start_year, end_year])
            if ementa:
                filtros.append("p.ementa ILIKE %s")
                params.append(f"%{ementa}%")
            if deputado:
                filtros.append("d.nome_civil ILIKE %s")
                params.append(f"%{deputado}%")
            if votadas:
                filtros.append("EXISTS (SELECT 1 FROM camara.votacoes_proposicoes vp WHERE vp.proposicao_id = p.id)")

            where_clause = " WHERE " + " AND ".join(filtros)

            # 1. Total para paginação
            query_count = f"""
                SELECT COUNT(DISTINCT p.id)
                {from_clause}
                {where_clause}
            """
            cursor.execute(query_count, tuple(params))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + limite - 1) // limite

            # 2. Distribuição por tipo (sobre todo o conjunto filtrado)
            query_tipos = f"""
                SELECT COALESCE(p.sigla_tipo, 'N/D') as sigla_tipo, COUNT(DISTINCT p.id) as quantidade
                {from_clause}
                {where_clause}
                GROUP BY COALESCE(p.sigla_tipo, 'N/D')
                ORDER BY quantidade DESC, sigla_tipo ASC
            """
            cursor.execute(query_tipos, tuple(params))
            tipos_raw = cursor.fetchall()
            distribuicao_tipos = [
                {"tipo": r[0], "quantidade": int(r[1])}
                for r in tipos_raw
            ]

            # 3. Dados paginados
            query_data = f"""
                SELECT DISTINCT ON (p.id)
                    p.id,
                    p.sigla_tipo as "siglaTipo",
                    p.numero,
                    p.ano,
                    p.ementa,
                    p.data_apresentacao as "dataApresentacao",
                    COALESCE(
                        (SELECT d.nome_civil 
                         FROM camara.proposicoes_autores pa 
                         JOIN camara.deputados d ON pa.deputado_id = d.id 
                         WHERE pa.proposicao_id = p.id AND pa.proponente = TRUE 
                         LIMIT 1),
                        (SELECT d.nome_civil 
                         FROM camara.proposicoes_autores pa 
                         JOIN camara.deputados d ON pa.deputado_id = d.id 
                         WHERE pa.proposicao_id = p.id 
                         ORDER BY pa.ordem_assinatura NULLS LAST 
                         LIMIT 1),
                        'Desconhecido'
                    ) as autor_principal,
                    p.descricao_tipo,
                    p.ementa_detalhada,
                    p.keywords,
                    p.url_inteiro_teor,
                    p.uri
                {from_clause}
                {where_clause}
                ORDER BY p.id DESC
                LIMIT %s OFFSET %s
            """
            params_data = [*params, limite, offset]
            cursor.execute(query_data, tuple(params_data))
            res = cursor.fetchall()

            return {
                "proposicoes": [
                    {
                        "id": r[0],
                        "siglaTipo": r[1],
                        "numero": r[2],
                        "ano": r[3],
                        "ementa": r[4],
                        "dataApresentacao": r[5].isoformat() if hasattr(r[5], 'isoformat') else str(r[5]) if r[5] else None,
                        "autor_principal": r[6],
                        "descricaoTipo": r[7],
                        "ementaDetalhada": r[8],
                        "keywords": r[9],
                        "urlInteiroTeor": r[10],
                        "uri": r[11]
                    }
                    for r in res
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
        _log.error(f"Erro ao buscar proposições: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar proposições")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/proposicoes/{proposicao_id}/votos", summary="Obtém o histórico de votos de um projeto legislativo")
def get_votos_proposicao(legislatura: int, proposicao_id: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    v.id AS votacao_id,
                    v.data as data_votacao,
                    v.descricao,
                    d.id AS deputado_id,
                    d.nome_civil,
                    vv.tipo_voto AS voto
                FROM camara.votacoes_proposicoes vp
                INNER JOIN camara.votacoes v ON vp.votacao_id = v.id
                INNER JOIN camara.votacoes_votos vv ON v.id = vv.votacao_id
                INNER JOIN camara.deputados d ON vv.deputado_id = d.id
                WHERE vp.proposicao_id = %s AND vv.tipo_voto != 'Artigo 17'
            """
            params = [proposicao_id]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query += " AND EXTRACT(YEAR FROM v.data) BETWEEN %s AND %s"
                params.extend([start_year, end_year])
            
            query += " ORDER BY v.data DESC, d.nome_civil ASC"
            cursor.execute(query, tuple(params))
            resultados = cursor.fetchall()
            
            votacoes_dict = {}
            for r in resultados:
                vot_id = r[0]
                if vot_id not in votacoes_dict:
                    votacoes_dict[vot_id] = {
                        "id_votacao": vot_id,
                        "data": r[1].isoformat() if hasattr(r[1], 'isoformat') else str(r[1]) if r[1] else None,
                        "descricao": r[2],
                        "total_votos": 0,
                        "lista_votos": []
                    }
                
                votacoes_dict[vot_id]["lista_votos"].append({
                    "deputado_id": r[3],
                    "nome": r[4],
                    "voto": r[5],
                    "foto": get_foto_url_camara(r[3], f"https://www.camara.leg.br/internet/deputado/bandep/{r[3]}.jpg")
                })
                votacoes_dict[vot_id]["total_votos"] += 1

            return {
                "proposicao_id": proposicao_id,
                "historico_votacoes": list(votacoes_dict.values())
            }
    except Exception as e:
        _log.error(f"Erro ao buscar votos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar votos")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/lista", summary="Lista todos os deputados ativos")
def get_todos_deputados(
    legislatura: int,
    incluir_suplentes: bool = Query(False, description="Se true, inclui suplentes na listagem")
):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            query = """
                SELECT DISTINCT ON (d.id)
                    d.id, 
                    d.nome_civil,
                    m.sigla_partido,
                    m.sigla_uf as uf,
                    m.url_foto
                FROM camara.deputados d
                INNER JOIN camara.deputados_mandatos m ON d.id = m.deputado_id
                WHERE m.sigla_uf IS NOT NULL
            """
            params = []
            if legislatura:
                query += " AND m.legislatura_id = %s"
                params.append(legislatura)
            
            # Por padrão, filtra apenas deputados titulares ou efetivados
            # A menos que incluir_suplentes seja True
            if not incluir_suplentes:
                query += " AND m.condicao_eleitoral IN ('Titular', 'Efetivado')"
                
            query += " ORDER BY d.id, m.id DESC"
            cursor.execute(query, tuple(params))
            res = cursor.fetchall()

            return [
                {
                    "id": r[0],
                    "nome_civil": r[1],
                    "sigla_partido": r[2] if r[2] else "S/P",
                    "uf": r[3],
                    "foto": get_foto_url_camara(r[0], r[4])
                }
                for r in res
            ]
    except Exception as e:
        _log.error(f"Erro ao buscar lista de deputados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar lista de deputados")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/estatisticas", summary="Obtém estatísticas gerais dos deputados")
@ttl_cache(maxsize=16, ttl=300, cache_name="camara_estatisticas")
def get_estatisticas_gerais(
    legislatura: int,
    incluir_suplentes: bool = Query(False, description="Se true, inclui suplentes nas estatísticas")
):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # Filtro base: por padrão, apenas deputados titulares ou efetivados
            condicao_filter = "" if incluir_suplentes else " AND m.condicao_eleitoral IN ('Titular', 'Efetivado')"
            
            # 1. Total de Deputados
            query_total = "SELECT COUNT(DISTINCT deputado_id) as total from camara.deputados_mandatos m"
            params = []
            if legislatura:
                query_total += " WHERE m.legislatura_id = %s" + condicao_filter
                params.append(legislatura)
            else:
                if condicao_filter:
                    query_total += " WHERE 1=1" + condicao_filter
            
            cursor.execute(query_total, tuple(params))
            total_deputados = cursor.fetchone()[0] or 0

            # 2. Distribuição por Região
            query_regiao = """
                SELECT 
                    CASE
                        WHEN m.sigla_uf IN ('AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO') THEN 'Norte'
                        WHEN m.sigla_uf IN ('AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE') THEN 'Nordeste'
                        WHEN m.sigla_uf IN ('DF', 'GO', 'MT', 'MS') THEN 'Centro-Oeste'
                        WHEN m.sigla_uf IN ('ES', 'MG', 'RJ', 'SP') THEN 'Sudeste'
                        WHEN m.sigla_uf IN ('PR', 'RS', 'SC') THEN 'Sul'
                        ELSE 'Outros'
                    END AS regiao,
                    COUNT(DISTINCT m.deputado_id) as quantidade
                FROM camara.deputados_mandatos m
                WHERE m.sigla_uf IS NOT NULL
            """
            if legislatura:
                query_regiao += " AND m.legislatura_id = %s"
            
            query_regiao += condicao_filter
            query_regiao += " GROUP BY regiao ORDER BY quantidade DESC"
            
            cursor.execute(query_regiao, (legislatura,) if legislatura else ())
            deputados_regiao = [{"name": r[0], "value": int(r[1])} for r in cursor.fetchall()]

            # 3. Total de UFs com deputados na seleção
            query_ufs = """
                SELECT COUNT(DISTINCT m.sigla_uf)
                FROM camara.deputados_mandatos m
                WHERE m.sigla_uf IS NOT NULL
            """
            params_ufs = []
            if legislatura:
                query_ufs += " AND m.legislatura_id = %s"
                params_ufs.append(legislatura)
            
            query_ufs += condicao_filter

            cursor.execute(query_ufs, tuple(params_ufs))
            total_ufs = cursor.fetchone()[0] or 0

            return {
                "total_deputados": int(total_deputados),
                "total_regioes": len(deputados_regiao),
                "total_ufs": int(total_ufs),
                "deputados_por_regiao": deputados_regiao
            }
    except Exception as e:
        _log.error(f"Erro ao buscar estatísticas gerais: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar estatísticas")
    finally:
        if conn:
            db.release_db_connection(conn)



@router.get("/{legislatura}/comparar", summary="Compara perfil e gastos entre dois deputados")
def get_comparativo_deputados(legislatura: int, id1: int, id2: int, ano: int = None):
    if id1 == id2:
        raise HTTPException(status_code=400, detail="Escolha dois deputados diferentes para comparar.")

    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # 1. Buscar Perfis
            query_perfil = """
                SELECT DISTINCT ON (d.id)
                    d.id, d.nome_civil, m.sigla_partido, m.sigla_uf, 
                    d.email, d.data_nascimento, d.escolaridade, d.uf_nascimento
                FROM camara.deputados d
                LEFT JOIN camara.deputados_mandatos m ON d.id = m.deputado_id
                WHERE d.id IN (%s, %s)
                ORDER BY d.id, m.id DESC
            """
            cursor.execute(query_perfil, (id1, id2))
            perfis_raw = cursor.fetchall()
            
            if len(perfis_raw) < 2:
                raise HTTPException(status_code=404, detail="Um ou ambos os deputados não foram encontrados.")
            
            comparacao = {}
            for r in perfis_raw:
                pid = r[0]
                comparacao[pid] = {
                    "id": pid,
                    "nome_civil": r[1],
                    "sigla_partido": r[2],
                    "sigla_uf": r[3],
                    "email": r[4],
                    "data_nascimento": r[5].isoformat() if isinstance(r[5], date) else None,
                    "escolaridade": r[6],
                    "uf_nascimento": r[7],
                    "foto": get_foto_url_camara(pid, f"https://www.camara.leg.br/internet/deputado/bandep/{pid}.jpg"),
                    "total_gasto": 0.0,
                    "qtd_despesas": 0,
                    "maior_categoria": {"nome": "-", "valor": 0.0},
                    "despesas": [],
                    "categorias": []
                }
            
            # 2. Buscar Despesas
            query_stats = """
                SELECT 
                    m.deputado_id, d.tipo_despesa, 
                    SUM(d.valor_documento) as total, COUNT(d.id) as qtd
                FROM camara.deputados_despesas d
                JOIN camara.deputados_mandatos m ON d.mandato_id = m.id
                WHERE m.deputado_id IN (%s, %s)
            """
            params = [id1, id2]
            if ano:
                query_stats += " AND d.ano = %s"
                params.append(ano)
            if legislatura:
                query_stats += " AND m.legislatura_id = %s"
                params.append(legislatura)
                
            query_stats += " GROUP BY m.deputado_id, d.tipo_despesa"

            cursor.execute(query_stats, tuple(params))
            stats = cursor.fetchall()

            for s in stats:
                dep_id, valor = s[0], float(s[2])
                if dep_id in comparacao:
                    comparacao[dep_id]["total_gasto"] += valor
                    comparacao[dep_id]["qtd_despesas"] += s[3]
                    comparacao[dep_id]["categorias"].append({"categoria": s[1], "valor": valor})

                    if valor > comparacao[dep_id]["maior_categoria"]["valor"]:
                        comparacao[dep_id]["maior_categoria"] = {
                            "nome": s[1].replace("_", " ").title() if s[1] else "-",
                            "valor": valor
                        }

            # 3. Buscar Últimas Despesas (histórico completo, mais recentes primeiro)
            for dep_id in [id1, id2]:
                cursor.execute("""
                    SELECT d.ano, d.mes, d.tipo_despesa, d.valor_documento as valor, d.url_documento
                    FROM camara.deputados_despesas d
                    JOIN camara.deputados_mandatos m ON d.mandato_id = m.id
                    WHERE m.deputado_id = %s
                    ORDER BY
                        COALESCE(
                            d.data_documento,
                            TO_DATE(d.ano::text || '-' || LPAD(d.mes::text, 2, '0') || '-01', 'YYYY-MM-DD')
                        ) DESC,
                        d.id DESC
                    LIMIT 12
                """, (dep_id,))
                recentes = cursor.fetchall()
                
                comparacao[dep_id]["despesas"] = [
                    {
                        "ano": r[0],
                        "mes": r[1],
                        "tipo_despesa": r[2],
                        "valor": float(r[3]),
                        "url_documento": r[4]
                    }
                    for r in recentes
                ]
            
            return [comparacao[id1], comparacao[id2]]
    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"Erro ao comparar deputados: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar comparação")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/{deputado_id}", summary="Obtém os detalhes do perfil e despesas do deputado pelo ID (via path)")
def get_perfil_deputado(legislatura: int, deputado_id: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            # 1. Buscar Perfil (Resiliente a legislatura inexistente)
            query_perfil = """
                SELECT d.id, d.nome_civil, d.cpf, d.sexo, d.email, d.data_nascimento, 
                       d.escolaridade, d.uf_nascimento, d.municipio_nascimento, 
                       m.sigla_partido, m.sigla_uf, m.legislatura_id
                FROM camara.deputados d
                LEFT JOIN camara.deputados_mandatos m ON d.id = m.deputado_id
                WHERE d.id = %s
            """
            params_perfil = [deputado_id]
            
            if legislatura:
                # Ordena para colocar a legislatura pedida no topo (se existir), senão a mais recente
                query_perfil += " ORDER BY (m.legislatura_id = %s) DESC NULLS LAST, m.id DESC LIMIT 1"
                params_perfil.append(legislatura)
            else:
                query_perfil += " ORDER BY m.id DESC LIMIT 1"
            
            cursor.execute(query_perfil, tuple(params_perfil))
            row = cursor.fetchone()
            
            if not row:
                # Verifica se o ID pelo menos existe na tabela base
                cursor.execute("SELECT id FROM camara.deputados WHERE id = %s", (deputado_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=404, detail=f"Deputado com ID {deputado_id} não encontrado")
                else:
                    # Existe mas sem mandatos registrados? (Raro)
                    raise HTTPException(status_code=404, detail=f"Deputado com ID {deputado_id} não possui mandatos registrados")

            # A legislatura efetivamente encontrada
            leg_efetiva = row[11]
            
            res = {
                "id": row[0],
                "nome_civil": row[1],
                "cpf": row[2],
                "sexo": row[3],
                "email": row[4],
                "data_nascimento": row[5].isoformat() if isinstance(row[5], date) else None,
                "escolaridade": row[6],
                "uf_nascimento": row[7],
                "municipio_nascimento": row[8],
                "sigla_partido": row[9] if row[9] else "S/P",
                "sigla_uf": row[10],
                "foto": get_foto_url_camara(row[0], f"https://www.camara.leg.br/internet/deputado/bandep/{row[0]}.jpg"),
                "legislatura_exibida": 0 if legislatura == 0 else leg_efetiva
            }

            # 2. Buscar Resumo de Emendas (Total de emendas pago ao autor)
            query_emendas_resumo = f"""
                WITH parlamentares_nomes AS (
{_NOMES_DEPUTADOS}
                )
                SELECT SUM(e.valor_pago) as total_emendas
                FROM portal.emendas e
                JOIN parlamentares_nomes p ON lower(e.autor) = p.nome
                WHERE p.id = %s
            """
            params_emendas = [deputado_id]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                query_emendas_resumo += " AND CAST(e.ano AS INTEGER) BETWEEN %s AND %s"
                params_emendas.extend([start_year, end_year])

            cursor.execute(query_emendas_resumo, tuple(params_emendas))
            row_emendas = cursor.fetchone()
            total_emendas = float(row_emendas[0]) if row_emendas and row_emendas[0] else 0.0

            # 5. Legislaturas Ativas
            query_legis = """
                SELECT DISTINCT legislatura_id
                FROM camara.deputados_mandatos
                WHERE deputado_id = %s
                ORDER BY legislatura_id DESC
            """
            cursor.execute(query_legis, (deputado_id,))
            legislaturas_ativas = [row[0] for row in cursor.fetchall()]

            return {
                **res,
                "total_emendas": total_emendas,
                "legislaturas_ativas": legislaturas_ativas
            }

    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"Erro ao buscar perfil do deputado: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar perfil")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/{deputado_id}/despesas", summary="Obtém o extrato de despesas de um deputado")
def get_despesas_deputado(legislatura: int, deputado_id: int, pagina: int = Query(1, ge=1)):
    itens_per_page = 20
    offset = (pagina - 1) * itens_per_page
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        with conn.cursor() as cursor:
            query_count = """
                SELECT COUNT(*)
                FROM camara.deputados_despesas AS desp
                JOIN camara.deputados_mandatos AS mand ON desp.mandato_id = mand.id
                WHERE mand.deputado_id = %s
            """
            params_count = [deputado_id]
            if legislatura:
                query_count += " AND mand.legislatura_id = %s"
                params_count.append(legislatura)

            cursor.execute(query_count, tuple(params_count))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + itens_per_page - 1) // itens_per_page

            query_recente = """
                SELECT
                    desp.ano, desp.mes, desp.tipo_despesa,
                    desp.valor_documento as valor, desp.url_documento
                FROM camara.deputados_despesas AS desp
                JOIN camara.deputados_mandatos AS mand ON desp.mandato_id = mand.id
                WHERE mand.deputado_id = %s
            """
            params_recente = [deputado_id]
            if legislatura:
                query_recente += " AND mand.legislatura_id = %s"
                params_recente.append(legislatura)

            query_recente += " ORDER BY desp.ano DESC, desp.mes DESC LIMIT %s OFFSET %s"
            params_recente.extend([itens_per_page, offset])
            cursor.execute(query_recente, tuple(params_recente))
            despesas_raw = cursor.fetchall()

            query_categorias = """
                SELECT desp.tipo_despesa as categoria, SUM(desp.valor_documento) as valor
                FROM camara.deputados_despesas AS desp
                JOIN camara.deputados_mandatos AS mand ON desp.mandato_id = mand.id
                WHERE mand.deputado_id = %s
            """
            params_cat = [deputado_id]
            if legislatura:
                query_categorias += " AND mand.legislatura_id = %s"
                params_cat.append(legislatura)

            query_categorias += " GROUP BY desp.tipo_despesa ORDER BY valor DESC"
            cursor.execute(query_categorias, tuple(params_cat))
            categorias_raw = cursor.fetchall()
            categorias = [{"categoria": r[0], "valor": float(r[1])} for r in categorias_raw]
            total_despesas = sum(c["valor"] for c in categorias)

            return {
                "despesas": [
                    {
                        "ano": r[0],
                        "mes": r[1],
                        "tipo_despesa": r[2],
                        "valor": float(r[3]),
                        "url_documento": r[4]
                    }
                    for r in despesas_raw
                ],
                "total_despesas": total_despesas,
                "categorias": categorias,
                "paginacao": {
                    "total": total_items,
                    "pagina": pagina,
                    "total_paginas": total_paginas,
                    "itens_por_pagina": itens_per_page
                }
            }
    except Exception as e:
        _log.error(f"Erro ao buscar despesas do deputado: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar despesas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/{deputado_id}/emendas", summary="Obtém a lista de emendas parlamentares de um deputado")
def get_emendas_deputado(legislatura: int, deputado_id: int, pagina: int = Query(1, ge=1)):
    itens_per_page = 15
    offset = (pagina - 1) * itens_per_page
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        with conn.cursor() as cursor:
            filtros = f"""
                FROM portal.emendas e
                JOIN (
{_NOMES_DEPUTADOS}
                ) d ON lower(e.autor) = d.nome
                WHERE d.id = %s
            """
            params_base = [deputado_id]
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                filtros += " AND CAST(e.ano AS INTEGER) BETWEEN %s AND %s"
                params_base.extend([start_year, end_year])

            query_count = "SELECT COUNT(*) " + filtros
            cursor.execute(query_count, tuple(params_base))
            total_items = cursor.fetchone()[0]
            total_paginas = (total_items + itens_per_page - 1) // itens_per_page

            query = """
                SELECT 
                    e.codigo_emenda as codigo,
                    e.ano,
                    e.tipo_emenda as tipo,
                    e.valor_pago,
                    e.funcao,
                    e.localidade_gasto as localidade
            """
            query += filtros
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
        _log.error(f"Erro ao buscar emendas do deputado: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar emendas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/despesas/evolucao", summary="Obtém a evolução de gastos da Câmara (mensal ou anual)")
@ttl_cache(maxsize=16, ttl=300, cache_name="camara_despesas_evolucao")
def get_evolucao_despesas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        with conn.cursor() as cursor:
            if legislatura:
                start_year, end_year = legislatura_anos(legislatura)
                cursor.execute("""
                    SELECT d.ano, d.mes, SUM(d.valor_documento) as valor
                    FROM camara.deputados_despesas d
                    JOIN camara.deputados_mandatos m ON d.mandato_id = m.id
                    WHERE m.legislatura_id = %s AND d.ano BETWEEN %s AND %s
                    GROUP BY d.ano, d.mes ORDER BY d.ano ASC, d.mes ASC
                """, (legislatura, start_year, end_year))
            else:
                cursor.execute("""
                    SELECT d.ano, 0 as mes, SUM(d.valor_documento) as valor
                    FROM camara.deputados_despesas d
                    GROUP BY d.ano ORDER BY d.ano ASC
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


@router.get("/{legislatura}/despesas/estatisticas", summary="Obtém o panorama geral de gastos da Câmara")
@ttl_cache(maxsize=16, ttl=300, cache_name="camara_despesas_estatisticas")
def get_estatisticas_despesas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT total_gastos, total_empresas_contratadas FROM stats.camara_despesas_totais WHERE legislatura_id = %s",
                (legislatura,)
            )
            row = cursor.fetchone()
            total_geral = float(row[0]) if row else 0.0
            total_empresas = int(row[1]) if row else 0

            cursor.execute(
                "SELECT COALESCE(SUM(valor), 0) FROM stats.camara_despesas_evolucao WHERE legislatura_id = %s AND (ano, mes) >= (EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '12 months')::int, EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '12 months')::int)",
                (legislatura,)
            )
            total_12_meses = float(cursor.fetchone()[0] or 0)

            cursor.execute(
                "SELECT categoria, valor FROM stats.camara_despesas_categorias WHERE legislatura_id = %s ORDER BY valor DESC",
                (legislatura,)
            )
            resultados_categoria = cursor.fetchall()

            gastos_categoria = []
            total_outros = 0.0
            LIMITE_TOP = 9

            for i, r in enumerate(resultados_categoria):
                nome_formatado = r[0].title().replace("_", " ") if r[0] else "Outros"
                valor = float(r[1])

                if i < LIMITE_TOP:
                    gastos_categoria.append({"categoria": nome_formatado, "valor": valor})
                else:
                    total_outros += valor

            if total_outros > 0:
                gastos_categoria.append({"categoria": "Outros", "valor": total_outros})

            cursor.execute(
                "SELECT ano, mes, valor FROM stats.camara_despesas_evolucao WHERE legislatura_id = %s ORDER BY ano DESC, mes DESC LIMIT 12",
                (legislatura,)
            )
            gastos_mensais = [{"ano": r[0], "mes": r[1], "valor": float(r[2])} for r in cursor.fetchall()]

            if legislatura:
                cursor.execute(
                    "SELECT ano, mes, valor FROM stats.camara_despesas_evolucao WHERE legislatura_id = %s ORDER BY ano ASC, mes ASC",
                    (legislatura,)
                )
                evolucao_gastos = [{"ano": r[0], "mes": r[1], "valor": float(r[2])} for r in cursor.fetchall()]
            else:
                cursor.execute(
                    "SELECT ano, 0 as mes, SUM(valor) FROM stats.camara_despesas_evolucao WHERE legislatura_id = 0 GROUP BY ano ORDER BY ano ASC"
                )
                evolucao_gastos = [{"ano": r[0], "mes": r[1], "valor": float(r[2])} for r in cursor.fetchall()]

            cursor.execute(
                "SELECT estado, valor FROM stats.camara_despesas_estados WHERE legislatura_id = %s ORDER BY valor DESC",
                (legislatura,)
            )
            gastos_estado = [{"estado": r[0], "valor": float(r[1])} for r in cursor.fetchall()]

            cursor.execute(
                "SELECT partido, valor FROM stats.camara_despesas_partidos WHERE legislatura_id = %s ORDER BY valor DESC",
                (legislatura,)
            )
            gastos_partido = [{"partido": r[0], "valor": float(r[1])} for r in cursor.fetchall()]

            cursor.execute(
                "SELECT deputado_id, nome_civil, sigla_partido, estado, total_gasto FROM stats.camara_despesas_deputados WHERE legislatura_id = %s ORDER BY total_gasto DESC LIMIT 10",
                (legislatura,)
            )
            gastos_dep_raw = cursor.fetchall()

            gastos_deputados = [
                {
                    "deputado_id": r[0], "nome_civil": r[1], "sigla_partido": r[2],
                    "estado": r[3], "total_gasto": float(r[4]),
                    "foto": get_foto_url_camara(r[0], f"https://www.camara.leg.br/internet/deputado/bandep/{r[0]}.jpg")
                }
                for r in gastos_dep_raw
            ]

            return {
                "total_gastos_12_meses": total_12_meses,
                "total_12_meses": total_12_meses,
                "total_gastos": total_geral,
                "total_empresas_contratadas": total_empresas,
                "gastos_por_categoria": gastos_categoria,
                "gastos_por_mes": gastos_mensais,
                "gastos_por_estado": gastos_estado,
                "gastos_por_partido": gastos_partido,
                "gastos_deputados": gastos_deputados,
                "evolucao_gastos": evolucao_gastos
            }
    except Exception as e:
        _log.error(f"Erro ao buscar estatísticas de despesas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar estatísticas de despesas")
    finally:
        if conn:
            db.release_db_connection(conn)

@router.get("/{legislatura}/despesas/panorama", summary="Obtém o panorama de gastos para a página de despesas da Câmara (leve)")
@ttl_cache(maxsize=16, ttl=300, cache_name="camara_despesas_panorama")
def get_panorama_despesas(legislatura: int):
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT total_gastos, total_empresas_contratadas FROM stats.camara_despesas_totais WHERE legislatura_id = %s",
                (legislatura,)
            )
            row = cursor.fetchone()
            total_geral = float(row[0]) if row else 0.0
            total_empresas = int(row[1]) if row else 0

            cursor.execute(
                "SELECT categoria, valor FROM stats.camara_despesas_categorias WHERE legislatura_id = %s ORDER BY valor DESC",
                (legislatura,)
            )
            resultados_categoria = cursor.fetchall()

            gastos_categoria = []
            total_outros = 0.0
            LIMITE_TOP = 9

            for i, r in enumerate(resultados_categoria):
                nome_formatado = r[0].title().replace("_", " ") if r[0] else "Outros"
                valor = float(r[1])

                if i < LIMITE_TOP:
                    gastos_categoria.append({"categoria": nome_formatado, "valor": valor})
                else:
                    total_outros += valor

            if total_outros > 0:
                gastos_categoria.append({"categoria": "Outros", "valor": total_outros})

            cursor.execute(
                "SELECT partido, valor FROM stats.camara_despesas_partidos WHERE legislatura_id = %s ORDER BY valor DESC",
                (legislatura,)
            )
            gastos_partido = [{"partido": r[0], "valor": float(r[1])} for r in cursor.fetchall()]

            cursor.execute(
                "SELECT deputado_id, nome_civil, sigla_partido, estado, total_gasto FROM stats.camara_despesas_deputados WHERE legislatura_id = %s ORDER BY total_gasto DESC LIMIT 10",
                (legislatura,)
            )
            gastos_dep_raw = cursor.fetchall()

            gastos_deputados = [
                {
                    "deputado_id": r[0], "nome_civil": r[1], "sigla_partido": r[2],
                    "estado": r[3], "total_gasto": float(r[4]),
                    "foto": get_foto_url_camara(r[0], f"https://www.camara.leg.br/internet/deputado/bandep/{r[0]}.jpg")
                }
                for r in gastos_dep_raw
            ]

            return {
                "total_gastos": total_geral,
                "total_empresas_contratadas": total_empresas,
                "gastos_por_categoria": gastos_categoria,
                "gastos_por_partido": gastos_partido,
                "gastos_deputados": gastos_deputados
            }
    except Exception as e:
        _log.error(f"Erro ao buscar panorama de despesas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar panorama de despesas")
    finally:
        if conn:
            db.release_db_connection(conn)


@router.get("/{legislatura}/empresas/estatisticas", summary="Obtém as estatísticas e ranking das empresas contratadas")
def get_estatisticas_empresas(legislatura: int, limit: int = 20):
    """
    Retorna estatísticas de empresas fornecedoras dos deputados.
    Lê da materialized view stats.camara_empresas_ranking (atualizada em background).
    """
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*), COALESCE(SUM(valor_total), 0), COALESCE(SUM(qtd_contratos), 0) FROM stats.camara_empresas_ranking WHERE legislatura_id = %s",
                (legislatura,)
            )
            ga, gp, gc = cursor.fetchone()
            total_empresas = ga or 0
            total_pago = float(gp) if gp else 0.0
            total_contratos = gc or 0

            if total_empresas == 0:
                return {"geral": {"total_empresas": 0, "total_pago": 0.0, "total_contratos": 0}, "ranking": []}

            cursor.execute(
                "SELECT cnpj, nome, valor_total, qtd_contratos, partidos FROM stats.camara_empresas_ranking WHERE legislatura_id = %s ORDER BY valor_total DESC LIMIT %s",
                (legislatura, limit)
            )
            res_ranking = cursor.fetchall()

            total_pago_real = total_pago if total_pago > 0 else 1.0

            ranking_formatado = [
                {
                    "rank": idx + 1,
                    "cnpj": r[0],
                    "nome": r[1] or f"CNPJ/CPF {r[0]}",
                    "valor_total": float(r[2]),
                    "contratos": int(r[3]),
                    "principais_partidos": r[4] or "N/A",
                    "percentual": round((float(r[2]) / total_pago_real) * 100, 2)
                }
                for idx, r in enumerate(res_ranking)
            ]

            return {
                "geral": {
                    "total_empresas": total_empresas,
                    "total_pago": total_pago,
                    "total_contratos": total_contratos
                },
                "ranking": ranking_formatado
            }
    except Exception as e:
        _log.error(f"Erro ao buscar estatísticas de empresas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar estatísticas de empresas")
    finally:
        if conn:
            db.release_db_connection(conn)



@router.get("/resumo-principal", summary="Resumo otimizado para a página principal (Câmara)")
def get_resumo_principal_camara(legislatura: int = 0):
    """
    Retorna apenas o total de deputados e o total de gastos dos últimos 12 meses.
    Ideal para dashboards e página inicial.
    Se legislatura não for informada (ou for 0), retorna dados de todas as legislaturas.
    """
    conn = None
    try:
        conn = db.get_db_connection()
        if not conn:
            raise HTTPException(status_code=503, detail="Banco de dados indisponível")
        
        # Se legislatura não foi informada (ou é 0), considera todas
        usar_legislatura = legislatura if (legislatura and legislatura > 0) else None
        
        if not usar_legislatura:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM camara.deputados_mandatos")
                if cursor.fetchone()[0] == 0:
                    return {
                        "total_parlamentares": 0,
                        "gastos_12_meses": 0.0,
                        "db_vazio": True
                    }
        
        with conn.cursor() as cursor:
            # 1. Total de deputados (titulares e efetivados)
            query_total = "SELECT COUNT(DISTINCT deputado_id) FROM camara.deputados_mandatos WHERE condicao_eleitoral IN ('Titular', 'Efetivado')"
            params_total = []
            if usar_legislatura:
                query_total += " AND legislatura_id = %s"
                params_total.append(usar_legislatura)
            
            cursor.execute(query_total, tuple(params_total))
            total_deputados = cursor.fetchone()[0] or 0

            # 2. Gastos dos últimos 12 meses
            query_gastos = """
                SELECT COALESCE(SUM(d.valor_documento), 0)
                FROM camara.deputados_despesas d
                WHERE TO_DATE(d.ano || '-' || LPAD(d.mes::text, 2, '0'), 'YYYY-MM')
                      >= (CURRENT_DATE - INTERVAL '12 months')
            """
            params_gastos = []
            if usar_legislatura:
                query_gastos = """
                    SELECT COALESCE(SUM(d.valor_documento), 0)
                    FROM camara.deputados_despesas d
                    JOIN camara.deputados_mandatos m ON d.mandato_id = m.id
                    WHERE m.legislatura_id = %s
                      AND TO_DATE(d.ano || '-' || LPAD(d.mes::text, 2, '0'), 'YYYY-MM')
                          >= (CURRENT_DATE - INTERVAL '12 months')
                """
                params_gastos.append(usar_legislatura)
            
            cursor.execute(query_gastos, tuple(params_gastos))
            gastos_12_meses = float(cursor.fetchone()[0] or 0)

            db_vazio = total_deputados == 0

            return {
                "total_parlamentares": total_deputados,
                "gastos_12_meses": gastos_12_meses,
                "db_vazio": db_vazio
            }
    except HTTPException:
        raise
    except Exception as e:
        _log.error(f"Erro no resumo principal da Câmara: {e}")
        raise HTTPException(status_code=500, detail="Erro ao processar resumo")
    finally:
        if conn:
            db.release_db_connection(conn)


