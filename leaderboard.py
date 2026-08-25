import os

import requests

from gtk_compat import Gtk

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


class LeaderboardMixin:
    def build_leaderboard_page(self):
        self.leaderboard_page.set_margin_top(4)
        self.leaderboard_page.set_margin_bottom(4)
        self.leaderboard_page.set_margin_start(4)
        self.leaderboard_page.set_margin_end(4)

        outer    = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        outer.append(controls)
        self.leaderboard_page.append(outer)

        refresh_btn = Gtk.Button(label="Refresh leaderboard")
        refresh_btn.connect("clicked", self.on_refresh_leaderboard_clicked)
        controls.append(refresh_btn)

        self.leaderboard_info_label = Gtk.Label(label="", xalign=0)
        outer.append(self.leaderboard_info_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        outer.append(scrolled)

        self.leaderboard_textview = Gtk.TextView()
        self.leaderboard_textview.set_editable(False)
        try:
            self.leaderboard_textview.set_monospace(True)
        except Exception:
            pass
        scrolled.set_child(self.leaderboard_textview)
        self.load_leaderboard()

    def update_leaderboard_view(self, rows):
        buffer = self.leaderboard_textview.get_buffer()
        if not rows:
            buffer.set_text("No leaderboard entries yet.", -1)
            return
        header    = f"{'Username':<20} {'Flesh':>10}  {'Timestamp':<32}\n"
        separator = "-" * 64 + "\n"
        lines     = [header, separator]
        for row in rows:
            username = str(row.get("username") or "?")
            flesh    = row.get("flesh_amount") or row.get("flesh")
            try:
                flesh_str = str(int(flesh))
            except Exception:
                flesh_str = str(flesh)
            ts = row.get("last_update") or row.get("created_at") or ""
            lines.append(f"{username:<20} {flesh_str:>10}  {ts:<32}\n")
        buffer.set_text("".join(lines), -1)

    def load_leaderboard(self):
        if not hasattr(self, "leaderboard_textview"):
            return
        ok, err, rows = fetch_leaderboard_entries()
        if not ok:
            if hasattr(self, "leaderboard_info_label"):
                self.leaderboard_info_label.set_text(f"Error loading leaderboard: {err}")
            return
        if hasattr(self, "leaderboard_info_label"):
            self.leaderboard_info_label.set_text(f"Loaded {len(rows)} entries.")
        self.update_leaderboard_view(rows)

    def on_refresh_leaderboard_clicked(self, button):
        self.load_leaderboard()

    def on_add_leaderboard_clicked(self, button):
        username     = get_default_username()
        flesh_amount = int(self.flesh)
        ok, info = submit_leaderboard_entry(username, flesh_amount)
        if ok:
            msg = f"Submitted leaderboard entry as '{username}' with {flesh_amount} flesh."
            if hasattr(self, "leaderboard_textview"):
                self.load_leaderboard()
        else:
            msg = f"Failed to submit leaderboard entry: {info}"
        if hasattr(self, "settings_info_label"):
            self.settings_info_label.set_text(msg)
        else:
            print(msg)
