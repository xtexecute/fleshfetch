import asyncio
from contextlib import suppress
import threading
import time

import runtime_scheduler as GLib

# ---------- OPTIONAL DISCORD RPC ----------
try:
    from pypresence import Presence
    RPC_AVAILABLE = True
except Exception:
    Presence = None
    RPC_AVAILABLE = False

try:
    from pypresence import AioPresence
    from pypresence.utils import get_ipc_path
except ImportError:
    AioPresence = None

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
                state="Playing fleshfetch",
                details="Clicking the flesh",
                large_image="flesh",
                large_text=self.current_game_title,
                start=self.start_time,
            )
        except Exception:
            self.rpc = None
            self.rpc_next_retry = now + 30
        return True


class _PresenceWorker:
    def __init__(self, title, start_time):
        self.title = title
        self.start_time = start_time
        self.stopped = threading.Event()
        threading.Thread(target=self._run, name="discord-presence", daemon=True).start()

    def _run(self):
        while not self.stopped.is_set():
            try:
                if get_ipc_path() and not self.stopped.is_set():
                    self._run_session()
            except Exception:
                pass
            self.stopped.wait(30)

    def _run_session(self):
        loop = asyncio.new_event_loop()
        client = None
        try:
            client = AioPresence(RPC_CLIENT_ID, loop=loop)
            loop.run_until_complete(asyncio.wait_for(client.connect(), 4))
            while not self.stopped.is_set():
                activity = client.update(
                    state="Playing fleshfetch",
                    details="Clicking the flesh",
                    large_image="flesh",
                    large_text=self.title,
                    start=self.start_time,
                )
                loop.run_until_complete(asyncio.wait_for(activity, 4))
                self.stopped.wait(10)
        finally:
            if client is not None:
                with suppress(Exception):
                    client.close()
            if not loop.is_closed():
                loop.close()


class ThreadedRpcMixin(RpcMixin):
    def init_rpc(self):
        if AioPresence is None:
            return False
        worker = getattr(self, "_presence_worker", None)
        if worker is None:
            self._presence_worker = _PresenceWorker(self.current_game_title, self.start_time)
        return True

    def shutdown_rpc(self):
        self._stop_rpc_update_timer()
        self._stop_presence_worker()

    def _stop_presence_worker(self):
        worker = getattr(self, "_presence_worker", None)
        if worker is not None:
            worker.stopped.set()
            self._presence_worker = None

    def tick_rpc_update(self):
        if not self.settings.get("enable_rpc"):
            self.rpc_update_timer_id = None
            self._stop_presence_worker()
            return False
        worker = getattr(self, "_presence_worker", None)
        if worker is not None:
            worker.title = self.current_game_title
        return True
