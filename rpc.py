# ---------- OPTIONAL DISCORD RPC ----------
try:
    from pypresence import Presence
    RPC_AVAILABLE = True
except Exception:
    Presence = None
    RPC_AVAILABLE = False

APP_ID = "dev.xtexecute.fleshfetch"
RPC_CLIENT_ID = "1499450242091716659"
DEFAULT_GAME_TITLE = "Flesh Clicker"
