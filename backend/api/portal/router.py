"""
Router para dados do Portal da Transparência (emendas parlamentares).
"""

from fastapi import APIRouter, HTTPException, Query
from database import db
from database.db import db_cursor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/emendas")
def get_emendas(
    ano: int = Query(None, description="Filtrar por ano"),
    autor: str = Query(None, description="Filtrar por nome do autor (parcial, case-insensitive)"),
    tipo: str = Query(None, description="Filtrar por tipo de emenda (Individual, Bancada, etc.)"),
    funcao: str = Query(None, description="Filtrar por função (Saúde, Educação, etc.)"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
):
    """
    Retorna emendas parlamentares do Portal da Transparência.
    Suporta filtros por ano, autor, tipo, função e paginação.
    """
    try:
        with db_cursor() as cursor:
            where_clauses = []
            params = []

            if ano is not None:
                where_clauses.append("e.ano = %s")
                params.append(ano)
            if autor:
                where_clauses.append("e.nome_autor ILIKE %s")
                params.append(f"%{autor}%")
            if tipo:
                where_clauses.append("e.tipo_emenda ILIKE %s")
                params.append(f"%{tipo}%")
            if funcao:
                where_clauses.append("e.funcao ILIKE %s")
                params.append(f"%{funcao}%")

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            # Total de registros
            cursor.execute(f"SELECT COUNT(*) FROM portal.emendas e {where_sql}", params)
            total = cursor.fetchone()[0]

            # Dados paginados
            cursor.execute(f"""
                SELECT e.id, e.codigo_emenda, e.ano, e.tipo_emenda,
                       e.autor, e.nome_autor, e.numero_emenda,
                       e.localidade_gasto, e.funcao, e.subfuncao,
                       e.valor_empenhado, e.valor_liquidado, e.valor_pago,
                       e.valor_resto_inscrito, e.valor_resto_cancelado, e.valor_resto_pago
                FROM portal.emendas e
                {where_sql}
                ORDER BY e.ano DESC, e.nome_autor ASC
                LIMIT %s OFFSET %s
            """, params + [limit, offset])

            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]

            emendas = []
            for row in rows:
                emenda = dict(zip(colnames, row))
                emendas.append(emenda)

            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "emendas": emendas,
            }
    except Exception as e:
        logger.error(f"Erro ao buscar emendas: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/emendas/resumo")
def get_emendas_resumo():
    """
    Retorna um resumo agregado das emendas: total por ano, total por tipo, etc.
    """
    try:
        with db_cursor() as cursor:
            # Total por ano
            cursor.execute("""
                SELECT ano, COUNT(*) as qtd, SUM(valor_empenhado) as total_empenhado,
                       SUM(valor_pago) as total_pago
                FROM portal.emendas
                GROUP BY ano
                ORDER BY ano DESC
            """)
            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            por_ano = [dict(zip(colnames, row)) for row in rows]

            # Total por tipo
            cursor.execute("""
                SELECT tipo_emenda, COUNT(*) as qtd, SUM(valor_empenhado) as total_empenhado
                FROM portal.emendas
                GROUP BY tipo_emenda
                ORDER BY qtd DESC
            """)
            rows = cursor.fetchall()
            colnames = [desc[0] for desc in cursor.description]
            por_tipo = [dict(zip(colnames, row)) for row in rows]

            # Total geral
            cursor.execute("""
                SELECT COUNT(*) as total_emendas,
                       SUM(valor_empenhado) as total_empenhado,
                       SUM(valor_pago) as total_pago
                FROM portal.emendas
            """)
            row = cursor.fetchone()
            colnames = [desc[0] for desc in cursor.description]
            total_geral = dict(zip(colnames, row))

            return {
                "total_geral": total_geral,
                "por_ano": por_ano,
                "por_tipo": por_tipo,
            }
    except Exception as e:
        logger.error(f"Erro ao buscar resumo de emendas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

