"""Nonblocking access to the existing leaderboard service."""

import threading
from PySide6.QtCore import QObject, Property, Signal, Slot, Qt
from leaderboard import (fetch_leaderboard_entries, submit_leaderboard_entry,
                         get_default_username, _leaderboard_configured)


class LeaderboardController(QObject):
    changed = Signal()
    finished = Signal(object)

    def __init__(self, game):
        super().__init__(game)
        self.game, self._closed = game, False
        self._state = {"rows": [], "busy": False, "message": "", "username": get_default_username(),
                       "configured": _leaderboard_configured()}
        self.finished.connect(self._finish, Qt.ConnectionType.QueuedConnection)

    @Property("QVariantMap", notify=changed)
    def state(self):
        return dict(self._state)

    def _start(self, job):
        if self._closed or self._state["busy"]:
            return
        if not self._state["configured"]:
            self._state["message"] = "Leaderboard unavailable: server settings are not configured."
            self.changed.emit()
            return
        self._state.update(busy=True, message="")
        self.changed.emit()
        def run():
            try:
                result = job()
            except Exception as exc:
                result = {"message": f"Leaderboard request failed: {exc}"}
            if not self._closed:
                self.finished.emit(result)
        threading.Thread(target=run, daemon=True, name="leaderboard-request").start()

    @Slot(object)
    def _finish(self, result):
        if not self._closed:
            self._state.update(result, busy=False)
            self.changed.emit()

    @Slot()
    def refresh(self):
        def job():
            ok, error, rows = fetch_leaderboard_entries()
            return {"rows": rows, "message": "" if ok else f"Could not load leaderboard: {error}"}
        self._start(job)

    @Slot(str)
    def submit(self, username):
        username = username.strip()[:64]
        if not username:
            self._state["message"] = "Enter a player name."
            self.changed.emit()
            return
        amount = int(self.game.get_currency("flesh"))
        def job():
            ok, info = submit_leaderboard_entry(username, amount)
            if not ok:
                return {"message": f"Could not submit score: {info}"}
            loaded, error, rows = fetch_leaderboard_entries()
            result = {"message": f"Submitted {amount:,} flesh as {username}."}
            if loaded:
                result["rows"] = rows
            return result
        self._start(job)

    def close(self):
        self._closed = True
