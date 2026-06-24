import os
import json
import time
import logging
import unicodedata
import requests

from .config import CACHE_DURATION_SECONDS


def is_cache_valid(filepath):
    if not os.path.isfile(filepath):
        return False
    idade = time.time() - os.path.getmtime(filepath)
    return idade < CACHE_DURATION_SECONDS


def save_json(data, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tmp = filepath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, filepath)
    logging.info(f"Dados salvos em: {filepath}")


def load_json_if_valid(filepath):
    if is_cache_valid(filepath):
        logging.info(f"Cache válido: {filepath}")
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def remover_acentos(texto):
    nfkd = unicodedata.normalize('NFKD', texto)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))


def download_foto(url, filepath):
    if os.path.isfile(filepath):
        return
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type and "image" not in content_type and "octet-stream" not in content_type:
            logging.warning(f"URL não retornou uma imagem: {url} -> {content_type}")
            return
        with open(filepath, "wb") as f:
            f.write(response.content)
        logging.info(f"Foto salva em: {filepath}")
    except Exception as e:
        logging.warning(f"Erro ao baixar foto {url}: {e}")
