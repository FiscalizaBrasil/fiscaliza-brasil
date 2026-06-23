import os
import json
import time
import threading

from .config import DATA_DIR

VERIFICATION_FILE = os.path.join(DATA_DIR, "verified.json")
VERIFICATION_TTL = 7200

_lock = threading.Lock()


def _load():
    if os.path.isfile(VERIFICATION_FILE):
        with open(VERIFICATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(data):
    os.makedirs(os.path.dirname(VERIFICATION_FILE), exist_ok=True)
    with open(VERIFICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_verified(source, key):
    with _lock:
        data = _load()
        entry = data.get(source, {}).get(str(key))
        if entry:
            age = time.time() - entry.get("verified_at", 0)
            if age < VERIFICATION_TTL:
                return True
    return False


def mark_verified(source, key, json_count, db_count):
    with _lock:
        data = _load()
        data.setdefault(source, {})[str(key)] = {
            "verified_at": time.time(),
            "json_count": json_count,
            "db_count": db_count,
        }
        _save(data)


def invalidate(source=None):
    with _lock:
        if source is None:
            if os.path.isfile(VERIFICATION_FILE):
                os.remove(VERIFICATION_FILE)
        else:
            data = _load()
            if source in data:
                del data[source]
                _save(data)


def clean_expired():
    with _lock:
        data = _load()
        now = time.time()
        changed = False
        for source_key in list(data.keys()):
            src = data[source_key]
            expired = [
                k for k, v in src.items()
                if now - v.get("verified_at", 0) >= VERIFICATION_TTL
            ]
            for k in expired:
                del src[k]
                changed = True
            if not src:
                del data[source_key]
                changed = True
        if changed:
            _save(data)
