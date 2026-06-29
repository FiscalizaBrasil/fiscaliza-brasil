#!/usr/bin/env python
"""
Script de importação de dados dos JSONs baixados pelo scraper para o banco de dados.
Lê os arquivos em backend/data/ e popula as tabelas.
"""

import os
import json
import logging
import sys
import time
import requests
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from database import db
    from database.db import savepoint
    from database.utils import legislatura_anos, legislatura_anos_lista
    from scripts.scraper.cache import is_cache_valid, save_json, remover_acentos
    from scripts.scraper.rate_limiter import senado_legis_limiter
    from scripts.scraper.verification import mark_verified
except ImportError as e:
    logging.error(f"Error importing database module: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


# Cache de senadores já buscados na API para evitar chamadas repetidas
_senadores_buscados_api = set()

# Lock global para evitar que múltiplas threads executem importação simultaneamente
_import_lock = threading.Lock()
_global_cache_lock = threading.Lock()

# Conjuntos para rastrear o que já foi importado (evita reimportação desnecessária)
_despesas_camara_importadas: set[int] = set()      # deputado_id já importados
_despesas_senado_importadas: set[int] = set()       # anos já importados
_emendas_importadas: set[str] = set()               # nomes de arquivos já importados



def _buscar_e_inserir_senador_api(cursor, cod_senador: int) -> bool:
    """
    Busca dados de um senador e insere na tabela parlamentar, com mandatos.
    Ordem de consulta: DB → cache em disco → API.
    Retorna True se conseguiu inserir, False caso contrário.
    
    API: GET https://legis.senado.leg.br/dadosabertos/senador/{codigo}?v=6
    API Mandatos: GET https://legis.senado.leg.br/dadosabertos/senador/{codigo}/mandatos?v=5
    """
    global _senadores_buscados_api
    
    # Evita chamadas repetidas para o mesmo código dentro da sessão
    with _global_cache_lock:
        if cod_senador in _senadores_buscados_api:
            return False
        _senadores_buscados_api.add(cod_senador)
    
    detalhes_dir = os.path.join(DATA_DIR, "senado", "senadores", str(cod_senador))
    cache_path = os.path.join(detalhes_dir, "detalhes.json")
    
    # 1. Tenta carregar do cache em disco
    if is_cache_valid(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logging.info(f"Senador {cod_senador}: carregado do cache em disco.")
    else:
        # 2. Busca na API
        url = f"https://legis.senado.leg.br/dadosabertos/senador/{cod_senador}?v=6"
        headers = {"accept": "application/json"}
        
        logging.info(f"Buscando dados do senador {cod_senador} na API...")
        try:
            senado_legis_limiter.acquire()
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            save_json(data, cache_path)
        except requests.exceptions.Timeout:
            logging.warning(f"Timeout ao buscar senador {cod_senador} na API")
            return False
        except requests.exceptions.HTTPError as e:
            status_code = response.status_code if response is not None else 0
            if status_code == 404:
                logging.warning(f"Senador {cod_senador} não encontrado na API (404)")
            else:
                logging.warning(f"Erro HTTP ao buscar senador {cod_senador}: {e}")
            return False
        except Exception as e:
            logging.warning(f"Erro ao buscar senador {cod_senador} na API: {e}")
            return False
    
    # Navega na estrutura do JSON
    parlamentar = (
        data.get("DetalheParlamentar", {})
        .get("Parlamentar", {})
    )
    
    if not parlamentar:
        logging.warning(f"API não retornou dados para o senador {cod_senador}")
        return False
    
    ident = parlamentar.get("IdentificacaoParlamentar", {})
    
    codigo = int(ident.get("CodigoParlamentar", 0))
    if not codigo or codigo != cod_senador:
        logging.warning(f"Código retornado pela API ({codigo}) não corresponde ao solicitado ({cod_senador})")
        return False
    
    nome_parlamentar = ident.get("NomeParlamentar", "").strip()
    nome_completo = ident.get("NomeCompletoParlamentar", "").strip()
    sexo = ident.get("SexoParlamentar", "")
    sigla_partido = ident.get("SiglaPartidoParlamentar", "")
    uf = ident.get("UfParlamentar", "")
    url_foto = ident.get("UrlFotoParlamentar", "")
    url_pagina = ident.get("UrlPaginaParlamentar", "")
    email = ident.get("EmailParlamentar", "")
    
    if not nome_parlamentar:
        nome_parlamentar = f"Senador {cod_senador}"
    
    # 1. Insere/ignora parlamentar
    cursor.execute("""
        INSERT INTO senado.parlamentar
            (codigo, nome_parlamentar, nome_completo, sexo,
             sigla_partido, uf, url_foto, url_pagina, email)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (codigo) DO NOTHING
    """, (codigo, nome_parlamentar, nome_completo, sexo,
          sigla_partido, uf, url_foto, url_pagina, email))
    
    # 2. Tenta buscar mandatos em endpoint separado
    try:
        url_mandatos = f"https://legis.senado.leg.br/dadosabertos/senador/{cod_senador}/mandatos?v=5"
        headers = {"accept": "application/json"}
        senado_legis_limiter.acquire()
        resp_mandatos = requests.get(url_mandatos, headers=headers, timeout=10)
        if resp_mandatos.status_code == 200:
            dados_mandatos = resp_mandatos.json()
            mandatos = (
                dados_mandatos.get("MandatoParlamentar", {})
                .get("Parlamentar", {})
                .get("Mandatos", {})
                .get("Mandato", [])
            )
            if isinstance(mandatos, dict):
                mandatos = [mandatos]
            for mandato in mandatos:
                codigo_mandato = mandato.get("CodigoMandato", "")
                if codigo_mandato:
                    uf_mandato = mandato.get("UfParlamentar", uf)
                    descricao = mandato.get("DescricaoParticipacao", "")
                    
                    for leg_key in ["PrimeiraLegislaturaDoMandato", "SegundaLegislaturaDoMandato"]:
                        leg_info = mandato.get(leg_key)
                        if leg_info:
                            num_leg = leg_info.get("NumeroLegislatura")
                            data_inicio = leg_info.get("DataInicio")
                            data_fim = leg_info.get("DataFim")
                            if num_leg:
                                cursor.execute("""
                                    INSERT INTO senado.legislatura (numero, data_inicio, data_fim)
                                    VALUES (%s, %s, %s)
                                    ON CONFLICT (numero) DO NOTHING
                                """, (num_leg, data_inicio, data_fim))
                    
                    prim_leg = mandato.get("PrimeiraLegislaturaDoMandato", {})
                    seg_leg = mandato.get("SegundaLegislaturaDoMandato")
                    primeira_leg = prim_leg.get("NumeroLegislatura", "") if prim_leg else ""
                    segunda_leg = seg_leg.get("NumeroLegislatura", "") if seg_leg else ""

                    if not primeira_leg or not primeira_leg.strip():
                        logging.warning(
                            f"Mandato {codigo_mandato} do senador {codigo} "
                            f"ignorado (via API): primeira_legislatura vazia."
                        )
                        continue

                    if segunda_leg is None:
                        segunda_leg = ""

                    cursor.execute("""
                        INSERT INTO senado.mandato
                            (codigo_mandato, codigo_parlamentar, uf,
                             descricao_participacao,
                             primeira_legislatura, segunda_legislatura)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (codigo_mandato, codigo_parlamentar) DO NOTHING
                    """, (codigo_mandato, codigo, uf_mandato,
                          descricao, primeira_leg, segunda_leg))
    except Exception as e:
        logging.warning(f"Não foi possível buscar mandatos do senador {cod_senador}: {e}")
    
    logging.info(f"Senador {cod_senador} ({nome_parlamentar}) inserido via API.")
    return True


def _capitalizar_nome(nome: str) -> str:
    """Converte nome em CAIXA ALTA para capitalização adequada (ex: ISMAEL DOS SANTOS -> Ismael dos Santos)."""
    if not nome or not nome.strip():
        return nome
    excecoes = {"de", "da", "do", "das", "dos", "e"}
    palavras = nome.strip().split()
    resultado = []
    for i, palavra in enumerate(palavras):
        p = palavra.lower()
        if i > 0 and p in excecoes:
            resultado.append(p)
        else:
            resultado.append(palavra.capitalize())
    return " ".join(resultado)


# Cache para evitar chamadas repetidas à API de detalhes de deputados
_deputados_detalhes_cache: dict[int, dict] = {}  # dep_id -> {situacao, condicao_eleitoral, nome_eleitoral, nome_civil}


def _buscar_situacao_deputado(dep_id: int) -> dict:
    """
    Busca detalhes de um deputado na API da Câmara (GET /deputados/{id}).
    Retorna um dict com situacao, condicao_eleitoral, nome_eleitoral e nome_civil.
    
    Usa cache para evitar chamadas repetidas à API.
    """
    global _deputados_detalhes_cache
    
    with _global_cache_lock:
        if dep_id in _deputados_detalhes_cache:
            return _deputados_detalhes_cache[dep_id]
    
    resultado = {}
    try:
        url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}"
        headers = {"accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        dados = data.get("dados", {})
        ultimo_status = dados.get("ultimoStatus", {})
        resultado["situacao"] = ultimo_status.get("situacao")
        resultado["condicao_eleitoral"] = ultimo_status.get("condicaoEleitoral")
        resultado["nome_eleitoral"] = ultimo_status.get("nomeEleitoral") or ultimo_status.get("nome")
        resultado["nome_civil"] = _capitalizar_nome(dados.get("nomeCivil") or "") or None
        
        with _global_cache_lock:
            _deputados_detalhes_cache[dep_id] = resultado
        time.sleep(0.2)  # Rate limiting
        return resultado
    except Exception as e:
        logging.warning(f"Erro ao buscar detalhes do deputado {dep_id}: {e}")
        resultado = {"situacao": None, "condicao_eleitoral": None, "nome_eleitoral": None, "nome_civil": None}
        with _global_cache_lock:
            _deputados_detalhes_cache[dep_id] = resultado
        return resultado


# ============================================================
# HELPERS DE IMPORTAÇÃO ATÔMICA (operam em cursor, sem commit)
# ============================================================

def _importar_despesas_cursor(cursor, deputado_id: int, legislatura_id: int, mandato_id: str) -> int:
    despesas_dir = os.path.join(
        DATA_DIR, "camara", "deputados", str(deputado_id), "despesas", str(legislatura_id)
    )
    if not os.path.isdir(despesas_dir):
        return 0

    inseridos = 0
    json_count = 0
    for fname in sorted(os.listdir(despesas_dir)):
        if not fname.endswith(".json"):
            continue
        filepath = os.path.join(despesas_dir, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        dados = data.get("dados", [])
        if not dados:
            continue
        json_count += len(dados)
        for despesa in dados:
            inseridos += _inserir_despesa(cursor, despesa, mandato_id)

    if json_count > 0:
        cursor.execute(
            "SELECT COUNT(*) FROM camara.deputados_despesas dd "
            "JOIN camara.deputados_mandatos dm ON dm.id = dd.mandato_id "
            "WHERE dm.deputado_id = %s AND dm.legislatura_id = %s",
            (deputado_id, legislatura_id),
        )
        db_count = cursor.fetchone()[0]
        if json_count == db_count:
            mark_verified("camara_despesas", f"{deputado_id}_{legislatura_id}", json_count, db_count)

    return inseridos


def _importar_detalhes_cursor(cursor, deputado_id: int) -> int:
    filepath = os.path.join(DATA_DIR, "camara", "deputados", str(deputado_id), "detalhes.json")
    if not os.path.isfile(filepath):
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    dados = data.get("dados", {})
    if not dados:
        return 0

    ultimo_status = dados.get("ultimoStatus", {})
    situacao = ultimo_status.get("situacao")
    condicao = ultimo_status.get("condicaoEleitoral")
    nome_eleitoral = ultimo_status.get("nomeEleitoral")

    atualizados = 0
    with savepoint(cursor, "sp_detdep"):
        cursor.execute("""
            UPDATE camara.deputados_mandatos
            SET situacao = %s,
                condicao_eleitoral = %s
            WHERE deputado_id = %s
              AND (situacao IS DISTINCT FROM %s
                OR condicao_eleitoral IS DISTINCT FROM %s)
        """, (situacao, condicao, deputado_id, situacao, condicao))
        if cursor.rowcount and cursor.rowcount > 0:
            atualizados += cursor.rowcount

        if nome_eleitoral:
            cursor.execute("""
                UPDATE camara.deputados
                SET nome_eleitoral = %s
                WHERE id = %s AND (nome_eleitoral IS NULL OR nome_eleitoral != %s)
            """, (nome_eleitoral, deputado_id, nome_eleitoral))

    if atualizados > 0:
        cursor.execute(
            "SELECT COUNT(*) FROM camara.deputados_mandatos WHERE deputado_id = %s AND condicao_eleitoral IS NOT NULL",
            (deputado_id,),
        )
        db_count = cursor.fetchone()[0]
        if db_count > 0:
            mark_verified("camara_detalhes", str(deputado_id), 1, db_count)

    return atualizados


def _importar_historico_cursor(cursor, deputado_id: int) -> int:
    filepath = os.path.join(DATA_DIR, "camara", "deputados", str(deputado_id), "historico.json")
    if not os.path.isfile(filepath):
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    eventos = data.get("dados", [])
    if not eventos:
        return 0

    cursor.execute("SELECT id, nome_civil FROM camara.deputados")
    nome_civil_map = {row[0]: row[1] for row in cursor.fetchall()}

    inseridos = 0
    for evento in eventos:
        data_hora = evento.get("dataHora")
        if not data_hora:
            continue
        try:
            with savepoint(cursor, "sp_hist"):
                cursor.execute("""
                    INSERT INTO camara.deputados_historico
                        (deputado_id, data_hora, situacao, condicao_eleitoral,
                         descricao_status, sigla_partido, sigla_uf,
                         nome_eleitoral, nome_civil, url_foto, id_legislatura)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (deputado_id, data_hora) DO NOTHING
                """, (
                    deputado_id, data_hora,
                    evento.get("situacao"), evento.get("condicaoEleitoral"),
                    evento.get("descricaoStatus"), evento.get("siglaPartido"),
                    evento.get("siglaUf"), evento.get("nomeEleitoral"),
                    nome_civil_map.get(deputado_id), evento.get("urlFoto"),
                    evento.get("idLegislatura")
                ))
            if cursor.rowcount and cursor.rowcount > 0:
                inseridos += 1
        except Exception as e:
            logging.error("Erro ao inserir historico deputado %d (data=%s): %s", deputado_id, evento.get("dataHora"), e)
            continue

    if inseridos > 0:
        cursor.execute(
            "SELECT COUNT(*) FROM camara.deputados_historico WHERE deputado_id = %s",
            (deputado_id,),
        )
        db_count = cursor.fetchone()[0]
        if len(eventos) == db_count:
            mark_verified("camara_historico", str(deputado_id), len(eventos), db_count)

    return inseridos


def _importar_emendas_cursor(cursor, nome_autor: str, anos: list) -> int:
    nome_sanitizado = remover_acentos(nome_autor).replace(" ", "_").replace("/", "_").upper()
    emendas_dir = os.path.join(DATA_DIR, "portal", "emendas")
    inseridos = 0
    for ano in anos:
        filepath = os.path.join(emendas_dir, f"{nome_sanitizado}_{ano}.json")
        if not os.path.isfile(filepath):
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for emenda in data.get("emendas", []):
            autor = (emenda.get("nomeAutor") or "").strip().upper()
            if remover_acentos(autor) != remover_acentos(nome_autor.upper()):
                continue
            try:
                with savepoint(cursor, "sp_emenda"):
                    cursor.execute("""
                        INSERT INTO portal.emendas
                            (codigo_emenda, ano, tipo_emenda, autor, nome_autor,
                             numero_emenda, localidade_gasto, funcao, subfuncao,
                             valor_empenhado, valor_liquidado, valor_pago,
                             valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (
                        emenda.get("codigoEmenda"), emenda.get("ano"),
                        emenda.get("tipoEmenda"), emenda.get("nomeAutor", ""),
                        emenda.get("nomeAutor", ""), emenda.get("numeroEmenda"),
                        emenda.get("localidadeDoGasto"), emenda.get("funcao"),
                        emenda.get("subfuncao"),
                        float(str(emenda.get("valorEmpenhado", "0")).replace(".", "").replace(",", ".")),
                        float(str(emenda.get("valorLiquidado", "0")).replace(".", "").replace(",", ".")),
                        float(str(emenda.get("valorPago", "0")).replace(".", "").replace(",", ".")),
                        float(str(emenda.get("valorRestoInscrito", "0")).replace(".", "").replace(",", ".")),
                        float(str(emenda.get("valorRestoCancelado", "0")).replace(".", "").replace(",", ".")),
                        float(str(emenda.get("valorRestoPago", "0")).replace(".", "").replace(",", ".")),
                    ))
                if cursor.rowcount and cursor.rowcount > 0:
                    inseridos += 1
            except Exception:
                continue
    return inseridos


# ============================================================
# IMPORTAÇÃO ATÔMICA DE MANDATOS (1 transação = 1 commit)
# ============================================================

def _importar_mandato_camara(dep_data: dict) -> dict:
    dep_id = dep_data["id"]
    id_leg = dep_data.get("idLegislatura")
    if not id_leg:
        raise ValueError(f"idLegislatura ausente para deputado {dep_id}")

    from database import db
    conn = db.get_db_connection()
    try:
        nome = dep_data.get("nome", "").strip()
        partido = dep_data.get("siglaPartido", "")
        uf = dep_data.get("siglaUf", "")
        url_foto = dep_data.get("urlFoto", "")
        email = dep_data.get("email", "")

        with conn.cursor() as cursor:
            ano_inicio = legislatura_anos(id_leg)[0]
            cursor.execute("""
                INSERT INTO camara.legislaturas (id, data_inicio)
                VALUES (%s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (id_leg, f"{ano_inicio}-02-01"))

            detalhes = _buscar_situacao_deputado(dep_id)
            situacao = detalhes["situacao"]
            condicao_eleitoral = detalhes["condicao_eleitoral"]
            nome_eleitoral_api = detalhes.get("nome_eleitoral") or ""
            nome_civil_api = detalhes.get("nome_civil") or nome

            cursor.execute("""
                INSERT INTO camara.deputados (id, nome_civil, nome_eleitoral, email)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    nome_eleitoral = EXCLUDED.nome_eleitoral
            """, (dep_id, nome_civil_api, nome_eleitoral_api, email))

            nome_exibicao = nome_eleitoral_api or nome_civil_api
            mandato_id = f"{dep_id}_{id_leg}"
            cursor.execute("""
                INSERT INTO camara.deputados_mandatos
                    (id, deputado_id, legislatura_id, nome_eleitoral,
                     sigla_partido, sigla_uf, url_foto, email,
                     situacao, condicao_eleitoral)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    sigla_partido = EXCLUDED.sigla_partido,
                    nome_eleitoral = EXCLUDED.nome_eleitoral,
                    sigla_uf = EXCLUDED.sigla_uf,
                    url_foto = EXCLUDED.url_foto,
                    email = EXCLUDED.email,
                    situacao = COALESCE(EXCLUDED.situacao, camara.deputados_mandatos.situacao),
                    condicao_eleitoral = COALESCE(EXCLUDED.condicao_eleitoral, camara.deputados_mandatos.condicao_eleitoral)
            """, (mandato_id, dep_id, id_leg, nome_exibicao,
                  partido, uf, url_foto, email,
                  situacao, condicao_eleitoral))

            despesas = _importar_despesas_cursor(cursor, dep_id, id_leg, mandato_id)
            detalhes_ok = _importar_detalhes_cursor(cursor, dep_id)
            historico = _importar_historico_cursor(cursor, dep_id)
            emendas = 0
            nome_emendas = nome_eleitoral_api or nome_civil_api
            if nome_emendas:
                anos_leg = legislatura_anos_lista(id_leg)
                emendas = _importar_emendas_cursor(cursor, nome_emendas, anos_leg)

        conn.commit()
        return {
            "deputado_id": dep_id,
            "legislatura_id": id_leg,
            "nome": nome_exibicao,
            "despesas": despesas,
            "detalhes": detalhes_ok,
            "historico": historico,
            "emendas": emendas,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        db.release_db_connection(conn)


def _importar_mandato_senado(sen_data: dict, expenses_cache: dict) -> dict:
    ident = sen_data.get("IdentificacaoParlamentar", {})
    id_leg = sen_data.get("idLegislatura")

    codigo = int(ident.get("CodigoParlamentar", 0))
    if not codigo:
        raise ValueError("CodigoParlamentar ausente no registro do senado")
    if not id_leg:
        raise ValueError(f"idLegislatura ausente para senador {codigo}")

    mandato_data = _extrair_mandato_senado(sen_data, id_leg)

    from database import db
    conn = db.get_db_connection()
    try:
        nome_parlamentar = ident.get("NomeParlamentar", "").strip()
        nome_completo = ident.get("NomeCompletoParlamentar", "").strip()
        sexo = ident.get("SexoParlamentar", "")
        sigla_partido = ident.get("SiglaPartidoParlamentar", "")
        uf = ident.get("UfParlamentar", "")
        url_foto = ident.get("UrlFotoParlamentar", "")
        url_pagina = ident.get("UrlPaginaParlamentar", "")
        email = ident.get("EmailParlamentar", "")

        with conn.cursor() as cursor:
            prim_leg = mandato_data.get("PrimeiraLegislaturaDoMandato", {})
            seg_leg = mandato_data.get("SegundaLegislaturaDoMandato")

            for leg_info in [prim_leg, seg_leg] if seg_leg else [prim_leg]:
                if leg_info:
                    num_leg = leg_info.get("NumeroLegislatura")
                    data_inicio = leg_info.get("DataInicio")
                    data_fim = leg_info.get("DataFim")
                    if num_leg:
                        cursor.execute("""
                            INSERT INTO senado.legislatura (numero, data_inicio, data_fim)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (numero) DO NOTHING
                        """, (num_leg, data_inicio, data_fim))

            cursor.execute("""
                INSERT INTO senado.parlamentar
                    (codigo, nome_parlamentar, nome_completo, sexo,
                     sigla_partido, uf, url_foto, url_pagina, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO NOTHING
            """, (codigo, nome_parlamentar, nome_completo, sexo,
                  sigla_partido, uf, url_foto, url_pagina, email))

            codigo_mandato = mandato_data.get("CodigoMandato", "")
            if codigo_mandato:
                uf_mandato = mandato_data.get("UfParlamentar", uf)
                descricao = mandato_data.get("DescricaoParticipacao", "")
                primeira_leg = prim_leg.get("NumeroLegislatura", "") if prim_leg else ""
                segunda_leg = seg_leg.get("NumeroLegislatura", "") if seg_leg else ""

                if primeira_leg and primeira_leg.strip():
                    if segunda_leg is None:
                        segunda_leg = ""
                    cursor.execute("""
                        INSERT INTO senado.mandato
                            (codigo_mandato, codigo_parlamentar, uf,
                             descricao_participacao,
                             primeira_legislatura, segunda_legislatura)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (codigo_mandato, codigo_parlamentar) DO NOTHING
                    """, (codigo_mandato, codigo, uf_mandato,
                          descricao, primeira_leg, segunda_leg))

            despesas = 0
            anos = legislatura_anos_lista(id_leg)
            for ano in anos:
                sen_map = expenses_cache.get(ano, {})
                for despesa in sen_map.get(codigo, []):
                    try:
                        id_despesa_api = despesa.get("id")
                        if not id_despesa_api:
                            continue
                        with savepoint(cursor, "sp_senado_despesa"):
                            cursor.execute("""
                                INSERT INTO senado.despesa_ceaps
                                    (id_despesa, ano, mes, cod_senador, nome_senador, tipo_despesa,
                                     cpf_cnpj, fornecedor, documento, data_despesa,
                                     detalhamento, valor_reembolsado, tipo_documento)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id_despesa)
                                DO NOTHING
                            """, (
                                id_despesa_api,
                                despesa.get("ano"), despesa.get("mes"), codigo,
                                despesa.get("nomeSenador", ""),
                                despesa.get("tipoDespesa", ""), despesa.get("cpfCnpj"),
                                despesa.get("fornecedor", ""), despesa.get("documento"),
                                despesa.get("data"),
                                despesa.get("detalhamento"), despesa.get("valorReembolsado", 0),
                                despesa.get("tipoDocumento")
                            ))
                        if cursor.rowcount and cursor.rowcount > 0:
                            despesas += 1
                    except Exception:
                        continue

            emendas = 0
            if nome_parlamentar:
                emendas = _importar_emendas_cursor(cursor, nome_parlamentar, anos)

        conn.commit()
        return {
            "codigo_parlamentar": codigo,
            "legislatura_id": id_leg,
            "nome": nome_parlamentar,
            "despesas": despesas,
            "emendas": emendas,
        }
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        db.release_db_connection(conn)


def _extrair_mandato_senado(sen_data: dict, id_leg: int) -> dict:
    mandatos_wrapper = sen_data.get("Mandatos", {})
    mandato_list = mandatos_wrapper.get("Mandato", [])
    if isinstance(mandato_list, dict):
        mandato_list = [mandato_list]

    for m in mandato_list:
        prim = m.get("PrimeiraLegislaturaDoMandato", {})
        seg = m.get("SegundaLegislaturaDoMandato")
        if prim and str(prim.get("NumeroLegislatura")) == str(id_leg):
            return m
        if seg and str(seg.get("NumeroLegislatura")) == str(id_leg):
            return m

    if mandato_list:
        return mandato_list[0]

    return {}


# ============================================================
# DADOS COMPLEMENTARES (após todas as legislaturas)
# ============================================================

def _importar_dados_complementares(conn) -> bool:
    imported = False
    try:
        if import_proposicoes_camara(conn):
            imported = True
    except Exception as e:
        logging.error("Erro em import_proposicoes_camara: %s", e)
    try:
        if import_votacoes_camara(conn):
            imported = True
    except Exception as e:
        logging.error("Erro em import_votacoes_camara: %s", e)
    try:
        if import_autores_proposicoes(conn):
            imported = True
    except Exception as e:
        logging.error("Erro em import_autores_proposicoes: %s", e)
    try:
        if import_processos_senado(conn):
            imported = True
    except Exception as e:
        logging.error("Erro em import_processos_senado: %s", e)
    if not imported:
        logging.warning("Nenhum dado complementar foi importado.")
    return imported


# ============================================================
# INICIALIZAÇÃO (importação do cache, sem API calls)
# ============================================================

CAMARA_WORKERS = 6
SENADO_WORKERS = 2

LEGISLATURAS = [57, 56, 55, 54, 53, 52, 51, 50, 49, 48]
SENADO_LEGISLATURAS = [57, 56, 55, 54, 53, 52, 51, 50, 49, 48]


def carregar_cache(casa: str, leg: int) -> list:
    if casa == "camara":
        filepath = os.path.join(DATA_DIR, "camara", "deputados", f"legislatura_{leg}.json")
    else:
        filepath = os.path.join(DATA_DIR, "senado", "senadores", f"legislatura_{leg}.json")

    if not os.path.isfile(filepath):
        logging.info("Cache %s legislatura %d ausente. Scrapers resolverao.", casa, leg)
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if casa == "camara":
        return data.get("dados", [])

    parlamentares = []
    for key in data:
        if isinstance(data[key], dict):
            items = data[key].get("Parlamentares", {}).get("Parlamentar", [])
            if items:
                parlamentares = items
                break
    for par in parlamentares:
        par["idLegislatura"] = leg
    return parlamentares


def _carregar_expenses_cache(leg: int) -> dict:
    cache = {}
    anos = legislatura_anos_lista(leg)
    for ano in anos:
        filepath = os.path.join(DATA_DIR, "senado", "despesas", f"{ano}.json")
        if os.path.isfile(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            despesas_lista = data.get("despesas", []) if isinstance(data, dict) else data if isinstance(data, list) else []
            sen_map = {}
            for d in despesas_lista:
                cod = d.get("codSenador")
                if cod:
                    cod = int(cod)
                    if cod not in sen_map:
                        sen_map[cod] = []
                    sen_map[cod].append(d)
            cache[ano] = sen_map
    return cache


def _salvar_falhos(falhos: list):
    if not falhos:
        return
    failed_dir = os.path.join(DATA_DIR, "failed")
    os.makedirs(failed_dir, exist_ok=True)
    filepath = os.path.join(failed_dir, "mandatos_falhos_import.json")
    existing = []
    if os.path.isfile(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing = json.load(f).get("falhos", [])
        except Exception:
            pass
    all_falhos = existing + falhos
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"falhos": all_falhos, "total": len(all_falhos)}, f, ensure_ascii=False, indent=2)
    logging.warning("%d mandato(s) falharam na importacao.", len(falhos))


def importar_em_paralelo(deputados: list, senadores: list, leg: int) -> list:
    expenses_cache = _carregar_expenses_cache(leg)
    falhos = []
    futures = {}
    falhos_lock = threading.Lock()

    def _add_falho(f):
        with falhos_lock:
            falhos.append(f)

    for dep in deputados:
        dep_id = dep.get("id")
        if not dep_id:
            continue
        dep["idLegislatura"] = leg

    with ThreadPoolExecutor(max_workers=CAMARA_WORKERS + SENADO_WORKERS) as executor:
        for dep in deputados:
            dep_id = dep.get("id")
            if not dep_id:
                continue
            fut = executor.submit(_importar_mandato_camara, dep)
            futures[fut] = ("camara", dep)

        for sen in senadores:
            codigo = int(sen.get("IdentificacaoParlamentar", {}).get("CodigoParlamentar", 0))
            if not codigo:
                continue
            sen["idLegislatura"] = leg
            fut = executor.submit(_importar_mandato_senado, sen, expenses_cache)
            futures[fut] = ("senado", sen)

        total = len(futures)
        logging.info("Importando %d mandatos da legislatura %d em paralelo...", total, leg)

        for fut in as_completed(futures):
            tipo, item = futures[fut]
            try:
                result = fut.result()
                if result:
                    logging.debug("OK %s legislatura %d", tipo, leg)
            except Exception as e:
                if tipo == "camara":
                    _add_falho({"tipo": "camara", "deputado_id": item.get("id", 0), "legislatura_id": leg, "nome": item.get("nome", ""), "erro": str(e)[:500]})
                    logging.error("FALHA deputado %d legislatura %d: %s", item.get("id", 0), leg, e)
                else:
                    codigo = int(item.get("IdentificacaoParlamentar", {}).get("CodigoParlamentar", 0))
                    _add_falho({"tipo": "senado", "codigo_parlamentar": codigo, "legislatura_id": leg, "nome": item.get("IdentificacaoParlamentar", {}).get("NomeParlamentar", ""), "erro": str(e)[:500]})
                    logging.error("FALHA senador %d legislatura %d: %s", codigo, leg, e)

    return falhos


def _agregar_arquivos_legislaturas():
    camara_dir = os.path.join(DATA_DIR, "camara", "deputados")
    todos = []
    for leg in LEGISLATURAS:
        fpath = os.path.join(camara_dir, f"legislatura_{leg}.json")
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for dep in data.get("dados", []):
                dep["idLegislatura"] = leg
                todos.append(dep)
    if todos:
        save_json({"dados": todos}, os.path.join(DATA_DIR, "camara", "deputados.json"))
        logging.info("deputados.json agregado: %d registros.", len(todos))

    senado_dir = os.path.join(DATA_DIR, "senado", "senadores")
    todos_sen = []
    codigos = set()
    for leg in SENADO_LEGISLATURAS:
        fpath = os.path.join(senado_dir, f"legislatura_{leg}.json")
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            parlamentares = []
            for key in data:
                if isinstance(data[key], dict):
                    items = data[key].get("Parlamentares", {}).get("Parlamentar", [])
                    if items:
                        parlamentares = items
                        break
            for par in parlamentares:
                ident = par.get("IdentificacaoParlamentar", {}).get("CodigoParlamentar", "")
                if ident:
                    codigos.add(str(ident))
                par["idLegislatura"] = leg
                todos_sen.append(par)
    if todos_sen:
        resultado = {"ListaParlamentarEmExercicio": {"Parlamentares": {"Parlamentar": todos_sen}}}
        save_json(resultado, os.path.join(DATA_DIR, "senado", "senadores.json"))
        logging.info("senadores.json agregado: %d registros de %d senadores.", len(todos_sen), len(codigos))


def inicializar_banco():
    logging.info("=== IMPORTACAO INICIAL INICIADA ===")
    for leg in LEGISLATURAS:
        logging.info("--- Legislatura %d ---", leg)
        deputados = carregar_cache("camara", leg)
        senadores = carregar_cache("senado", leg)
        if not deputados and not senadores:
            logging.info("Sem cache para legislatura %d. Scrapers resolverao.", leg)
            break
        logging.info("%d deputados, %d senadores.", len(deputados), len(senadores))
        falhos = importar_em_paralelo(deputados, senadores, leg)
        if falhos:
            _salvar_falhos(falhos)

    logging.info("Agregando arquivos de todas as legislaturas...")
    try:
        _agregar_arquivos_legislaturas()
    except Exception as e:
        logging.error("Falha ao agregar arquivos: %s", e)

    conn = None
    try:
        conn = db.get_db_connection()
        if conn:
            logging.info("Importando dados complementares...")
            _importar_dados_complementares(conn)
    except Exception as e:
        logging.error("Falha ao importar dados complementares: %s", e)
    finally:
        if conn:
            try:
                db.release_db_connection(conn)
            except Exception:
                pass

    logging.info("=== IMPORTACAO INICIAL CONCLUIDA ===")
# ============================================================

def _inserir_despesa(cursor, despesa: dict, mandato_id: str) -> int:
    """Insere uma única despesa no banco. Retorna 1 se inseriu, 0 se conflito."""
    valor_documento = despesa.get("valorDocumento")
    if valor_documento is not None and not isinstance(valor_documento, (int, float)):
        try:
            valor_documento = float(str(valor_documento).replace(",", "."))
        except (ValueError, TypeError):
            valor_documento = 0

    valor_liquido = despesa.get("valorLiquido")
    if valor_liquido is not None and not isinstance(valor_liquido, (int, float)):
        try:
            valor_liquido = float(str(valor_liquido).replace(",", "."))
        except (ValueError, TypeError):
            valor_liquido = 0

    valor_glosa = despesa.get("valorGlosa")
    if valor_glosa is not None and not isinstance(valor_glosa, (int, float)):
        try:
            valor_glosa = float(str(valor_glosa).replace(",", "."))
        except (ValueError, TypeError):
            valor_glosa = 0

    with savepoint(cursor, "sp_camara_despesa"):
        cursor.execute("""
            INSERT INTO camara.deputados_despesas
                (ano, mes, tipo_despesa, cod_documento, tipo_documento,
                 cod_tipo_documento, data_documento, num_documento,
                 valor_documento, url_documento, nome_fornecedor,
                 cnpj_cpf_fornecedor, valor_liquido, valor_glosa,
                 num_ressarcimento, cod_lote, parcela, mandato_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cod_documento, num_documento, data_documento, valor_documento, nome_fornecedor) 
            DO NOTHING
        """, (
            despesa.get("ano"),
            despesa.get("mes"),
            despesa.get("tipoDespesa", ""),
            despesa.get("codDocumento"),
            despesa.get("tipoDocumento"),
            despesa.get("codTipoDocumento"),
            despesa.get("dataDocumento"),
            despesa.get("numDocumento"),
            valor_documento,
            despesa.get("urlDocumento"),
            despesa.get("nomeFornecedor", ""),
            despesa.get("cnpjCpfFornecedor"),
            valor_liquido,
            valor_glosa,
            despesa.get("numRessarcimento"),
            despesa.get("codLote", 0),
            despesa.get("parcela", 0),
            mandato_id
        ))
    return 1 if cursor.rowcount > 0 else 0


def import_despesas_camara(conn, deputado_id: int = None) -> Optional[bool]:
    """
    Lê os JSONs de despesas em backend/data/camara/deputados/{deputado_id}/despesas/
    e insere/atualiza os dados na tabela camara.deputados_despesas.
    
    Se deputado_id for fornecido, processa APENAS aquele deputado (importação incremental).
    Caso contrário, processa todos os deputados (importação completa).
    
    Estrutura esperada do JSON da API:
    {
        "dados": [
            {
                "ano": 2023,
                "mes": 1,
                "tipoDespesa": "PASSAGEM AÉREA",
                "codDocumento": 12345,
                "tipoDocumento": "Nota Fiscal",
                "codTipoDocumento": 1,
                "dataDocumento": "2023-01-15",
                "numDocumento": "123",
                "valorDocumento": 1500.00,
                "urlDocumento": "https://...",
                "nomeFornecedor": "LATAM",
                "cnpjCpfFornecedor": "12345678000199",
                "valorLiquido": 1500.00,
                "valorGlosa": 0.00,
                "numRessarcimento": null,
                "codLote": 1,
                "parcela": 0
            }
        ],
        "links": [...]
    }
    """
    global _despesas_camara_importadas
    
    with _import_lock:
        despesas_dir = os.path.join(DATA_DIR, "camara", "deputados")
        if not os.path.isdir(despesas_dir):
            logging.warning(f"Diretório de despesas não encontrado: {despesas_dir}")
            return None
        
        # Carrega o JSON de deputados para referência cruzada
        deputados_filepath = os.path.join(DATA_DIR, "camara", "deputados.json")
        deputados_por_id = {}
        if os.path.isfile(deputados_filepath):
            with open(deputados_filepath, "r", encoding="utf-8") as f:
                dep_data = json.load(f)
            for dep in dep_data.get("dados", []):
                deputados_por_id[dep["id"]] = dep
        
        total_inseridos = 0
        erro_mandato = False
        
        # Determina quais deputados processar
        if deputado_id is not None:
            # Modo incremental: processa apenas um deputado específico
            if deputado_id in _despesas_camara_importadas:
                return None  # Já foi importado anteriormente nesta sessão
            
            dep_ids = [(str(deputado_id), deputado_id)]
        else:
            # Modo completo: processa todos os deputados
            dep_ids = []
            for dep_id_str in os.listdir(despesas_dir):
                dep_dir = os.path.join(despesas_dir, dep_id_str, "despesas")
                if os.path.isdir(dep_dir):
                    dep_ids.append((dep_id_str, int(dep_id_str)))
        
        for dep_id_str, dep_id in dep_ids:
            dep_dir = os.path.join(despesas_dir, dep_id_str, "despesas")
            if not os.path.isdir(dep_dir):
                continue
            
            # Pula se já foi importado nesta sessão
            if dep_id in _despesas_camara_importadas:
                continue
            
            inseridos_dep = 0
            
            try:
                with conn.cursor() as cursor:
                    # Pré-busca todos os mandatos do deputado com seu período (ano início)
                    cursor.execute("""
                        SELECT m.id, m.legislatura_id, 
                               EXTRACT(YEAR FROM l.data_inicio)::integer as ano_inicio
                        FROM camara.deputados_mandatos m
                        JOIN camara.legislaturas l ON m.legislatura_id = l.id
                        WHERE m.deputado_id = %s
                    """, (dep_id,))
                    mandatos_info = cursor.fetchall()
                    
                    if not mandatos_info:
                        # Tenta cadastrar o deputado dinamicamente a partir do JSON já carregado
                        dep_info = deputados_por_id.get(dep_id)
                        if dep_info:
                            nome = dep_info.get("nome", "").strip()
                            partido = dep_info.get("siglaPartido", "")
                            uf = dep_info.get("siglaUf", "")
                            url_foto = dep_info.get("urlFoto", "")
                            email = dep_info.get("email", "")
                            id_legislatura = dep_info.get("idLegislatura")
                            
                            if id_legislatura:
                                # Fórmula: ano_início = 4 × L + 1795
                                ano_inicio = legislatura_anos(id_legislatura)[0]
                                cursor.execute("""
                                    INSERT INTO camara.legislaturas (id, data_inicio)
                                    VALUES (%s, %s)
                                    ON CONFLICT (id) DO NOTHING
                                """, (id_legislatura, f"{ano_inicio}-02-01"))
                            
                            # Busca situação, condição eleitoral e nomes na API (com cache)
                            detalhes = _buscar_situacao_deputado(dep_id)
                            situacao = detalhes["situacao"]
                            condicao_eleitoral = detalhes["condicao_eleitoral"]
                            nome_eleitoral_api = detalhes.get("nome_eleitoral") or ""
                            nome_civil_api = detalhes.get("nome_civil") or nome

                            cursor.execute("""
                                INSERT INTO camara.deputados (id, nome_civil, nome_eleitoral, email)
                                VALUES (%s, %s, %s, %s)
                                ON CONFLICT (id) DO UPDATE SET
                                    nome_eleitoral = EXCLUDED.nome_eleitoral
                            """, (dep_id, nome_civil_api, nome_eleitoral_api, email))

                            nome_exibicao = nome_eleitoral_api or nome_civil_api

                            if id_legislatura:
                                mandato_id = f"{dep_id}_{id_legislatura}"
                                ano_inicio = legislatura_anos(id_legislatura)[0]
                                cursor.execute("""
                                    INSERT INTO camara.deputados_mandatos
                                        (id, deputado_id, legislatura_id, nome_eleitoral,
                                         sigla_partido, sigla_uf, url_foto, email,
                                         situacao, condicao_eleitoral)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (id) DO NOTHING
                                """, (mandato_id, dep_id, id_legislatura, nome_exibicao,
                                      partido, uf, url_foto, email,
                                      situacao, condicao_eleitoral))
                                conn.commit()
                                logging.info(f"Deputado {dep_id} ({nome_exibicao}) cadastrado dinamicamente a partir do JSON.")
                                mandatos_info = [(mandato_id, id_legislatura, ano_inicio)]
                            else:
                                logging.warning(f"Deputado {dep_id} encontrado no JSON mas sem idLegislatura. Pulando.")
                                continue
                        else:
                            logging.warning(f"Mandato não encontrado para deputado {dep_id} e deputado não consta no JSON. Pulando.")
                            erro_mandato = True
                            continue
                    
                    # Mapeia legislatura_id -> mandato_id
                    mandato_por_legislatura = {}
                    mandato_por_ano = {}
                    for m_id, leg_id, ano_ini in mandatos_info:
                        mandato_por_legislatura[leg_id] = m_id
                        for y in range(ano_ini, ano_ini + 4):
                            if y not in mandato_por_ano:
                                mandato_por_ano[y] = m_id
                    
                    mandato_fallback = mandatos_info[-1][0]

                    # Determina estrutura: novo formato (subdir por legislatura) ou antigo (arquivos diretos)
                    try:
                        dir_contents = os.listdir(dep_dir)
                    except OSError:
                        dir_contents = []
                    
                    leg_subdirs = [
                        d for d in dir_contents
                        if os.path.isdir(os.path.join(dep_dir, d)) and d.lstrip('-').isdigit()
                    ]
                    
                    if leg_subdirs:
                        # === NOVO FORMATO: deputados/{dep_id}/despesas/{legislatura}/{ano}.json ===
                        for leg_str in sorted(leg_subdirs):
                            leg_id = int(leg_str)
                            leg_dir = os.path.join(dep_dir, leg_str)
                            mandato_id = mandato_por_legislatura.get(leg_id, mandato_fallback)
                            
                            json_count_leg = 0
                            for fname in sorted(os.listdir(leg_dir)):
                                if not fname.endswith(".json"):
                                    continue
                                filepath = os.path.join(leg_dir, fname)
                                with open(filepath, "r", encoding="utf-8") as f:
                                    data = json.load(f)
                                dados = data.get("dados", [])
                                if not dados:
                                    continue
                                json_count_leg += len(dados)
                                for despesa in dados:
                                    inseridos_dep += _inserir_despesa(cursor, despesa, mandato_id)
                                conn.commit()
                            
                            cursor.execute(
                                "SELECT COUNT(*) FROM camara.deputados_despesas dd "
                                "JOIN camara.deputados_mandatos dm ON dm.id = dd.mandato_id "
                                "WHERE dm.deputado_id = %s AND dm.legislatura_id = %s",
                                (dep_id, leg_id),
                            )
                            db_count_leg = cursor.fetchone()[0]
                            if json_count_leg > 0 and json_count_leg == db_count_leg:
                                mark_verified("camara_despesas", f"{dep_id}_{leg_id}", json_count_leg, db_count_leg)
                    else:
                        # Sem subdirs de legislatura — estrutura não suportada, pula
                        continue
                    
                    total_inseridos += inseridos_dep
                    if inseridos_dep > 0:
                        logging.info(f"Deputado {dep_id}: {inseridos_dep} despesas importadas.")
                    _despesas_camara_importadas.add(dep_id)
            except Exception as e:
                logging.error(f"Erro ao processar deputado {dep_id}: {e}")
                conn.rollback()
                continue
        
        if erro_mandato:
            return False
        if total_inseridos > 0 or deputado_id is None:
            logging.info(f"Importação de despesas da Câmara concluída. {total_inseridos} registros inseridos.")
        return True if total_inseridos > 0 else None



# ============================================================
# IMPORTAÇÃO DE PROCESSOS LEGISLATIVOS - SENADO
# ============================================================

def import_processos_senado(conn, ano: int = None) -> bool:
    """
    Lê os JSONs de processos legislativos do Senado em backend/data/senado/processos/
    e insere/atualiza os dados na tabela senado.materia.
    
    Se ano for fornecido, processa APENAS aquele ano (importação incremental).
    Caso contrário, processa todos os anos disponíveis.
    
    A listagem da API /processo retorna dados básicos. Os detalhes completos
    (incluindo autoriaIniciativa com codigoParlamentar) são buscados do endpoint
    /processo/{id} e salvos em backend/data/senado/processos/{id}.json.
    
    Estrutura da listagem (/processo?ano=...):
    [
        {
            "id": 8983465,
            "codigoMateria": 172518,
            "identificacao": "PL 199/2026",
            "ementa": "...",
            "dataApresentacao": "2025-12-23",
            "dataSituacaoAtual": "2026-02-03",
            "dataUltimaAtualizacao": "2026-02-11T11:30:15.986",
            "situacaoAtual": "AGUARDANDO DESPACHO",
            "tramitando": "Sim",
            "urlDocumento": "https://...",
            "objetivo": "Revisora",
            "tipoConteudo": "Norma Geral",
            "tipoDocumento": "Projeto de Lei Ordinária",
            "casaIdentificadora": "SF",
            "enteIdentificador": "SF",
            "autoria": "Câmara dos Deputados"
        }
    ]
    
    Estrutura do detalhe (/processo/{id}):
    {
        "id": 8983465,
        "codigoMateria": 172518,
        "identificacao": "PL 199/2026",
        "sigla": "PL",
        "descricaoSigla": "Projeto de Lei",
        "numero": "199",
        "ano": 2026,
        "objetivo": "Revisora",
        "casaIdentificadora": "SF",
        "conteudo": {
            "ementa": "...",
            "tipo": "Norma Geral"
        },
        "documento": {
            "dataApresentacao": "2025-12-23",
            "indexacao": "...",
            "url": "https://...",
            "autoria": [
                {
                    "autor": "Câmara dos Deputados",
                    "siglaTipo": "CAMARA",
                    "descricaoTipo": "CAMARA",
                    "ordem": 1
                }
            ]
        },
        "tramitando": "Sim",
        "situacaoAtual": "AGUARDANDO DESPACHO",
        "dataSituacaoAtual": "2026-02-03",
        "autoriaIniciativa": [
            {
                "autor": "Ricardo Izar",
                "sexo": "M",
                "siglaTipo": "DEPUTADO",
                "descricaoTipo": "DEPUTADO",
                "ordem": 1,
                "codigoParlamentar": 5375,
                "siglaPartido": "PP",
                "partido": "Progressistas",
                "siglaCargo": "DEPUTADO",
                "cargo": "Deputado Federal",
                "idEnte": 2,
                "siglaEnte": "CD",
                "casaEnte": "CD",
                "ente": "Câmara dos Deputados"
            }
        ]
    }
    """
    processos_dir = os.path.join(DATA_DIR, "senado", "processos")
    if not os.path.isdir(processos_dir):
        logging.warning(f"Diretório de processos não encontrado: {processos_dir}")
        return False
    
    ano_dir = os.path.join(processos_dir, "ano")
    
    # Determina quais arquivos processar
    if ano is not None:
        arquivos = [f"{ano}.json"]
    else:
        arquivos = []
        if os.path.isdir(ano_dir):
            arquivos = sorted([f for f in os.listdir(ano_dir) if f.endswith(".json")])
    
    if not arquivos:
        return False
    
    total_inseridos = 0
    total_atualizados = 0
    
    with conn.cursor() as cursor:
        for fname in arquivos:
            filepath = os.path.join(ano_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # A API retorna uma lista diretamente
            if not isinstance(data, list):
                logging.warning(f"Formato inesperado em {fname}: tipo {type(data).__name__}")
                continue
            
            logging.info(f"Importando {len(data)} processos de {fname}...")
            
            for proc in data:
                cursor.execute("SAVEPOINT sp_proc")
                try:
                    codigo_materia = proc.get("codigoMateria")
                    if not codigo_materia:
                        cursor.execute("RELEASE SAVEPOINT sp_proc")
                        continue
                    
                    # Extrai sigla e número da identificacao (ex: "PL 199/2026")
                    identificacao = proc.get("identificacao", "")
                    sigla = ""
                    numero = ""
                    if identificacao:
                        partes = identificacao.split(" ")
                        if len(partes) >= 2:
                            sigla = partes[0]
                            # Pega o número antes da barra
                            num_parts = partes[1].split("/")
                            if num_parts:
                                numero = num_parts[0]
                    
                    # Converte dataApresentacao para DATE
                    data_apresentacao = proc.get("dataApresentacao")
                    if data_apresentacao and len(data_apresentacao) >= 10:
                        data_apresentacao = data_apresentacao[:10]
                    
                    # Converte dataSituacaoAtual para DATE
                    data_situacao = proc.get("dataSituacaoAtual")
                    if data_situacao and len(data_situacao) >= 10:
                        data_situacao = data_situacao[:10]
                    
                    # Converte dataUltimaAtualizacao para TIMESTAMP
                    data_ult_atualizacao = proc.get("dataUltimaAtualizacao")
                    if data_ult_atualizacao and len(data_ult_atualizacao) >= 19:
                        data_ult_atualizacao = data_ult_atualizacao[:19].replace("T", " ")
                    
                    # Converte tramitando para booleano
                    tramitando = proc.get("tramitando", "Não") == "Sim"
                    
                    # Extrai ano da identificacao ou do campo ano
                    ano_proc = proc.get("ano")
                    if not ano_proc and identificacao and "/" in identificacao:
                        try:
                            ano_proc = int(identificacao.split("/")[-1])
                        except (ValueError, IndexError):
                            ano_proc = None
                    
                    # Tipo de documento (ex: "Projeto de Lei Ordinária")
                    tipo_documento = proc.get("tipoDocumento", "")
                    
                    cursor.execute("""
                        INSERT INTO senado.materia
                            (codigo, identificacao_processo, sigla, numero, ano, ementa, data,
                             id_processo, situacao_atual, data_situacao_atual, tramitando,
                             url_documento, objetivo, tipo_conteudo, casa_identificadora,
                             ente_identificador, data_ultima_atualizacao,
                             descricao_identificacao)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (codigo) DO UPDATE SET
                            identificacao_processo = EXCLUDED.identificacao_processo,
                            sigla = EXCLUDED.sigla,
                            numero = EXCLUDED.numero,
                            ano = EXCLUDED.ano,
                            ementa = EXCLUDED.ementa,
                            data = EXCLUDED.data,
                            id_processo = EXCLUDED.id_processo,
                            situacao_atual = EXCLUDED.situacao_atual,
                            data_situacao_atual = EXCLUDED.data_situacao_atual,
                            tramitando = EXCLUDED.tramitando,
                            url_documento = EXCLUDED.url_documento,
                            objetivo = EXCLUDED.objetivo,
                            tipo_conteudo = EXCLUDED.tipo_conteudo,
                            casa_identificadora = EXCLUDED.casa_identificadora,
                            ente_identificador = EXCLUDED.ente_identificador,
                            data_ultima_atualizacao = EXCLUDED.data_ultima_atualizacao,
                            descricao_identificacao = EXCLUDED.descricao_identificacao
                    """, (
                        codigo_materia,
                        identificacao,
                        sigla,
                        numero,
                        ano_proc,
                        proc.get("ementa"),
                        data_apresentacao,
                        proc.get("id"),
                        proc.get("situacaoAtual"),
                        data_situacao,
                        tramitando,
                        proc.get("urlDocumento"),
                        proc.get("objetivo"),
                        proc.get("tipoConteudo"),
                        proc.get("casaIdentificadora"),
                        proc.get("enteIdentificador"),
                        data_ult_atualizacao,
                        tipo_documento
                    ))
                    if cursor.rowcount > 0:
                        if cursor.rowcount == 1:
                            total_inseridos += 1
                        else:
                            total_atualizados += 1
                    
                    # --- Processa detalhes se disponíveis ---
                    detalhe_filepath = os.path.join(processos_dir, f"{proc.get('id')}.json")
                    
                    if os.path.isfile(detalhe_filepath):
                        with open(detalhe_filepath, "r", encoding="utf-8") as df:
                            detalhe = json.load(df)
                        
                        if detalhe:
                            # Atualiza campos adicionais do detalhe
                            sigla_detalhe = detalhe.get("sigla", sigla)
                            numero_detalhe = detalhe.get("numero", numero)
                            ano_detalhe = detalhe.get("ano", ano_proc)
                            indexacao = detalhe.get("documento", {}).get("indexacao", "")
                            
                            cursor.execute("""
                                UPDATE senado.materia
                                SET sigla = %s,
                                    numero = %s,
                                    ano = %s,
                                    indexacao = %s
                                WHERE codigo = %s
                                  AND (sigla IS DISTINCT FROM %s
                                    OR numero IS DISTINCT FROM %s
                                    OR ano IS DISTINCT FROM %s
                                    OR indexacao IS DISTINCT FROM %s)
                            """, (sigla_detalhe, numero_detalhe, ano_detalhe,
                                  indexacao, codigo_materia,
                                  sigla_detalhe, numero_detalhe, ano_detalhe,
                                  indexacao))
                            
                            # Processa autoriaIniciativa (autores com codigoParlamentar)
                            autoria_iniciativa = detalhe.get("autoriaIniciativa", [])
                            if isinstance(autoria_iniciativa, list):
                                for autor in autoria_iniciativa:
                                    codigo_parlamentar = autor.get("codigoParlamentar")
                                    if codigo_parlamentar:
                                        # Verifica se o parlamentar existe no banco
                                        cursor.execute("""
                                            SELECT 1 FROM senado.parlamentar WHERE codigo = %s
                                        """, (codigo_parlamentar,))
                                        if cursor.fetchone():
                                            # Insere autoria
                                            cursor.execute("""
                                                INSERT INTO senado.autoria
                                                    (codigo_parlamentar, codigo_materia, autor_principal)
                                                VALUES (%s, %s, %s)
                                                ON CONFLICT (codigo_parlamentar, codigo_materia) DO NOTHING
                                            """, (codigo_parlamentar, codigo_materia, True))
                                        else:
                                            # Tenta cadastrar o parlamentar via API
                                            logging.info(f"Parlamentar {codigo_parlamentar} não encontrado. Buscando na API...")
                                            _buscar_e_inserir_senador_api(cursor, codigo_parlamentar)
                                            cursor.execute("RELEASE SAVEPOINT sp_proc")
                                            conn.commit()
                                            
                                            # Tenta inserir autoria novamente
                                            cursor.execute("""
                                                INSERT INTO senado.autoria
                                                    (codigo_parlamentar, codigo_materia, autor_principal)
                                                VALUES (%s, %s, %s)
                                                ON CONFLICT (codigo_parlamentar, codigo_materia) DO NOTHING
                                            """, (codigo_parlamentar, codigo_materia, True))
                                    else:
                                        # Autor sem código (ex: "Câmara dos Deputados")
                                        # Salva como autor_texto
                                        nome_autor = autor.get("autor", "")
                                        sigla_partido = autor.get("siglaPartido", "")
                                        uf_autor = autor.get("siglaEnte", "")
                                        if nome_autor:
                                            cursor.execute("""
                                                INSERT INTO senado.autoria
                                                    (codigo_materia, autor_principal, autor_texto,
                                                     sigla_partido_autor, uf_autor)
                                                VALUES (%s, %s, %s, %s, %s)
                                                ON CONFLICT (codigo_parlamentar, codigo_materia) DO NOTHING
                                            """, (codigo_materia, True, nome_autor,
                                                  sigla_partido, uf_autor))
                            
                            # Processa autoria do documento (fallback)
                            documento_autoria = detalhe.get("documento", {}).get("autoria", [])
                            if isinstance(documento_autoria, list):
                                for autor_doc in documento_autoria:
                                    nome_autor = autor_doc.get("autor", "")
                                    if nome_autor and not autoria_iniciativa:
                                        # Só insere se não tiver autoriaIniciativa
                                        cursor.execute("""
                                            INSERT INTO senado.autoria
                                                (codigo_materia, autor_principal, autor_texto)
                                            VALUES (%s, %s, %s)
                                            ON CONFLICT (codigo_parlamentar, codigo_materia) DO NOTHING
                                        """, (codigo_materia, True, nome_autor))
                    
                    cursor.execute("RELEASE SAVEPOINT sp_proc")
                except Exception as e:
                    logging.error(f"Erro ao importar processo (codigoMateria={proc.get('codigoMateria')}): {e}")
                    try:
                        cursor.execute("ROLLBACK TO SAVEPOINT sp_proc")
                    except Exception:
                        pass
                    continue
            
            conn.commit()
            logging.info(f"  -> {fname}: {total_inseridos} inseridos, {total_atualizados} atualizados (acumulado)")
        
        conn.commit()
    
    logging.info(f"Importação de processos do Senado concluída. Total: {total_inseridos} inseridos, {total_atualizados} atualizados.")
    return total_inseridos > 0 or total_atualizados > 0


# ============================================================
# IMPORTAÇÃO DE DESPESAS - SENADO
# ============================================================

def import_despesas_senado(conn, ano: int = None) -> Optional[bool]:
    """
    Lê os JSONs de despesas CEAPS em backend/data/senado/despesas/{ano}.json
    e insere/atualiza os dados na tabela senado.despesa_ceaps.
    
    Se ano for fornecido, processa APENAS aquele ano (importação incremental).
    Caso contrário, processa todos os anos (importação completa).
    
    Estrutura esperada do JSON da API:
    {
        "despesas": [
            {
                "ano": 2023,
                "mes": 1,
                "codigoParlamentar": 123,
                "nomeParlamentar": "Nome",
                "tipoDespesa": "PASSAGEM AÉREA",
                "cpfCnpj": "12345678000199",
                "fornecedor": "LATAM",
                "documento": "123",
                "dataDespesa": "2023-01-15",
                "detalhamento": "...",
                "valorReembolsado": 1500.00,
                "tipoDocumento": "Nota Fiscal"
            }
        ]
    }
    """
    global _despesas_senado_importadas
    
    with _import_lock:
        despesas_dir = os.path.join(DATA_DIR, "senado", "despesas")
        if not os.path.isdir(despesas_dir):
            logging.warning(f"Diretório de despesas do senado não encontrado: {despesas_dir}")
            return None
        
        total_inseridos = 0
        
        # Determina quais arquivos processar
        if ano is not None:
            if ano in _despesas_senado_importadas:
                return None  # Já foi importado nesta sessão
            arquivos = [f"{ano}.json"]
        else:
            arquivos = sorted(os.listdir(despesas_dir))
        
        for fname in arquivos:
            if not fname.endswith(".json"):
                continue
            
            # Extrai o ano do nome do arquivo
            ano_arquivo = int(fname.replace(".json", ""))
            if ano_arquivo in _despesas_senado_importadas:
                continue
            
            filepath = os.path.join(despesas_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # A API pode retornar em diferentes formatos. Tenta os mais comuns.
            despesas_lista = []
            if "despesas" in data:
                despesas_lista = data["despesas"]
            elif isinstance(data, list):
                despesas_lista = data
            
            if not despesas_lista:
                logging.warning(f"Nenhuma despesa encontrada em {filepath}")
                _despesas_senado_importadas.add(ano_arquivo)
                continue
            
            inseridos_arquivo = 0
            
            try:
                with conn.cursor() as cursor:
                    # Pré-carrega os códigos de senadores existentes para evitar FK violations
                    cursor.execute("SELECT codigo FROM senado.parlamentar")
                    senadores_existentes = {row[0] for row in cursor.fetchall()}
                    
                    for despesa in despesas_lista:
                        try:
                            cod_senador = despesa.get("codSenador")
                            if not cod_senador:
                                continue
                            
                            # Tenta buscar senador não cadastrado na API
                            if cod_senador not in senadores_existentes:
                                logging.info(
                                    f"Senador {cod_senador} não encontrado na tabela parlamentar. "
                                    f"Buscando na API... (ano={despesa.get('ano')}, doc={despesa.get('documento')})"
                                )
                                inserido = _buscar_e_inserir_senador_api(cursor, cod_senador)
                                if inserido:
                                    conn.commit()
                                    senadores_existentes.add(cod_senador)
                                    logging.info(f"Senador {cod_senador} cadastrado com sucesso via API.")
                                else:
                                    logging.warning(
                                        f"Senador {cod_senador} não encontrado na API. "
                                        f"Pulando despesa (ano={despesa.get('ano')}, doc={despesa.get('documento')})"
                                    )
                                    continue

                            
                            id_despesa_api = despesa.get("id")
                            if not id_despesa_api:
                                continue
                            with savepoint(cursor, "sp_senado_despesa"):
                                cursor.execute("""
                                    INSERT INTO senado.despesa_ceaps
                                        (id_despesa, ano, mes, cod_senador, nome_senador, tipo_despesa,
                                         cpf_cnpj, fornecedor, documento, data_despesa,
                                         detalhamento, valor_reembolsado, tipo_documento)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (id_despesa)
                                    DO NOTHING
                                """, (
                                    id_despesa_api,
                                    despesa.get("ano"),
                                    despesa.get("mes"),
                                    cod_senador,
                                    despesa.get("nomeSenador", ""),
                                    despesa.get("tipoDespesa", ""),
                                    despesa.get("cpfCnpj"),
                                    despesa.get("fornecedor", ""),
                                    despesa.get("documento"),
                                    despesa.get("data"),
                                    despesa.get("detalhamento"),
                                    despesa.get("valorReembolsado", 0),
                                    despesa.get("tipoDocumento")
                                ))
                            if cursor.rowcount > 0:
                                inseridos_arquivo += 1
                        except Exception as e:
                            logging.error(f"Erro ao inserir despesa do senado (ano={despesa.get('ano')}, doc={despesa.get('documento')}): {e}")
                            continue
                    else:
                        conn.commit()
                        total_inseridos += inseridos_arquivo
                        if inseridos_arquivo > 0:
                            logging.info(f"Arquivo {fname}: {inseridos_arquivo} despesas importadas.")
                        _despesas_senado_importadas.add(ano_arquivo)
                        
                        json_count = len(despesas_lista)
                        cursor.execute(
                            "SELECT COUNT(*) FROM senado.despesa_ceaps WHERE ano = %s",
                            (ano_arquivo,),
                        )
                        db_count = cursor.fetchone()[0]
                        if json_count > 0 and json_count == db_count:
                            mark_verified("senado_despesas", str(ano_arquivo), json_count, db_count)
            except Exception as e:
                logging.error(f"Erro ao processar arquivo {fname}: {e}")
                conn.rollback()
                continue
        
        if total_inseridos > 0 or ano is None:
            logging.info(f"Importação de despesas do Senado concluída. {total_inseridos} registros inseridos.")
        return True if total_inseridos > 0 else None



# ============================================================
# IMPORTAÇÃO DE HISTÓRICO DE DEPUTADOS - CÂMARA
# ============================================================

def import_historico_deputados(conn, deputado_id: int = None) -> Optional[bool]:
    deputados_dir = os.path.join(DATA_DIR, "camara", "deputados")
    if not os.path.isdir(deputados_dir):
        logging.warning(f"Diretório de deputados não encontrado: {deputados_dir}")
        return None

    if deputado_id is not None:
        arquivos = [deputado_id]
    else:
        arquivos = []
        for dep_id_str in sorted(os.listdir(deputados_dir)):
            dep_dir = os.path.join(deputados_dir, dep_id_str)
            if not os.path.isdir(dep_dir):
                continue
            if os.path.isfile(os.path.join(dep_dir, "historico.json")):
                try:
                    arquivos.append(int(dep_id_str))
                except ValueError:
                    continue

    if not arquivos:
        return None

    total_inseridos = 0
    with conn.cursor() as cursor:
        for dep_id in arquivos:
            try:
                inseridos = _importar_historico_cursor(cursor, dep_id)
                total_inseridos += inseridos
                if inseridos > 0:
                    logging.info(f"Histórico do deputado {dep_id}: {inseridos} eventos importados.")
            except Exception as e:
                logging.error(f"Erro ao importar histórico do deputado {dep_id}: {e}")

    conn.commit()
    if total_inseridos > 0:
        logging.info(f"Importação de históricos concluída. {total_inseridos} eventos inseridos.")
    return True if total_inseridos > 0 else None


# ============================================================
# DETALHES DE DEPUTADOS (situação/condição eleitoral)
# ============================================================

def import_detalhes_deputados(conn, deputado_id: int = None) -> Optional[bool]:
    deputados_dir = os.path.join(DATA_DIR, "camara", "deputados")
    if not os.path.isdir(deputados_dir):
        logging.warning(f"Diretório de deputados não encontrado: {deputados_dir}")
        return None

    if deputado_id is not None:
        arquivos = [deputado_id]
    else:
        arquivos = []
        for dep_id_str in sorted(os.listdir(deputados_dir)):
            dep_dir = os.path.join(deputados_dir, dep_id_str)
            if not os.path.isdir(dep_dir):
                continue
            if os.path.isfile(os.path.join(dep_dir, "detalhes.json")):
                try:
                    arquivos.append(int(dep_id_str))
                except ValueError:
                    continue

    if not arquivos:
        return None

    total_atualizados = 0
    with conn.cursor() as cursor:
        for dep_id in arquivos:
            try:
                atualizados = _importar_detalhes_cursor(cursor, dep_id)
                total_atualizados += atualizados
            except Exception as e:
                logging.error(f"Erro ao atualizar detalhes do deputado {dep_id}: {e}")

    conn.commit()
    if total_atualizados > 0:
        logging.info(f"Detalhes de deputados concluído. {total_atualizados} mandatos atualizados.")
    return True if total_atualizados > 0 else None


# ============================================================
# IMPORTAÇÃO DE PROPOSIÇÕES - CÂMARA
# ============================================================

def import_proposicoes_camara(conn, ano: int = None) -> Optional[bool]:
    """
    Lê os JSONs de proposições em backend/data/camara/proposicoes/ano/
    e insere/atualiza os dados na tabela camara.proposicoes.
    
    Se ano for fornecido, processa APENAS aquele ano (importação incremental).
    Caso contrário, processa todos os anos (importação completa).
    
    Estrutura esperada do JSON da API (listagem):
    {
        "dados": [
            {
                "id": 2599885,
                "uri": "...",
                "siglaTipo": "PL",
                "codTipo": 139,
                "numero": 1,
                "ano": 2026,
                "ementa": "...",
                "dataApresentacao": "2026-01-02T10:11"
            }
        ]
    }
    """
    proposicoes_dir = os.path.join(DATA_DIR, "camara", "proposicoes", "ano")
    if not os.path.isdir(proposicoes_dir):
        logging.warning(f"Diretório de proposições não encontrado: {proposicoes_dir}")
        return None
    
    total_inseridos = 0
    
    # Determina quais arquivos processar
    if ano is not None:
        arquivos = [f for f in os.listdir(proposicoes_dir) if f == f"{ano}.json"]
    else:
        arquivos = sorted([f for f in os.listdir(proposicoes_dir) if f.endswith(".json")])
    
    if not arquivos:
        logging.warning(f"Nenhum arquivo de proposições encontrado em {proposicoes_dir}")
        return None
    
    logging.info(f"Importando proposições de {len(arquivos)} arquivo(s)...")
    
    with conn.cursor() as cursor:
        for fname in arquivos:
            filepath = os.path.join(proposicoes_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            dados = data.get("dados", [])
            if not dados:
                continue
            
            inseridos_arquivo = 0
            
            for prop in dados:
                try:
                    with savepoint(cursor, "sp_prop"):
                        cursor.execute("""
                            INSERT INTO camara.proposicoes
                                (id, sigla_tipo, cod_tipo, numero, ano, ementa, data_apresentacao, uri)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                sigla_tipo = EXCLUDED.sigla_tipo,
                                cod_tipo = EXCLUDED.cod_tipo,
                                numero = EXCLUDED.numero,
                                ano = EXCLUDED.ano,
                                ementa = EXCLUDED.ementa,
                                data_apresentacao = EXCLUDED.data_apresentacao,
                                uri = EXCLUDED.uri
                        """, (
                            prop.get("id"),
                            prop.get("siglaTipo"),
                            prop.get("codTipo"),
                            prop.get("numero"),
                            prop.get("ano"),
                            prop.get("ementa"),
                            prop.get("dataApresentacao"),
                            prop.get("uri")
                        ))
                    if cursor.rowcount > 0:
                        inseridos_arquivo += 1
                except Exception as e:
                    logging.error(f"Erro ao inserir proposição {prop.get('id')}: {e}")
                    continue
            else:
                conn.commit()
                total_inseridos += inseridos_arquivo
                if inseridos_arquivo > 0:
                    logging.info(f"Arquivo {fname}: {inseridos_arquivo} proposições importadas.")
                continue
            
            logging.warning(f"Arquivo {fname}: importação interrompida devido a erro.")
    
    if total_inseridos > 0:
        logging.info(f"Importação de proposições concluída. {total_inseridos} registros inseridos/atualizados.")
    return True if total_inseridos > 0 else None


def import_proposicoes_deputado(conn, deputado_id: int) -> Optional[bool]:
    """
    Lê os JSONs de proposições de um deputado específico em
     backend/data/camara/proposicoes/autor/{deputado_id}.json
    e insere/atualiza os dados na tabela camara.proposicoes.
    
    A estrutura do JSON é a mesma da listagem geral (via API com idDeputadoAutor).
    """
    proposicoes_dir = os.path.join(DATA_DIR, "camara", "proposicoes", "autor")
    if not os.path.isdir(proposicoes_dir):
        logging.warning(f"Diretório de proposições por deputado não encontrado: {proposicoes_dir}")
        return None
    
    arquivos = sorted([
        f for f in os.listdir(proposicoes_dir)
        if f == f"{deputado_id}.json"
    ])
    
    if not arquivos:
        logging.warning(f"Nenhum arquivo de proposições encontrado para deputado {deputado_id}")
        return None
    
    logging.info(f"Importando proposições do deputado {deputado_id} de {len(arquivos)} arquivo(s)...")
    
    total_inseridos = 0
    
    with conn.cursor() as cursor:
        for fname in arquivos:
            filepath = os.path.join(proposicoes_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            dados = data.get("dados", [])
            if not dados:
                continue
            
            inseridos_arquivo = 0
            
            for prop in dados:
                try:
                    with savepoint(cursor, "sp_propdep"):
                        cursor.execute("""
                            INSERT INTO camara.proposicoes
                                (id, sigla_tipo, cod_tipo, numero, ano, ementa, data_apresentacao, uri)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                sigla_tipo = EXCLUDED.sigla_tipo,
                                cod_tipo = EXCLUDED.cod_tipo,
                                numero = EXCLUDED.numero,
                                ano = EXCLUDED.ano,
                                ementa = EXCLUDED.ementa,
                                data_apresentacao = EXCLUDED.data_apresentacao,
                                uri = EXCLUDED.uri
                        """, (
                            prop.get("id"),
                            prop.get("siglaTipo"),
                            prop.get("codTipo"),
                            prop.get("numero"),
                            prop.get("ano"),
                            prop.get("ementa"),
                            prop.get("dataApresentacao"),
                            prop.get("uri")
                        ))
                    if cursor.rowcount > 0:
                        inseridos_arquivo += 1
                except Exception as e:
                    logging.error(f"Erro ao inserir proposição {prop.get('id')} do deputado {deputado_id}: {e}")
                    continue
            else:
                conn.commit()
                total_inseridos += inseridos_arquivo
                if inseridos_arquivo > 0:
                    logging.info(f"Arquivo {fname}: {inseridos_arquivo} proposições importadas.")
                continue
            
            logging.warning(f"Arquivo {fname}: importação interrompida devido a erro.")
    
    if total_inseridos > 0:
        logging.info(f"Importação de proposições do deputado {deputado_id} concluída. {total_inseridos} registros inseridos/atualizados.")
    return True if total_inseridos > 0 else None


def import_votacoes_camara(conn, ano: int = None) -> Optional[bool]:
    """
    Lê os JSONs de votações em backend/data/camara/votacoes/
    e insere/atualiza os dados nas tabelas camara.votacoes e
    camara.votacoes_proposicoes.

    Se ano for fornecido, processa APENAS aquele ano (importação incremental).
    Caso contrário, processa todos os anos (importação completa).

    Estrutura esperada do JSON da API (listagem):
    {
        "dados": [
            {
                "id": "2196871-83",
                "uri": "...",
                "data": "2026-06-18",
                "dataHoraRegistro": "2026-06-18T11:37:20",
                "siglaOrgao": "CDE",
                "uriOrgao": "...",
                "uriEvento": null,
                "proposicaoObjeto": null,
                "uriProposicaoObjeto": null,
                "descricao": "...",
                "aprovacao": 1
            }
        ]
    }

    Extrai id_orgao e id_evento das URIs quando disponíveis.
    Insere também a relação proposição nas votações_proposicoes
    quando proposicaoObjeto não for nulo.
    """
    votacoes_dir = os.path.join(DATA_DIR, "camara", "votacoes")
    if not os.path.isdir(votacoes_dir):
        logging.warning(f"Diretório de votações não encontrado: {votacoes_dir}")
        return None

    # Determina quais arquivos processar
    if ano is not None:
        merged = os.path.join(votacoes_dir, f"{ano}.json")
        if os.path.isfile(merged):
            arquivos = [f"{ano}.json"]
        else:
            arquivos = sorted([
                f for f in os.listdir(votacoes_dir)
                if f.startswith(f"{ano}_Q") and f.endswith(".json")
            ])
    else:
        all_files = sorted([
            f for f in os.listdir(votacoes_dir)
            if f.endswith(".json")
        ])
        merged_years = {
            f.replace(".json", "")
            for f in all_files if "_Q" not in f
        }
        arquivos = [f for f in all_files if "_Q" not in f]
        for f in all_files:
            if "_Q" in f:
                ano_str = f.split("_")[0]
                if ano_str not in merged_years:
                    arquivos.append(f)

    if not arquivos:
        logging.warning(f"Nenhum arquivo de votações encontrado em {votacoes_dir}")
        return None

    logging.info(f"Importando votações de {len(arquivos)} arquivo(s)...")

    total_inseridos = 0

    with conn.cursor() as cursor:
        for fname in arquivos:
            filepath = os.path.join(votacoes_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            dados = data.get("dados", [])
            if not dados:
                continue

            inseridos_arquivo = 0

            for vot in dados:
                try:
                    id_orgao = None
                    uri_orgao = vot.get("uriOrgao")
                    if uri_orgao:
                        try:
                            id_orgao = int(uri_orgao.rstrip("/").split("/")[-1])
                        except (ValueError, IndexError):
                            pass

                    id_evento = None
                    uri_evento = vot.get("uriEvento")
                    if uri_evento:
                        try:
                            id_evento = int(uri_evento.rstrip("/").split("/")[-1])
                        except (ValueError, IndexError):
                            pass

                    with savepoint(cursor, "sp_vot"):
                        cursor.execute("""
                            INSERT INTO camara.votacoes
                                (id, uri, data, data_hora_registro, sigla_orgao,
                                 uri_orgao, id_orgao, uri_evento, id_evento,
                                 descricao, aprovacao)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                uri = EXCLUDED.uri,
                                data = EXCLUDED.data,
                                data_hora_registro = EXCLUDED.data_hora_registro,
                                sigla_orgao = EXCLUDED.sigla_orgao,
                                uri_orgao = EXCLUDED.uri_orgao,
                                id_orgao = EXCLUDED.id_orgao,
                                uri_evento = EXCLUDED.uri_evento,
                                id_evento = EXCLUDED.id_evento,
                                descricao = EXCLUDED.descricao,
                                aprovacao = EXCLUDED.aprovacao
                        """, (
                            vot.get("id"),
                            vot.get("uri"),
                            vot.get("data"),
                            vot.get("dataHoraRegistro"),
                            vot.get("siglaOrgao"),
                            vot.get("uriOrgao"),
                            id_orgao,
                            vot.get("uriEvento"),
                            id_evento,
                            vot.get("descricao"),
                            vot.get("aprovacao"),
                        ))

                        proposicao_id = None
                        uri_prop = vot.get("uriProposicaoObjeto")
                        if uri_prop:
                            try:
                                proposicao_id = int(uri_prop.rstrip("/").split("/")[-1])
                            except (ValueError, IndexError):
                                pass
                        proposicao_objeto = vot.get("proposicaoObjeto")
                        if proposicao_id is not None or proposicao_objeto is not None:
                            try:
                                cursor.execute("""
                                    INSERT INTO camara.votacoes_proposicoes
                                        (votacao_id, proposicao_id, proposicao_objeto)
                                    VALUES (%s, %s, %s)
                                    ON CONFLICT (votacao_id, proposicao_id) DO NOTHING
                                """, (
                                    vot.get("id"),
                                    proposicao_id,
                                    proposicao_objeto,
                                ))
                            except Exception:
                                cursor.execute("ROLLBACK TO SAVEPOINT sp_vot")

                    inseridos_arquivo += 1
                except Exception as e:
                    logging.error(f"Erro ao inserir votação {vot.get('id')}: {e}")
                    continue
            else:
                conn.commit()
                total_inseridos += inseridos_arquivo
                if inseridos_arquivo > 0:
                    logging.info(f"Arquivo {fname}: {inseridos_arquivo} votações importadas.")
                continue

            logging.warning(f"Arquivo {fname}: importação interrompida devido a erro.")

    if total_inseridos > 0:
        logging.info(f"Importação de votações concluída. {total_inseridos} registros inseridos/atualizados.")
    return True if total_inseridos > 0 else None


def import_detalhes_proposicoes(conn, ano: int = None) -> bool:
    """
    Lê os JSONs de detalhes em backend/data/camara/proposicoes/{id}/detalhes.json
    e atualiza os campos adicionais na tabela camara.proposicoes
    (descricao_tipo, ementa_detalhada, keywords, url_inteiro_teor, etc.).
    
    Se ano for fornecido, processa APENAS proposições daquele ano.
    Caso contrário, processa todos os detalhes disponíveis.
    """
    proposicoes_dir = os.path.join(DATA_DIR, "camara", "proposicoes")
    if not os.path.isdir(proposicoes_dir):
        logging.warning(f"Diretório de proposições não encontrado: {proposicoes_dir}")
        return False
    
    arquivos = []
    for prop_id_str in sorted(os.listdir(proposicoes_dir)):
        prop_dir = os.path.join(proposicoes_dir, prop_id_str)
        if not os.path.isdir(prop_dir):
            continue
        detalhes_file = os.path.join(prop_dir, "detalhes.json")
        if not os.path.isfile(detalhes_file):
            continue
        try:
            prop_id = int(prop_id_str)
        except ValueError:
            continue
        # Se ano foi especificado, verifica se a proposição é daquele ano
        if ano is not None:
            cursor = conn.cursor()
            cursor.execute("SELECT ano FROM camara.proposicoes WHERE id = %s", (prop_id,))
            row = cursor.fetchone()
            cursor.close()
            if not row or row[0] != ano:
                continue
        arquivos.append((prop_id, detalhes_file))
    
    if not arquivos:
        return False
    
    total_atualizados = 0
    
    with conn.cursor() as cursor:
        for prop_id, filepath in arquivos:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            dados = data.get("dados", {})
            if not dados:
                continue
            
            try:
                with savepoint(cursor, "sp_detprop"):
                    cursor.execute("""
                        UPDATE camara.proposicoes SET
                            descricao_tipo = COALESCE(%s, descricao_tipo),
                            ementa_detalhada = COALESCE(%s, ementa_detalhada),
                            keywords = COALESCE(%s, keywords),
                            url_inteiro_teor = COALESCE(%s, url_inteiro_teor),
                            urn_final = COALESCE(%s, urn_final),
                            texto = COALESCE(%s, texto),
                            justificativa = COALESCE(%s, justificativa),
                            uri_orgao_numerador = COALESCE(%s, uri_orgao_numerador),
                            uri_prop_principal = COALESCE(%s, uri_prop_principal),
                            uri_prop_anterior = COALESCE(%s, uri_prop_anterior),
                            uri_prop_posterior = COALESCE(%s, uri_prop_posterior)
                        WHERE id = %s
                    """, (
                        dados.get("descricaoTipo"),
                        dados.get("ementaDetalhada"),
                    dados.get("keywords"),
                    dados.get("urlInteiroTeor"),
                    dados.get("urnFinal"),
                    dados.get("texto"),
                    dados.get("justificativa"),
                    dados.get("uriOrgaoNumerador"),
                    dados.get("uriPropPrincipal"),
                    dados.get("uriPropAnterior"),
                    dados.get("uriPropPosterior"),
                    prop_id
                ))
                if cursor.rowcount > 0:
                    total_atualizados += 1
            except Exception as e:
                logging.error(f"Erro ao atualizar detalhes da proposição {prop_id}: {e}")
                continue
        
        conn.commit()
    
    if total_atualizados > 0:
        logging.info(f"Detalhes de {total_atualizados} proposições atualizados.")
    return total_atualizados > 0


def import_autores_proposicoes(conn, ano: int = None) -> bool:
    """
    Lê os JSONs de autores em backend/data/camara/proposicoes/{id}/autores.json
    e insere na tabela camara.proposicoes_autores.
    
    Tenta identificar se o autor é um deputado conhecido no banco
    através da URI (contém '/deputados/') ou pelo nome.
    
    Se ano for fornecido, processa APENAS proposições daquele ano.
    """
    proposicoes_dir = os.path.join(DATA_DIR, "camara", "proposicoes")
    if not os.path.isdir(proposicoes_dir):
        logging.warning(f"Diretório de proposições não encontrado: {proposicoes_dir}")
        return False
    
    arquivos = []
    for prop_id_str in sorted(os.listdir(proposicoes_dir)):
        prop_dir = os.path.join(proposicoes_dir, prop_id_str)
        if not os.path.isdir(prop_dir):
            continue
        autores_file = os.path.join(prop_dir, "autores.json")
        if not os.path.isfile(autores_file):
            continue
        try:
            prop_id = int(prop_id_str)
        except ValueError:
            continue
        # Se ano foi especificado, verifica se a proposição é daquele ano
        if ano is not None:
            cursor = conn.cursor()
            cursor.execute("SELECT ano FROM camara.proposicoes WHERE id = %s", (prop_id,))
            row = cursor.fetchone()
            cursor.close()
            if not row or row[0] != ano:
                continue
        arquivos.append((prop_id, autores_file))
    
    if not arquivos:
        return False
    
    total_inseridos = 0
    
    with conn.cursor() as cursor:
        for prop_id, filepath in arquivos:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            autores_lista = data.get("dados", [])
            if not autores_lista:
                continue
            
            inseridos_prop = 0
            
            for autor in autores_lista:
                try:
                    with savepoint(cursor, "sp_autor"):
                        uri = autor.get("uri", "")
                        nome = autor.get("nome", "")
                        cod_tipo = autor.get("codTipo")
                        tipo = autor.get("tipo", "")
                        ordem = autor.get("ordemAssinatura")
                        proponente = autor.get("proponente", 0)
                        
                        # Tenta identificar se é um deputado pela URI
                        deputado_id = None
                        if "/deputados/" in uri:
                            # Extrai o ID do deputado da URI
                            try:
                                deputado_id = int(uri.split("/deputados/")[-1].split("/")[0].split("?")[0])
                            except (ValueError, IndexError):
                                pass
                        
                        # Se não encontrou pela URI, tenta pelo nome
                        if deputado_id is None and nome:
                            cursor.execute("""
                                SELECT id FROM camara.deputados 
                                WHERE nome_civil ILIKE %s 
                                LIMIT 1
                            """, (nome.strip(),))
                            row = cursor.fetchone()
                            if row:
                                deputado_id = row[0]
                        
                        cursor.execute("""
                            INSERT INTO camara.proposicoes_autores
                                (proposicao_id, deputado_id, tipo_autor, ordem_assinatura, proponente)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (proposicao_id, deputado_id) DO NOTHING
                        """, (
                            prop_id,
                            deputado_id,
                            tipo,
                            ordem,
                            bool(proponente)
                        ))
                    if cursor.rowcount > 0:
                        inseridos_prop += 1
                except Exception as e:
                    logging.error(f"Erro ao inserir autor da proposição {prop_id}: {e}")
                    continue
            else:
                conn.commit()
                total_inseridos += inseridos_prop
                continue
            
            logging.warning(f"Proposição {prop_id}: importação de autores interrompida devido a erro.")
    
    if total_inseridos > 0:
        logging.info(f"Importação de autores concluída. {total_inseridos} registros inseridos.")
    return total_inseridos > 0


# ============================================================
# IMPORTAÇÃO DE EMENDAS - PORTAL DA TRANSPARÊNCIA
# ============================================================

def _parse_br_number(valor) -> float:
    """
    Converte string no formato brasileiro (ex: '15.300.000,00') para float.
    Se já for int/float, retorna o próprio valor.
    Se for None ou vazio, retorna 0.0.
    """
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    if not isinstance(valor, str) or not valor.strip():
        return 0.0
    try:
        # Remove whitespace e converte formato brasileiro (ex: '- 15.300.000,00') para float
        s = "".join(valor.split())
        return float(s.replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        logger.warning(f"Não foi possível converter valor '{valor}' para número.")
        return 0.0


def import_emendas(conn, arquivo: str = None) -> Optional[bool]:
    """
    Lê os JSONs de emendas em backend/data/portal/emendas/
    e insere/atualiza os dados na tabela portal.emendas.
    
    Se 'arquivo' for fornecido (ex: "ERIKA_HILTON"), processa APENAS os arquivos
    que começam com aquele prefixo (importação incremental).
    Caso contrário, processa todos os arquivos (importação completa).
    
    Estrutura esperada do JSON da API do Portal da Transparência:
    [
        {
            "anoEmenda": 2024,
            "codigoEmenda": "12345",
            "tipoEmenda": "Individual",
            "nomeAutor": "ERIKA HILTON",
            "numeroEmenda": "1",
            "localidadeDoGasto": "São Paulo",
            "funcao": "Saúde",
            "subfuncao": "Atenção Básica",
            "valorEmpenhado": 100000.00,
            "valorLiquidado": 50000.00,
            "valorPago": 45000.00,
            "valorRestoInscrito": 0.00,
            "valorRestoCancelado": 0.00,
            "valorRestoPago": 0.00
        }
    ]
    """
    global _emendas_importadas
    
    emendas_dir = os.path.join(DATA_DIR, "portal", "emendas")
    if not os.path.isdir(emendas_dir):
        logging.warning(f"Diretório de emendas não encontrado: {emendas_dir}")
        return None
    
    total_inseridos = 0
    
    # Determina quais arquivos processar
    if arquivo is not None:
        # Modo incremental: processa apenas arquivos do parlamentar específico
        # Remove acentos para compatibilidade com nomes de arquivos salvos pelo scraper
        nome_sem_acento = unicodedata.normalize('NFKD', arquivo)
        nome_sem_acento = ''.join(c for c in nome_sem_acento if not unicodedata.combining(c))
        prefixo = nome_sem_acento.replace(" ", "_").replace("/", "_").upper()
        if prefixo in _emendas_importadas:
            return None  # Já foi importado nesta sessão
        arquivos = [f for f in os.listdir(emendas_dir) if f.startswith(prefixo) and f.endswith(".json")]

    else:
        # Modo completo: processa todos os arquivos
        arquivos = sorted(os.listdir(emendas_dir))
    
    json_counts_by_prefix = {}
    autor_por_prefix = {}

    with conn.cursor() as cursor:
        for fname in arquivos:
            if not fname.endswith(".json"):
                continue

            # Extrai o prefixo do nome do arquivo (ex: "ERIKA_HILTON_2024" de "ERIKA_HILTON_2024.json")
            prefixo_arquivo = fname.replace(".json", "")
            if prefixo_arquivo in _emendas_importadas:
                continue  # Já importado nesta sessão

            filepath = os.path.join(emendas_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            emendas_lista = data.get("emendas", [])
            if not emendas_lista:
                continue

            # Parlamentar prefix (sem ano) para agrupar verificacao
            parts = prefixo_arquivo.rsplit('_', 1)
            if len(parts) == 2 and len(parts[1]) == 4 and parts[1].isdigit():
                parlamentar_prefix = parts[0]
            else:
                parlamentar_prefix = prefixo_arquivo

            # Filtra emendas por match exato no nomeAutor (API do Portal faz substring match)
            nome_esperado = remover_acentos(parlamentar_prefix.replace("_", " ").upper())
            emendas_lista = [
                e for e in emendas_lista
                if remover_acentos((e.get("nomeAutor") or "").strip().upper()) == nome_esperado
            ]
            if not emendas_lista:
                continue

            if parlamentar_prefix not in autor_por_prefix:
                autor_por_prefix[parlamentar_prefix] = emendas_lista[0].get("nomeAutor", "")

            inseridos_arquivo = 0

            for emenda in emendas_lista:
                try:
                    with savepoint(cursor, "sp_emenda"):
                        cursor.execute("""
                            INSERT INTO portal.emendas
                                (codigo_emenda, ano, tipo_emenda, autor, nome_autor,
                                 numero_emenda, localidade_gasto, funcao, subfuncao,
                                 valor_empenhado, valor_liquidado, valor_pago,
                                 valor_resto_inscrito, valor_resto_cancelado, valor_resto_pago)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            emenda.get("codigoEmenda"),
                            emenda.get("ano"),
                            emenda.get("tipoEmenda"),
                            emenda.get("nomeAutor", ""),
                            emenda.get("nomeAutor", ""),
                            emenda.get("numeroEmenda"),
                            emenda.get("localidadeDoGasto"),
                            emenda.get("funcao"),
                            emenda.get("subfuncao"),
                            _parse_br_number(emenda.get("valorEmpenhado")),
                            _parse_br_number(emenda.get("valorLiquidado")),
                            _parse_br_number(emenda.get("valorPago")),
                            _parse_br_number(emenda.get("valorRestoInscrito")),
                            _parse_br_number(emenda.get("valorRestoCancelado")),
                            _parse_br_number(emenda.get("valorRestoPago"))
                        ))
                    if cursor.rowcount > 0:
                        inseridos_arquivo += 1
                except Exception as e:
                    logging.error(f"Erro ao inserir emenda {emenda.get('codigoEmenda')}: {e}")
                    continue
            else:
                conn.commit()
                total_inseridos += inseridos_arquivo
                if inseridos_arquivo > 0:
                    logging.info(f"Arquivo {fname}: {inseridos_arquivo} emendas importadas.")
                _emendas_importadas.add(prefixo_arquivo)
                json_counts_by_prefix[parlamentar_prefix] = json_counts_by_prefix.get(parlamentar_prefix, 0) + len(emendas_lista)
                continue

            # Se chegou aqui, houve break por erro
            logging.warning(f"Arquivo {fname}: importação interrompida devido a erro.")

        for parlamentar_prefix, json_count in json_counts_by_prefix.items():
            if json_count == 0:
                continue
            nome_esperado = parlamentar_prefix.replace("_", " ").upper()
            try:
                cursor.execute(
                    "SELECT COUNT(*) FROM portal.emendas WHERE lower(autor) = lower(%s)",
                    (nome_esperado,),
                )
                db_count = cursor.fetchone()[0]
                if json_count > 0 and json_count == db_count:
                    mark_verified("portal_emendas", parlamentar_prefix, json_count, db_count)
            except Exception:
                pass
    
    if total_inseridos > 0 or arquivo is None:
        logging.info(f"Importação de emendas concluída. {total_inseridos} registros inseridos.")
    elif any(v > 0 for v in json_counts_by_prefix.values()):
        logging.info("Importação de emendas concluída (dados já estavam sincronizados).")
        return True
    return True if total_inseridos > 0 else None



# ============================================================
# A importação principal agora é feita pelo pipeline (pipeline.py).
# _importar_dados_complementares está definida acima, junto das
# funções atômicas de mandato.
# ============================================================
