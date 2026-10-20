"""Lazy GTK scheduling, or Qt scheduling when configured before startup.

Qt sources must be created and removed on the Qt event-loop thread. Configure
Qt before scheduling runtime work; existing GTK sources remain GTK sources.
"""

import itertools


_qt_backend = None


def _glib():
    from gtk_compat import GLib

    return GLib


class _QtScheduler:
    def __init__(self, qt_core):
        self.qt_core = qt_core
        self.sources = {}
        self.source_ids = itertools.count(1)

    def add(self, interval, callback, args, once=False):
        if not callable(callback):
            raise TypeError("callback must be callable")
        timer = self.qt_core.QTimer()
        timer.setTimerType(self.qt_core.Qt.TimerType.PreciseTimer)
        timer.setSingleShot(once)
        source_id = next(self.source_ids)

        def dispatch():
            if source_id not in self.sources:
                return
            keep = False
            try:
                keep = bool(callback(*args)) and not once
            finally:
                if not keep:
                    self.remove(source_id)

        timer.timeout.connect(dispatch)
        self.sources[source_id] = timer
        timer.start(max(0, int(interval)))
        return source_id

    def remove(self, source_id):
        timer = self.sources.pop(source_id, None)
        if timer is None:
            return False
        timer.stop()
        timer.deleteLater()
        return True


def configure_qt(qt_core=None):
    """Install QTimer scheduling; call on the Qt thread before runtime startup.

    The optional QtCore module allows callers to supply their Qt binding.
    Otherwise PySide6 is imported here, never when this module is imported.
    Repeated calls preserve all active Qt sources.
    """
    global _qt_backend
    if _qt_backend is None:
        if qt_core is None:
            from PySide6 import QtCore as qt_core
        _qt_backend = _QtScheduler(qt_core)


def timeout_add(interval, function, *user_data, priority=None):
    if _qt_backend is not None:
        return _qt_backend.add(interval, function, user_data)
    kwargs = {} if priority is None else {"priority": priority}
    return _glib().timeout_add(interval, function, *user_data, **kwargs)


def timeout_add_seconds(interval, function, *user_data, priority=None):
    if _qt_backend is not None:
        return _qt_backend.add(interval * 1000, function, user_data)
    kwargs = {} if priority is None else {"priority": priority}
    return _glib().timeout_add_seconds(interval, function, *user_data, **kwargs)


def idle_add(function, *user_data, priority=None):
    if _qt_backend is not None:
        return _qt_backend.add(0, function, user_data, once=True)
    kwargs = {} if priority is None else {"priority": priority}
    return _glib().idle_add(function, *user_data, **kwargs)


def source_remove(source_id):
    if _qt_backend is not None:
        return _qt_backend.remove(source_id)
    return _glib().source_remove(source_id)
