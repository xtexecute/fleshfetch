import os

import requests

# ---------- LEADERBOARD / SUPABASE HELPERS ----------

SUPABASE_URL               = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY               = os.environ.get("SUPABASE_KEY", "")
SUPABASE_LEADERBOARD_TABLE = os.environ.get("SUPABASE_LEADERBOARD_TABLE", "leaderboard")


def get_default_username() -> str:
    try:
        return os.getlogin()
    except Exception:
        pass
    if os.name == "nt":
        name = os.environ.get("USERNAME", "")
        if name:
            return name
    home = os.path.expanduser("~")
    return os.path.basename(home.rstrip(os.sep)) or "unknown"


def _leaderboard_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def submit_leaderboard_entry(username: str, flesh_amount: int):
    if not _leaderboard_configured():
        return False, "SUPABASE_URL / SUPABASE_KEY not configured in environment"
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{SUPABASE_LEADERBOARD_TABLE}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    payload = {"username": username, "flesh_amount": int(flesh_amount)}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception as e:
        return False, f"Request error: {e}"
    if resp.status_code not in (200, 201):
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    try:
        data = resp.json()
    except Exception:
        data = {}
    return True, data


def fetch_leaderboard_entries():
    if not _leaderboard_configured():
        return False, "SUPABASE_URL / SUPABASE_KEY not configured in environment", []
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/{SUPABASE_LEADERBOARD_TABLE}?select=*&order=flesh_amount.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
    except Exception as e:
        return False, f"Request error: {e}", []
    if resp.status_code != 200:
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}", []
    try:
        rows = resp.json()
    except Exception as e:
        return False, f"JSON decode error: {e}", []
    if not isinstance(rows, list):
        return False, "Unexpected response format", []
    return True, "", rows
