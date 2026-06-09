#!/usr/bin/env python
"""
Script de scraping para buscar dados das APIs públicas da Câmara e Senado.
Os dados são salvos em arquivos JSON na pasta backend/data/.
As fotos dos parlamentares são baixadas para backend/data/fotos/.
"""

import os
import json
import time
import logging
import requests
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

CACHE_DURATION_SECONDS = 3600  # 1 hora


def _is_cache_valid(filepath: str) -> bool:
    """Verifica se o arquivo existe e foi modificado há menos de CACHE_DURATION_SECONDS."""
    if not os.path.isfile(filepath):
        return False
    idade = time.time() - os.path.getmtime(filepath)
    return idade < CACHE_DURATION_SECONDS


def _save_json(data, filepath: str):
    """Salva dados em um arquivo JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logging.info(f"Dados salvos em: {filepath}")


def _download_foto(url: str, filepath: str):
    """
    Baixa uma imagem de uma URL e salva no caminho especificado.
    Pula se o arquivo já existir.
    """
    if os.path.isfile(filepath):
        return  # já existe

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            logging.warning(f"URL não retornou uma imagem: {url} -> {content_type}")
            return

        with open(filepath, "wb") as f:
            f.write(response.content)
        logging.info(f"Foto salva em: {filepath}")
    except Exception as e:
        logging.warning(f"Erro ao baixar foto {url}: {e}")


# ============================================================
# CÂMARA DOS DEPUTADOS
# ============================================================

def fetch_deputados_camara(data_dir: str = None) -> dict:
    """
    Busca a lista de deputados da API da Câmara.
    URL: https://dadosabertos.camara.leg.br/api/v2/deputados?ordem=ASC&ordenarPor=nome
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara")

    filepath = os.path.join(data_dir, "deputados.json")

    if _is_cache_valid(filepath):
        logging.info("Cache válido encontrado para deputados da Câmara. Pulando download.")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
    params = {"ordem": "ASC", "ordenarPor": "nome"}
    headers = {"accept": "application/json"}

    logging.info(f"Buscando deputados da Câmara...")
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    _save_json(data, filepath)
    return data


def download_fotos_deputados(data_dir: str = None):
    """
    Baixa as fotos de todos os deputados listados no JSON.
    Salva em: backend/data/fotos/camara/{id}.jpg
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara")

    json_path = os.path.join(data_dir, "deputados.json")
    if not os.path.isfile(json_path):
        logging.warning("Arquivo de deputados não encontrado. Execute fetch_deputados_camara primeiro.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    dados = data.get("dados", [])
    fotos_dir = os.path.join(DATA_DIR, "fotos", "camara")

    logging.info(f"Baixando fotos de {len(dados)} deputados...")
    for dep in dados:
        dep_id = dep["id"]
        url_foto = dep.get("urlFoto", "")
        if not url_foto:
            continue

        ext = os.path.splitext(url_foto.split("?")[0])[1] or ".jpg"
        filepath = os.path.join(fotos_dir, f"{dep_id}{ext}")
        _download_foto(url_foto, filepath)


# ============================================================
# SENADO FEDERAL
# ============================================================

def fetch_senadores_senado(data_dir: str = None) -> dict:
    """
    Busca a lista de senadores da API do Senado.
    URL: https://legis.senado.leg.br/dadosabertos/senador/lista/atual?participacao=T&v=4
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado")

    filepath = os.path.join(data_dir, "senadores.json")

    if _is_cache_valid(filepath):
        logging.info("Cache válido encontrado para senadores. Pulando download.")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    url = "https://legis.senado.leg.br/dadosabertos/senador/lista/atual"
    params = {"participacao": "T", "v": "4"}
    headers = {"accept": "application/json"}

    logging.info(f"Buscando senadores...")
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    _save_json(data, filepath)
    return data


