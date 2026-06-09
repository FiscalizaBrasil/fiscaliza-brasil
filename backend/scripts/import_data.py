#!/usr/bin/env python
"""
Script de importação de dados dos JSONs baixados pelo scraper para o banco de dados.
Lê os arquivos em backend/data/ e popula as tabelas.
"""

import os
import json
import logging
import sys
import requests
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from database import db
except ImportError as e:
    logging.error(f"Error importing database module: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

# Cache de senadores já buscados na API para evitar chamadas repetidas
_senadores_buscados_api = set()


def _buscar_e_inserir_senador_api(cursor, cod_senador: int) -> bool:
    """
    Busca dados de um senador na API pública do Senado e insere na tabela parlamentar.
    Retorna True se conseguiu inserir, False caso contrário.
    
    API: GET https://legis.senado.leg.br/dadosabertos/senador/{codigo}?v=6
    """
    global _senadores_buscados_api
    
    # Evita chamadas repetidas para o mesmo código
    if cod_senador in _senadores_buscados_api:
        return False
    
    _senadores_buscados_api.add(cod_senador)
    
    url = f"https://legis.senado.leg.br/dadosabertos/senador/{cod_senador}?v=6"
    headers = {"accept": "application/json"}
    
    try:
        logging.info(f"Buscando dados do senador {cod_senador} na API...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Navega na estrutura do JSON para encontrar os dados do parlamentar
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
            resp_mandatos = requests.get(url_mandatos, headers=headers, timeout=10)
            if resp_mandatos.status_code == 200:
                dados_mandatos = resp_mandatos.json()
                mandatos = (
                    dados_mandatos.get("Mandatos", {})
                    .get("Mandato", [])
                )
                if isinstance(mandatos, dict):
                    mandatos = [mandatos]
                for mandato in mandatos:
                    codigo_mandato = mandato.get("CodigoMandato", "")
                    if codigo_mandato:
                        uf_mandato = mandato.get("UfParlamentar", uf)
                        descricao = mandato.get("DescricaoParticipacao", "")
                        
                        # Insere legislaturas do mandato
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
                        
                        cursor.execute("""
                            INSERT INTO senado.mandato
                                (codigo_mandato, codigo_parlamentar, uf,
                                 descricao_participacao,
                                 primeira_legislatura, segunda_legislatura)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (codigo_mandato) DO NOTHING
                        """, (codigo_mandato, codigo, uf_mandato,
                              descricao, primeira_leg, segunda_leg))
        except Exception as e:
            logging.warning(f"Não foi possível buscar mandatos do senador {cod_senador}: {e}")
        
        logging.info(f"Senador {cod_senador} ({nome_parlamentar}) inserido via API.")
        time.sleep(0.3)  # Rate limiting
        return True
        
    except requests.exceptions.Timeout:


        logging.warning(f"Timeout ao buscar senador {cod_senador} na API")
        return False
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            logging.warning(f"Senador {cod_senador} não encontrado na API (404)")
        else:
            logging.warning(f"Erro HTTP ao buscar senador {cod_senador}: {e}")
        return False
    except Exception as e:
        logging.warning(f"Erro ao buscar senador {cod_senador} na API: {e}")
        return False


# ============================================================
# CÂMARA DOS DEPUTADOS
# ============================================================

def import_deputados_camara(conn) -> bool:
    """
    Lê backend/data/camara/deputados.json e insere os dados no banco.
    Retorna True se importou dados, False se o arquivo não existe.
    """
    filepath = os.path.join(DATA_DIR, "camara", "deputados.json")
    if not os.path.isfile(filepath):
        logging.warning(f"Arquivo não encontrado: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    dados = data.get("dados", [])
    if not dados:
        logging.warning("Nenhum dado encontrado no arquivo da Câmara.")
        return False

    logging.info(f"Importando {len(dados)} deputados da Câmara...")

    with conn.cursor() as cursor:
        for dep in dados:
            dep_id = dep["id"]
            nome = dep.get("nome", "").strip()
            partido = dep.get("siglaPartido", "")
            uf = dep.get("siglaUf", "")
            url_foto = dep.get("urlFoto", "")
            email = dep.get("email", "")
            id_legislatura = dep.get("idLegislatura")

            # 1. Insere/ignora legislatura
            if id_legislatura:
                cursor.execute("""
                    INSERT INTO camara.legislaturas (id, data_inicio)
                    VALUES (%s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (id_legislatura, f"{2023 - (57 - id_legislatura) * 4}-02-01"))

            # 2. Insere/ignora deputado
            cursor.execute("""
                INSERT INTO camara.deputados (id, nome_civil, email)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (dep_id, nome, email))

            # 3. Insere/ignora mandato
            if id_legislatura:
                mandato_id = f"{dep_id}_{id_legislatura}"
                cursor.execute("""
                    INSERT INTO camara.deputados_mandatos
                        (id, deputado_id, legislatura_id, nome_eleitoral,
                         sigla_partido, sigla_uf, url_foto, email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (mandato_id, dep_id, id_legislatura, nome,
                      partido, uf, url_foto, email))

    conn.commit()
    logging.info("Importação da Câmara concluída.")
    return True


# ============================================================
# SENADO FEDERAL
# ============================================================

def import_senadores_senado(conn) -> bool:
    """
    Lê backend/data/senado/senadores.json e insere os dados no banco.
    Retorna True se importou dados, False se o arquivo não existe.
    """
    filepath = os.path.join(DATA_DIR, "senado", "senadores.json")
    if not os.path.isfile(filepath):
        logging.warning(f"Arquivo não encontrado: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    parlamentares = (
        data.get("ListaParlamentarEmExercicio", {})
        .get("Parlamentares", {})
        .get("Parlamentar", [])
    )

    if not parlamentares:
        logging.warning("Nenhum dado encontrado no arquivo do Senado.")
        return False

    logging.info(f"Importando {len(parlamentares)} senadores...")

    with conn.cursor() as cursor:
        for par in parlamentares:
            ident = par.get("IdentificacaoParlamentar", {})
            mandato = par.get("Mandato", {})

            codigo = int(ident.get("CodigoParlamentar", 0))
            if not codigo:
                continue

            nome_parlamentar = ident.get("NomeParlamentar", "").strip()
            nome_completo = ident.get("NomeCompletoParlamentar", "").strip()
            sexo = ident.get("SexoParlamentar", "")
            sigla_partido = ident.get("SiglaPartidoParlamentar", "")
            uf = ident.get("UfParlamentar", "")
            url_foto = ident.get("UrlFotoParlamentar", "")
            url_pagina = ident.get("UrlPaginaParlamentar", "")
            email = ident.get("EmailParlamentar", "")

            # 1. Insere/ignora legislaturas do mandato
            prim_leg = mandato.get("PrimeiraLegislaturaDoMandato", {})
            seg_leg = mandato.get("SegundaLegislaturaDoMandato")

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

            # 2. Insere/ignora parlamentar
            cursor.execute("""
                INSERT INTO senado.parlamentar
                    (codigo, nome_parlamentar, nome_completo, sexo,
                     sigla_partido, uf, url_foto, url_pagina, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (codigo) DO NOTHING
            """, (codigo, nome_parlamentar, nome_completo, sexo,
                  sigla_partido, uf, url_foto, url_pagina, email))

            # 3. Insere/ignora mandato
            codigo_mandato = mandato.get("CodigoMandato", "")
            if codigo_mandato:
                uf_mandato = mandato.get("UfParlamentar", uf)
                descricao = mandato.get("DescricaoParticipacao", "")
                primeira_leg = prim_leg.get("NumeroLegislatura", "") if prim_leg else ""
                segunda_leg = seg_leg.get("NumeroLegislatura", "") if seg_leg else ""

                cursor.execute("""
                    INSERT INTO senado.mandato
                        (codigo_mandato, codigo_parlamentar, uf,
                         descricao_participacao,
                         primeira_legislatura, segunda_legislatura)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (codigo_mandato) DO NOTHING
                """, (codigo_mandato, codigo, uf_mandato,
                      descricao, primeira_leg, segunda_leg))

    conn.commit()
    logging.info("Importação do Senado concluída.")
    return True


# ============================================================
# IMPORTAÇÃO DE DESPESAS - CÂMARA
# ============================================================

def import_despesas_camara(conn) -> bool:
    """
    Lê os JSONs de despesas em backend/data/camara/despesas/{deputado_id}/
    e insere/atualiza os dados na tabela camara.deputados_despesas.
    
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
    despesas_dir = os.path.join(DATA_DIR, "camara", "despesas")
    if not os.path.isdir(despesas_dir):
        logging.warning(f"Diretório de despesas não encontrado: {despesas_dir}")
        return False
    
    # Carrega o JSON de deputados para referência cruzada
    deputados_filepath = os.path.join(DATA_DIR, "camara", "deputados.json")
    deputados_por_id = {}
    if os.path.isfile(deputados_filepath):
        with open(deputados_filepath, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
        for dep in dep_data.get("dados", []):
            deputados_por_id[dep["id"]] = dep
    
    total_inseridos = 0
    
    # Percorre cada deputado
    for dep_id_str in os.listdir(despesas_dir):
        dep_dir = os.path.join(despesas_dir, dep_id_str)
        if not os.path.isdir(dep_dir):
            continue
        
        dep_id = int(dep_id_str)
        inseridos_dep = 0
        
        try:
            with conn.cursor() as cursor:
                # Busca o mandato_id para este deputado (qualquer legislatura)
                cursor.execute("""
                    SELECT id FROM camara.deputados_mandatos 
                    WHERE deputado_id = %s 
                    ORDER BY legislatura_id DESC LIMIT 1
                """, (dep_id,))
                mandato_row = cursor.fetchone()
                if not mandato_row:
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
                            # Insere legislatura se não existir
                            cursor.execute("""
                                INSERT INTO camara.legislaturas (id, data_inicio)
                                VALUES (%s, %s)
                                ON CONFLICT (id) DO NOTHING
                            """, (id_legislatura, f"{2023 - (57 - id_legislatura) * 4}-02-01"))
                        
                        # Insere deputado se não existir
                        cursor.execute("""
                            INSERT INTO camara.deputados (id, nome_civil, email)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """, (dep_id, nome, email))
                        
                        if id_legislatura:
                            # Insere mandato se não existir
                            mandato_id = f"{dep_id}_{id_legislatura}"
                            cursor.execute("""
                                INSERT INTO camara.deputados_mandatos
                                    (id, deputado_id, legislatura_id, nome_eleitoral,
                                     sigla_partido, sigla_uf, url_foto, email)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id) DO NOTHING
                            """, (mandato_id, dep_id, id_legislatura, nome,
                                  partido, uf, url_foto, email))
                            conn.commit()
                            logging.info(f"Deputado {dep_id} ({nome}) cadastrado dinamicamente a partir do JSON.")
                            mandato_row = cursor.fetchone() if False else (mandato_id,)
                        else:
                            logging.warning(f"Deputado {dep_id} encontrado no JSON mas sem idLegislatura. Pulando.")
                            continue
                    else:
                        logging.warning(f"Mandato não encontrado para deputado {dep_id} e deputado não consta no JSON. Pulando.")
                        continue
                mandato_id = mandato_row[0]
                
                # Percorre os arquivos JSON de cada ano/página
                for fname in sorted(os.listdir(dep_dir)):
                    if not fname.endswith(".json"):
                        continue
                    
                    filepath = os.path.join(dep_dir, fname)
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    dados = data.get("dados", [])
                    if not dados:
                        continue
                    
                    for despesa in dados:
                        try:
                            # Valida campos numéricos para evitar erro de sintaxe no PostgreSQL
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
                            if cursor.rowcount > 0:
                                inseridos_dep += 1
                        except Exception as e:
                            logging.error(f"Erro ao inserir despesa do deputado {dep_id} (doc={despesa.get('codDocumento')}, valor={despesa.get('valorDocumento')}): {e}")
                            # Faz rollback para resetar o estado da transação
                            conn.rollback()
                            # Marca que houve erro para pular o commit
                            break
                    else:
                        # Commit apenas se não houve erro na transação deste deputado
                        conn.commit()
                        total_inseridos += inseridos_dep
                        logging.info(f"Deputado {dep_id}: {inseridos_dep} despesas importadas.")
                        continue
                    
                    # Se chegou aqui, houve break por erro - já fez rollback
                    logging.warning(f"Deputado {dep_id}: importação interrompida devido a erro.")
        except Exception as e:
            logging.error(f"Erro ao processar deputado {dep_id}: {e}")
            conn.rollback()
            continue
    
    logging.info(f"Importação de despesas da Câmara concluída. {total_inseridos} registros inseridos.")
    return total_inseridos > 0


# ============================================================
# IMPORTAÇÃO DE DESPESAS - SENADO
# ============================================================

def import_despesas_senado(conn) -> bool:
    """
    Lê os JSONs de despesas CEAPS em backend/data/senado/despesas/{ano}.json
    e insere/atualiza os dados na tabela senado.despesa_ceaps.
    
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
    despesas_dir = os.path.join(DATA_DIR, "senado", "despesas")
    if not os.path.isdir(despesas_dir):
        logging.warning(f"Diretório de despesas do senado não encontrado: {despesas_dir}")
        return False
    
    total_inseridos = 0
    
    for fname in sorted(os.listdir(despesas_dir)):
        if not fname.endswith(".json"):
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
            continue
        
        inseridos_arquivo = 0
        
        try:
            with conn.cursor() as cursor:
                # Pré-carrega os códigos de senadores existentes para evitar FK violations
                cursor.execute("SELECT codigo FROM senado.parlamentar")
                senadores_existentes = {row[0] for row in cursor.fetchall()}
                
                for despesa in despesas_lista:
                    try:
                        cod_senador = despesa.get("codigoParlamentar") or despesa.get("codSenador")
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
                                # Commit parcial para garantir que o senador esteja visível
                                conn.commit()
                                # Atualiza o cache local
                                senadores_existentes.add(cod_senador)
                                logging.info(f"Senador {cod_senador} cadastrado com sucesso via API.")
                            else:
                                logging.warning(
                                    f"Senador {cod_senador} não encontrado na API. "
                                    f"Pulando despesa (ano={despesa.get('ano')}, doc={despesa.get('documento')})"
                                )
                                continue

                        
                        cursor.execute("""
                            INSERT INTO senado.despesa_ceaps
                                (ano, mes, cod_senador, nome_senador, tipo_despesa,
                                 cpf_cnpj, fornecedor, documento, data_despesa,
                                 detalhamento, valor_reembolsado, tipo_documento)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT DO NOTHING
                        """, (
                            despesa.get("ano"),
                            despesa.get("mes"),
                            cod_senador,
                            despesa.get("nomeParlamentar", ""),
                            despesa.get("tipoDespesa", ""),
                            despesa.get("cpfCnpj"),
                            despesa.get("fornecedor", ""),
                            despesa.get("documento"),
                            despesa.get("dataDespesa"),
                            despesa.get("detalhamento"),
                            despesa.get("valorReembolsado", 0),
                            despesa.get("tipoDocumento")
                        ))
                        if cursor.rowcount > 0:
                            inseridos_arquivo += 1
                    except Exception as e:
                        logging.error(f"Erro ao inserir despesa do senado (ano={despesa.get('ano')}, doc={despesa.get('documento')}): {e}")
                        conn.rollback()
                        break
                else:
                    # Commit apenas se não houve erro
                    conn.commit()
                    total_inseridos += inseridos_arquivo
                    logging.info(f"Arquivo {fname}: {inseridos_arquivo} despesas importadas.")
                    continue
                
                # Se chegou aqui, houve break por erro - já fez rollback
                logging.warning(f"Arquivo {fname}: importação interrompida devido a erro.")
        except Exception as e:
            logging.error(f"Erro ao processar arquivo {fname}: {e}")
            conn.rollback()
            continue
    
    logging.info(f"Importação de despesas do Senado concluída. {total_inseridos} registros inseridos.")
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
        # Remove pontos (separador de milhar) e troca vírgula por ponto
        return float(valor.replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        logging.warning(f"Não foi possível converter valor '{valor}' para número.")
        return 0.0


def import_emendas(conn) -> bool:
    """
    Lê os JSONs de emendas em backend/data/portal/emendas/
    e insere/atualiza os dados na tabela portal.emendas.
    
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
    emendas_dir = os.path.join(DATA_DIR, "portal", "emendas")
    if not os.path.isdir(emendas_dir):
        logging.warning(f"Diretório de emendas não encontrado: {emendas_dir}")
        return False
    
    total_inseridos = 0
    
    with conn.cursor() as cursor:
        for fname in sorted(os.listdir(emendas_dir)):
            if not fname.endswith(".json"):
                continue
            
            filepath = os.path.join(emendas_dir, fname)
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            emendas_lista = data.get("emendas", [])
            if not emendas_lista:
                continue
            
            inseridos_arquivo = 0
            
            for emenda in emendas_lista:
                try:
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
                        emenda.get("ano"),  # Corrigido: a chave no JSON é "ano", não "anoEmenda"
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
                    conn.rollback()
                    break
            else:
                conn.commit()
                total_inseridos += inseridos_arquivo
                logging.info(f"Arquivo {fname}: {inseridos_arquivo} emendas importadas.")
                continue
            
            # Se chegou aqui, houve break por erro
            logging.warning(f"Arquivo {fname}: importação interrompida devido a erro.")
    
    logging.info(f"Importação de emendas concluída. {total_inseridos} registros inseridos.")
    return total_inseridos > 0


# ============================================================
# FUNÇÃO PRINCIPAL DE IMPORTAÇÃO
# ============================================================

def import_all_data(conn) -> bool:
    """
    Importa dados da Câmara e Senado a partir dos JSONs baixados.
    Retorna True se algum dado foi importado.
    """
    imported = False

    if import_deputados_camara(conn):
        imported = True
    if import_senadores_senado(conn):
        imported = True
    if import_despesas_camara(conn):
        imported = True
    if import_despesas_senado(conn):
        imported = True
    if import_emendas(conn):
        imported = True

    if not imported:
        logging.warning("Nenhum dado foi importado. Verifique se os arquivos JSON existem em backend/data/.")

    return imported


def main():
    """Executa a importação diretamente (para testes)."""
    conn = None
    try:
        conn = db.get_db_connection()
        import_all_data(conn)
    except Exception as e:
        logging.error(f"Erro na importação: {e}")
        raise
    finally:
        if conn:
            db.release_db_connection(conn)


if __name__ == "__main__":
    main()
