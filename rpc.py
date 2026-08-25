import time

from gtk_compat import GLib

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


class RpcMixin:
    def _ensure_rpc_update_timer(self):
        if self.rpc_update_timer_id is None:
            self.rpc_update_timer_id = GLib.timeout_add(2000, self.tick_rpc_update)

    def _stop_rpc_update_timer(self):
        if self.rpc_update_timer_id is None:
            return
        try:
            GLib.source_remove(self.rpc_update_timer_id)
        except Exception:
            pass
        self.rpc_update_timer_id = None

    def init_rpc(self):
        if not RPC_AVAILABLE:
            return False
        try:
            self.rpc = Presence(RPC_CLIENT_ID)
            self.rpc.connect()
            self.rpc_last_update = 0
            return True
        except Exception:
            self.rpc = None
            self.rpc_next_retry = time.time() + 30
            return False

    def shutdown_rpc(self):
        self._stop_rpc_update_timer()
        if not self.rpc:
            return
        try:
            self.rpc.close()
        except Exception:
            pass
        finally:
            self.rpc = None

    def tick_rpc_update(self):
        if not self.settings.get("enable_rpc"):
            self.rpc_update_timer_id = None
            return False

        now = time.time()
        if not self.rpc:
            if RPC_AVAILABLE and now >= self.rpc_next_retry:
                self.init_rpc()
            return True

        if now - self.rpc_last_update < 10:
            return True
        self.rpc_last_update = now
        try:
            self.rpc.update(
                state="Playing Fleshfetch",
                details="Clicking the flesh",
                large_image="flesh",
                large_text=self.current_game_title,
                start=self.start_time,
            )
        except Exception:
            self.rpc = None
            self.rpc_next_retry = now + 30
        return True