def download_fotos_senadores(data_dir: str = None):
    """
    Baixa as fotos de todos os senadores listados no JSON.
    Salva em: backend/data/fotos/senado/{codigo}.jpg
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado")

    json_path = os.path.join(data_dir, "senadores.json")
    if not os.path.isfile(json_path):
        logging.warning("Arquivo de senadores não encontrado. Execute fetch_senadores_senado primeiro.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    parlamentares = (
        data.get("ListaParlamentarEmExercicio", {})
        .get("Parlamentares", {})
        .get("Parlamentar", [])
    )

    fotos_dir = os.path.join(DATA_DIR, "fotos", "senado")

    logging.info(f"Baixando fotos de {len(parlamentares)} senadores...")
    for par in parlamentares:
        ident = par.get("IdentificacaoParlamentar", {})
        codigo = ident.get("CodigoParlamentar", "")
        url_foto = ident.get("UrlFotoParlamentar", "")
        if not codigo or not url_foto:
            continue

        ext = os.path.splitext(url_foto.split("?")[0])[1] or ".jpg"
        filepath = os.path.join(fotos_dir, f"{codigo}{ext}")
        _download_foto(url_foto, filepath)


# ============================================================
# DESPESAS - CÂMARA DOS DEPUTADOS
# ============================================================

def fetch_despesas_deputado(deputado_id: int, anos: list = None, data_dir: str = None) -> dict:
    """
    Busca as despesas de UM deputado específico (prioritário).
    Percorre os anos informados e todas as páginas de cada ano.
    
    API: GET https://dadosabertos.camara.leg.br/api/v2/deputados/{id}/despesas
    Params: ano, itens=100, ordem=ASC, ordenarPor=ano
    
    Salva em: backend/data/camara/despesas/{deputado_id}/{ano}_pagina{p}.json
    Retorna um dict com {ano: {pagina: dados}} para referência.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")
    
    if anos is None:
        anos = list(range(2023, 2027))  # 2023 a 2026
    
    dep_dir = os.path.join(data_dir, str(deputado_id))
    os.makedirs(dep_dir, exist_ok=True)
    
    headers = {"accept": "application/json"}
    resultados = {}
    
    for ano in anos:
        pagina = 1
        total_paginas = 1
        ano_resultados = {}
        
        while pagina <= total_paginas:
            filepath = os.path.join(dep_dir, f"{ano}_pagina{pagina}.json")
            
            if _is_cache_valid(filepath):
                logging.info(f"Cache válido: {filepath}")
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                ano_resultados[pagina] = data
                # Atualiza total_paginas com base no cache
                links = data.get("links", [])
                for link in links:
                    if link.get("rel") == "last":
                        href = link.get("href", "")
                        if "pagina=" in href:
                            total_paginas = int(href.split("pagina=")[-1].split("&")[0])
                        break
                pagina += 1
                continue
            
            url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado_id}/despesas"
            params = {
                "ano": ano,
                "itens": 100,
                "ordem": "ASC",
                "ordenarPor": "ano",
                "pagina": pagina
            }
            
            logging.info(f"Buscando despesas Câmara dep={deputado_id} ano={ano} pagina={pagina}...")
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                _save_json(data, filepath)
                ano_resultados[pagina] = data
                
                # Descobrir total de páginas pelo link "last"
                links = data.get("links", [])
                for link in links:
                    if link.get("rel") == "last":
                        href = link.get("href", "")
                        if "pagina=" in href:
                            total_paginas = int(href.split("pagina=")[-1].split("&")[0])
                        break
                
                pagina += 1
                time.sleep(0.3)  # Rate limiting
            except Exception as e:
                logging.error(f"Erro ao buscar despesas dep={deputado_id} ano={ano} pag={pagina}: {e}")
                break
        
        resultados[ano] = ano_resultados
    
    return resultados


