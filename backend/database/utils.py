"""
Funções utilitárias para consultas ao banco de dados.
"""

import os
import logging
from functools import lru_cache


def get_maior_legislatura_camara(conn):
    """
    Retorna a maior legislatura disponível na tabela camara.deputados_mandatos.
    Retorna None se não houver nenhuma legislatura.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(legislatura_id) FROM camara.deputados_mandatos")
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None
    except Exception as e:
        logging.error(f"Erro ao buscar maior legislatura da Câmara: {e}")
        return None


def get_maior_legislatura_senado(conn):
    """
    Retorna a maior legislatura disponível no banco.
    Tenta primeiro da tabela senado.mandato.
    Se vazio, tenta da tabela senado.legislatura.
    Se ainda vazio, calcula a partir dos anos das despesas.
    Retorna None se não houver nenhuma legislatura.
    """
    try:
        with conn.cursor() as cursor:
            # 1. Tenta de senado.mandato
            cursor.execute("""
                SELECT MAX(GREATEST(
                    COALESCE(NULLIF(primeira_legislatura, '')::INTEGER, 0),
                    COALESCE(NULLIF(segunda_legislatura, '')::INTEGER, 0)
                ))
                FROM senado.mandato
            """)
            result = cursor.fetchone()
            if result and result[0] is not None and result[0] > 0:
                return result[0]

            # 2. Fallback: senado.legislatura
            cursor.execute("""
                SELECT MAX(CAST(numero AS INTEGER))
                FROM senado.legislatura
                WHERE numero IS NOT NULL AND TRIM(numero) != ''
                  AND TRIM(numero) ~ '^\\d+$'
            """)
            result = cursor.fetchone()
            if result and result[0] is not None and result[0] > 0:
                return result[0]

            # 3. Fallback: calcular a partir dos anos das despesas
            cursor.execute("""
                SELECT MIN(ano), MAX(ano) FROM senado.despesa_ceaps
            """)
            row = cursor.fetchone()
            if row and row[0] and row[1]:
                min_ano, max_ano = int(row[0]), int(row[1])
                # Calcula a maior legislatura que cobre o intervalo
                maior_leg = 57 - (2023 - max_ano) // 4
                return maior_leg if maior_leg > 0 else None

            return None
    except Exception as e:
        logging.error(f"Erro ao buscar maior legislatura do Senado: {e}")
        return None



def get_ano_referencia_legislatura(conn, casa="camara"):
    """
    Retorna o ano de início da maior legislatura disponível no banco.
    Utiliza o fato de que a legislatura X começou em (2023 - (57 - X) * 4),
    mas substitui 57 pela maior legislatura real do banco.
    
    Retorna (maior_legislatura, ano_inicio) ou (None, None) se vazio.
    """
    if casa == "camara":
        maior_leg = get_maior_legislatura_camara(conn)
    else:
        maior_leg = get_maior_legislatura_senado(conn)
    
    if maior_leg is None:
        return None, None
    
    # Cada legislatura dura 4 anos. A legislatura 57 começou em 2023.
    ano_inicio = 2023 - (57 - maior_leg) * 4
    return maior_leg, ano_inicio


def periodo_legislatura(legislatura: int, maior_legislatura: int = 57):
    """
    Calcula o período (ano_inicio, ano_fim) de uma legislatura.
    Utiliza a maior legislatura conhecida como referência.
    
    A legislatura 57 começou em 2023. Cada legislatura dura 4 anos.
    """
    ano_inicio = 2023 - (57 - legislatura) * 4
    return ano_inicio, ano_inicio + 3


# ============================================================
# FOTOS LOCAIS
# ============================================================

FOTOS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "fotos"))


def get_foto_url_camara(deputado_id: int, url_externa: str = None) -> str:
    """
    Retorna a URL local da foto do deputado se o arquivo existir,
    caso contrário retorna a URL externa original ou placeholder.
    """
    for ext in [".jpg", ".jpeg", ".png"]:
        filepath = os.path.join(FOTOS_DIR, "camara", f"{deputado_id}{ext}")
        if os.path.isfile(filepath):
            return f"/api/fotos/camara/{deputado_id}{ext}"
    return url_externa or f"/placeholder-user.svg"


def get_foto_url_senado(codigo: int, url_externa: str = None) -> str:
    """
    Retorna a URL local da foto do senador se o arquivo existir,
    caso contrário retorna a URL externa original ou placeholder.
    """
    for ext in [".jpg", ".jpeg", ".png"]:
        filepath = os.path.join(FOTOS_DIR, "senado", f"{codigo}{ext}")
        if os.path.isfile(filepath):
            return f"/api/fotos/senado/{codigo}{ext}"
    return url_externa or "/placeholder-user.svg"
