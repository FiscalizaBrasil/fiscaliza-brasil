"""
Funções utilitárias para consultas ao banco de dados.
"""

import os
import logging
from datetime import date


# ---------------------------------------------------------------------------
# Funções de conversão legislatura ↔ ano
# Fórmula: L = floor((Y - 1987) / 4) + 48  ↔  ano_início = 4 × L + 1795
# ---------------------------------------------------------------------------

def ano_para_legislatura(ano: int) -> int:
    """Converte um ano na legislatura correspondente."""
    return (ano - 1987) // 4 + 48


def legislatura_anos(legislatura: int) -> tuple[int, int]:
    """Retorna (ano_inicio, ano_fim) de uma legislatura."""
    inicio = 4 * legislatura + 1795
    return inicio, inicio + 3


def legislatura_anos_lista(legislatura: int) -> list[int]:
    """Retorna a lista de anos cobertos por uma legislatura."""
    inicio, fim = legislatura_anos(legislatura)
    return list(range(inicio, fim + 1))


def get_legislatura_atual() -> int:
    """Retorna a legislatura atual com base no ano corrente."""
    return ano_para_legislatura(date.today().year)


def get_maior_legislatura_camara(conn):
    """
    Retorna a maior legislatura disponível na tabela camara.deputados_mandatos,
    limitada à legislatura atual (não retorna legislaturas futuras).
    Retorna None se não houver nenhuma legislatura.
    """
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(legislatura_id) FROM camara.deputados_mandatos")
            result = cursor.fetchone()
            if result and result[0] is not None:
                return min(result[0], get_legislatura_atual())
            return None
    except Exception as e:
        logging.error(f"Erro ao buscar maior legislatura da Câmara: {e}")
        return None


def get_maior_legislatura_senado(conn):
    """
    Retorna a maior legislatura disponível no banco,
    limitada à legislatura atual (não retorna legislaturas futuras).
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
                return min(result[0], get_legislatura_atual())

            # 2. Fallback: senado.legislatura
            cursor.execute("""
                SELECT MAX(CAST(numero AS INTEGER))
                FROM senado.legislatura
                WHERE numero IS NOT NULL AND TRIM(numero) != ''
                  AND TRIM(numero) ~ '^\\d+$'
            """)
            result = cursor.fetchone()
            if result and result[0] is not None and result[0] > 0:
                return min(result[0], get_legislatura_atual())

            # 3. Fallback: calcular a partir dos anos das despesas
            cursor.execute("""
                SELECT MIN(ano), MAX(ano) FROM senado.despesa_ceaps
            """)
            row = cursor.fetchone()
            if row and row[0] and row[1]:
                min_ano, max_ano = int(row[0]), int(row[1])
                # Calcula a maior legislatura que cobre o intervalo
                maior_leg = ano_para_legislatura(int(max_ano))
                if maior_leg > 0:
                    return min(maior_leg, get_legislatura_atual())
                return None

            return None
    except Exception as e:
        logging.error(f"Erro ao buscar maior legislatura do Senado: {e}")
        return None



def get_ano_referencia_legislatura(conn, casa="camara"):
    """
    Retorna o ano de início da maior legislatura disponível no banco.
    Retorna (maior_legislatura, ano_inicio) ou (None, None) se vazio.
    """
    if casa == "camara":
        maior_leg = get_maior_legislatura_camara(conn)
    else:
        maior_leg = get_maior_legislatura_senado(conn)

    if maior_leg is None:
        return None, None

    return maior_leg, legislatura_anos(maior_leg)[0]


def periodo_legislatura(legislatura: int, maior_legislatura: int = 57):
    """
    Calcula o período (ano_inicio, ano_fim) de uma legislatura.
    Mantido para compatibilidade retroativa.
    """
    return legislatura_anos(legislatura)


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