def fetch_despesas_todas_camara(data_dir: str = None):
    """
    Busca despesas de TODOS os deputados em background.
    Usa a lista de deputados já baixada e sorteia aleatoriamente
    quem ainda não foi baixado ou está desatualizado.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")
    
    # Carrega lista de deputados
    json_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if not os.path.isfile(json_path):
        logging.warning("Lista de deputados não encontrada. Execute fetch_deputados_camara primeiro.")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    dados = data.get("dados", [])
    if not dados:
        logging.warning("Nenhum deputado na lista.")
        return
    
    # Embaralha para baixar aleatoriamente
    import random
    random.shuffle(dados)
    
    anos = list(range(2023, 2027))
    
    for dep in dados:
        dep_id = dep["id"]
        dep_dir = os.path.join(data_dir, str(dep_id))
        
        # Verifica se já tem dados completos para todos os anos
        completo = True
        for ano in anos:
            # Verifica se existe pelo menos uma página para este ano
            ano_tem_dados = False
            if os.path.isdir(dep_dir):
                for fname in os.listdir(dep_dir):
                    if fname.startswith(f"{ano}_pagina") and fname.endswith(".json"):
                        ano_tem_dados = True
                        break
            if not ano_tem_dados:
                completo = False
                break
        
        if completo:
            continue  # Pula quem já está completo
        
        logging.info(f"Background: baixando despesas do deputado {dep_id} ({dep.get('nome', '')})")
        try:
            fetch_despesas_deputado(dep_id, anos=anos, data_dir=data_dir)
        except Exception as e:
            logging.error(f"Erro no background para deputado {dep_id}: {e}")
            continue


# ============================================================
# DESPESAS - SENADO FEDERAL
# ============================================================

def fetch_despesas_senado_ano(ano: int, data_dir: str = None) -> dict:
    """
    Busca as despesas CEAPS de TODOS os senadores para um ano específico.
    
    API: GET https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}
    
    Salva em: backend/data/senado/despesas/{ano}.json
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "despesas")
    
    os.makedirs(data_dir, exist_ok=True)
    filepath = os.path.join(data_dir, f"{ano}.json")
    
    if _is_cache_valid(filepath):
        logging.info(f"Cache válido: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    url = f"https://adm.senado.gov.br/adm-dadosabertos/api/v1/senadores/despesas_ceaps/{ano}"
    headers = {"accept": "application/json"}
    
    logging.info(f"Buscando despesas CEAPS do Senado para {ano}...")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        _save_json(data, filepath)
        return data
    except Exception as e:
        logging.error(f"Erro ao buscar despesas CEAPS {ano}: {e}")
        return {}


def fetch_despesas_senado_todas(data_dir: str = None):
    """
    Busca despesas CEAPS para todos os anos disponíveis.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "despesas")
    
    anos = list(range(2023, 2027))
    for ano in anos:
        fetch_despesas_senado_ano(ano, data_dir=data_dir)
        time.sleep(0.5)


# ============================================================
# EMENDAS - PORTAL DA TRANSPARÊNCIA
# ============================================================

def fetch_emendas_parlamentar(nome_autor: str, pagina: int = 1, data_dir: str = None) -> dict:
    """
    Busca emendas de um parlamentar pelo nome (maiúsculo) no Portal da Transparência.
    
    API: GET https://api.portaldatransparencia.gov.br/api-de-dados/emendas
    Params: nomeAutor=NOME, pagina=1
    Header: chave-api-dados: {API_KEY}
    
    Salva em: backend/data/portal/emendas/{nome_autor_sanitizado}_pagina{p}.json
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "portal", "emendas")
    
    os.makedirs(data_dir, exist_ok=True)
    
    # Sanitiza o nome para usar como nome de arquivo
    nome_sanitizado = nome_autor.replace(" ", "_").replace("/", "_").upper()
    filepath = os.path.join(data_dir, f"{nome_sanitizado}_pagina{pagina}.json")
    
    if _is_cache_valid(filepath):
        logging.info(f"Cache válido: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    
    api_key = os.environ.get("API_KEY", "")
    if not api_key:
        logging.warning("API_KEY não configurada. Defina a variável de ambiente API_KEY.")
        return {"emendas": []}
    
    url = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    params = {"nomeAutor": nome_autor.upper(), "pagina": pagina}
    headers = {"accept": "*/*", "chave-api-dados": api_key}
    
    logging.info(f"Buscando emendas de {nome_autor.upper()} (página {pagina})...")
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # A API retorna uma lista diretamente
        result = {"emendas": data if isinstance(data, list) else []}
        
        _save_json(result, filepath)
        time.sleep(0.5)  # Rate limit para o Portal da Transparência
        return result
    except Exception as e:
        logging.error(f"Erro ao buscar emendas de {nome_autor}: {e}")
        return {"emendas": []}


def fetch_emendas_todas(data_dir: str = None):
    """
    Busca emendas de TODOS os deputados e senadores.
    Usa os nomes dos parlamentares já baixados.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "portal", "emendas")
    
    # Carrega lista de deputados
    nomes_parlamentares = set()
    
    # Deputados
    dep_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if os.path.isfile(dep_path):
        with open(dep_path, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
        for dep in dep_data.get("dados", []):
            nome = dep.get("nome", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)
    
    # Senadores
    sen_path = os.path.join(DATA_DIR, "senado", "senadores.json")
    if os.path.isfile(sen_path):
        with open(sen_path, "r", encoding="utf-8") as f:
            sen_data = json.load(f)
        parlamentares = (
            sen_data.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        for par in parlamentares:
            ident = par.get("IdentificacaoParlamentar", {})
            nome = ident.get("NomeParlamentar", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)
    
    logging.info(f"Buscando emendas para {len(nomes_parlamentares)} parlamentares...")
    
    for nome in sorted(nomes_parlamentares):
        # Verifica se já tem dados completos (página 1 existe)
        nome_sanitizado = nome.replace(" ", "_").replace("/", "_")
        pagina1_path = os.path.join(data_dir, f"{nome_sanitizado}_pagina1.json")
        
        if os.path.isfile(pagina1_path) and _is_cache_valid(pagina1_path):
            continue  # Pula quem já está em cache
        
        logging.info(f"Emendas: buscando dados de {nome}")
        pagina = 1
        while True:
            result = fetch_emendas_parlamentar(nome, pagina=pagina, data_dir=data_dir)
            emendas = result.get("emendas", [])
            if not emendas:
                break
            pagina += 1
            if pagina > 50:  # Limite de segurança
                break


# ============================================================
# BACKGROUND SCRAPER
# ============================================================

import threading

# Importa funções de banco para importar dados após download
try:
    from database import db
    from scripts.import_data import import_despesas_camara, import_despesas_senado, import_emendas
except ImportError:
    db = None
    import_despesas_camara = None
    import_despesas_senado = None
    import_emendas = None

_background_thread = None
_stop_background = False

# Variáveis de status do scraping (acessíveis via import)
scraping_status = {
    "em_andamento": False,
    "camara_pendentes": 0,
    "senado_pendentes": 0,
    "camara_completa": False,
    "senado_completo": False,
}


def _get_deputados_pendentes(data_dir: str = None) -> list:
    """
    Retorna lista de deputados que ainda não têm despesas completas baixadas.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "camara", "despesas")
    
    json_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if not os.path.isfile(json_path):
        return []
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    dados = data.get("dados", [])
    if not dados:
        return []
    
    anos = list(range(2023, 2027))
    pendentes = []
    
    for dep in dados:
        dep_id = dep["id"]
        dep_dir = os.path.join(data_dir, str(dep_id))
        
        completo = True
        for ano in anos:
            ano_tem_dados = False
            if os.path.isdir(dep_dir):
                for fname in os.listdir(dep_dir):
                    if fname.startswith(f"{ano}_pagina") and fname.endswith(".json"):
                        ano_tem_dados = True
                        break
            if not ano_tem_dados:
                completo = False
                break
        
        if not completo:
            pendentes.append(dep)
    
    return pendentes


def _get_anos_senado_pendentes(data_dir: str = None) -> list:
    """
    Retorna lista de anos do Senado que ainda não foram baixados.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "senado", "despesas")
    
    anos = list(range(2023, 2027))
    pendentes = []
    
    for ano in anos:
        filepath = os.path.join(data_dir, f"{ano}.json")
        if not os.path.isfile(filepath):
            pendentes.append(ano)
    
    return pendentes


def _processar_deputado(dep):
    """Processa um deputado: baixa despesas e importa para o banco."""
    dep_id = dep["id"]
    logging.info(f"Background Câmara: baixando despesas do deputado {dep_id} ({dep.get('nome', '')})")
    try:
        anos = list(range(2023, 2027))
        fetch_despesas_deputado(dep_id, anos=anos)
        
        if import_despesas_camara is not None:
            conn = db.get_db_connection()
            if conn:
                try:
                    import_despesas_camara(conn)
                    logging.info(f"Background Câmara: despesas do deputado {dep_id} importadas.")
                finally:
                    db.release_db_connection(conn)
        return f"deputado {dep_id} OK"
    except Exception as e:
        logging.error(f"Background Câmara: erro no deputado {dep_id}: {e}")
        return f"deputado {dep_id} ERRO: {e}"


def _processar_ano_senado(ano):
    """Processa um ano do Senado: baixa despesas e importa para o banco."""
    logging.info(f"Background Senado: baixando despesas CEAPS de {ano}")
    try:
        fetch_despesas_senado_ano(ano)
        
        if import_despesas_senado is not None:
            conn = db.get_db_connection()
            if conn:
                try:
                    import_despesas_senado(conn)
                    logging.info(f"Background Senado: despesas de {ano} importadas.")
                finally:
                    db.release_db_connection(conn)
        return f"senado {ano} OK"
    except Exception as e:
        logging.error(f"Background Senado: erro no ano {ano}: {e}")
        return f"senado {ano} ERRO: {e}"


def _processar_emendas_parlamentar(nome):
    """Processa emendas de um parlamentar: baixa e importa."""
    logging.info(f"Background Emendas: buscando dados de {nome}")
    try:
        pagina = 1
        while True:
            result = fetch_emendas_parlamentar(nome, pagina=pagina)
            emendas = result.get("emendas", [])
            if not emendas:
                break
            pagina += 1
            if pagina > 50:
                break
        
        if import_emendas is not None:
            conn = db.get_db_connection()
            if conn:
                try:
                    import_emendas(conn)
                    logging.info(f"Background Emendas: dados de {nome} importados.")
                finally:
                    db.release_db_connection(conn)
        return f"emendas {nome} OK"
    except Exception as e:
        logging.error(f"Background Emendas: erro em {nome}: {e}")
        return f"emendas {nome} ERRO: {e}"


def _get_parlamentares_sem_emendas(data_dir: str = None) -> list:
    """
    Retorna lista de nomes de parlamentares que ainda não têm emendas baixadas.
    """
    if data_dir is None:
        data_dir = os.path.join(DATA_DIR, "portal", "emendas")
    
    nomes_parlamentares = set()
    
    # Deputados
    dep_path = os.path.join(DATA_DIR, "camara", "deputados.json")
    if os.path.isfile(dep_path):
        with open(dep_path, "r", encoding="utf-8") as f:
            dep_data = json.load(f)
        for dep in dep_data.get("dados", []):
            nome = dep.get("nome", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)
    
    # Senadores
    sen_path = os.path.join(DATA_DIR, "senado", "senadores.json")
    if os.path.isfile(sen_path):
        with open(sen_path, "r", encoding="utf-8") as f:
            sen_data = json.load(f)
        parlamentares = (
            sen_data.get("ListaParlamentarEmExercicio", {})
            .get("Parlamentares", {})
            .get("Parlamentar", [])
        )
        for par in parlamentares:
            ident = par.get("IdentificacaoParlamentar", {})
            nome = ident.get("NomeParlamentar", "").strip().upper()
            if nome:
                nomes_parlamentares.add(nome)
    
    # Filtra apenas quem ainda não tem cache
    sem_emendas = []
    for nome in nomes_parlamentares:
        nome_sanitizado = nome.replace(" ", "_").replace("/", "_")
        pagina1_path = os.path.join(data_dir, f"{nome_sanitizado}_pagina1.json")
        if not os.path.isfile(pagina1_path) or not _is_cache_valid(pagina1_path):
            sem_emendas.append(nome)
    
    return sem_emendas


def _background_worker():
    """
    Worker que roda em background baixando dados em paralelo usando ThreadPoolExecutor.
    Câmara, Senado e Emendas rodam simultaneamente em threads separadas.
    """
    global _stop_background, scraping_status
    logging.info("Background scraper iniciado (paralelo: Câmara + Senado + Emendas).")
    
    while not _stop_background:
        try:
            # Obtém listas de pendentes
            deputados_pendentes = _get_deputados_pendentes()
            anos_senado_pendentes = _get_anos_senado_pendentes()
            parlamentares_sem_emendas = _get_parlamentares_sem_emendas()
            
            camara_completa = len(deputados_pendentes) == 0
            senado_completo = len(anos_senado_pendentes) == 0
            emendas_completa = len(parlamentares_sem_emendas) == 0
            
            # Atualiza status global
            scraping_status["em_andamento"] = not (camara_completa and senado_completo and emendas_completa)
            scraping_status["camara_pendentes"] = len(deputados_pendentes)
            scraping_status["senado_pendentes"] = len(anos_senado_pendentes)
            scraping_status["camara_completa"] = camara_completa
            scraping_status["senado_completo"] = senado_completo
            
            if camara_completa and senado_completa and emendas_completa:
                # Tudo baixado. Aguarda 1 hora antes de verificar novamente
                logging.info("Background: todos os dados baixados. Aguardando 1 hora...")
                for _ in range(3600):
                    if _stop_background:
                        break
                    time.sleep(1)
                continue
            
            # Embaralha para baixar aleatoriamente
            random.shuffle(deputados_pendentes)
            random.shuffle(anos_senado_pendentes)
            random.shuffle(parlamentares_sem_emendas)
            
            # Prepara tarefas para o pool de threads
            tarefas = []
            
            # Pega até 2 deputados da Câmara
            for dep in deputados_pendentes[:2]:
                tarefas.append(("camara", dep))
            
            # Pega até 2 anos do Senado
            for ano in anos_senado_pendentes[:2]:
                tarefas.append(("senado", ano))
            
            # Pega até 3 parlamentares para emendas
            for nome in parlamentares_sem_emendas[:3]:
                tarefas.append(("emendas", nome))
            
            if not tarefas:
                time.sleep(5)
                continue
            
            logging.info(f"Background: processando {len(tarefas)} tarefas em paralelo...")
            
            # Executa tarefas em paralelo com ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for tipo, item in tarefas:
                    if tipo == "camara":
                        future = executor.submit(_processar_deputado, item)
                    elif tipo == "senado":
                        future = executor.submit(_processar_ano_senado, item)
                    elif tipo == "emendas":
                        future = executor.submit(_processar_emendas_parlamentar, item)
                    futures[future] = (tipo, item)
                
                for future in as_completed(futures):
                    tipo, item = futures[future]
                    try:
                        result = future.result(timeout=120)
                        logging.info(f"Background: tarefa concluída - {result}")
                    except Exception as e:
                        logging.error(f"Background: tarefa {tipo} falhou: {e}")
            
            # Pequena pausa entre ciclos
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"Erro no background scraper: {e}")
            time.sleep(60)



def start_background_scraper():
    """Inicia o scraper em background (thread daemon)."""
    global _background_thread
    if _background_thread and _background_thread.is_alive():
        logging.info("Background scraper já está rodando.")
        return
    
    _background_thread = threading.Thread(target=_background_worker, daemon=True)
    _background_thread.start()
    logging.info("Background scraper iniciado em thread separada.")


def stop_background_scraper():
    """Sinaliza para o background scraper parar."""
    global _stop_background
    _stop_background = True
    logging.info("Background scraper sinalizado para parar.")


# ============================================================
# FUNÇÕES DE BACKGROUND (Fotos e dados iniciais)
# ============================================================

def _background_fotos_camara():
    """Baixa fotos dos deputados em background."""
    try:
        logging.info("Background: baixando fotos dos deputados...")
        fetch_deputados_camara()
        download_fotos_deputados()
        logging.info("Background: fotos dos deputados concluído.")
    except Exception as e:
        logging.error(f"Background: erro ao baixar fotos dos deputados: {e}")


def _background_fotos_senado():
    """Baixa fotos dos senadores em background."""
    try:
        logging.info("Background: baixando fotos dos senadores...")
        fetch_senadores_senado()
        download_fotos_senadores()
        logging.info("Background: fotos dos senadores concluído.")
    except Exception as e:
        logging.error(f"Background: erro ao baixar fotos dos senadores: {e}")


def start_background_fotos():
    """Dispara o download de fotos em threads separadas (não bloqueante)."""
    threading.Thread(target=_background_fotos_camara, daemon=True).start()
    threading.Thread(target=_background_fotos_senado, daemon=True).start()
    logging.info("Download de fotos iniciado em background.")


# ============================================================
# MAIN (para execução direta via CLI)
# ============================================================

def main():
    """Executa os fetches de dados e download de fotos em background."""
    logging.info("Iniciando scraping de dados em background...")

    # Tudo em background para não bloquear
    start_background_fotos()
    start_background_scraper()

    logging.info("Scraping inicial concluído. Background scraper rodando...")


if __name__ == "__main__":
    main()
