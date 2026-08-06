import sys
from collections import deque

# ---------- CONSOLE CAPTURE ----------
# Intercept stdout and stderr so we can show them in the in-game Console tab.
# The original streams are preserved so output still goes to the terminal too.

CONSOLE_HISTORY_MAX_CHUNKS = 2000
CONSOLE_FLUSH_INTERVAL_MS = 50
CONSOLE_MAX_BUFFER_CHARS = 1_000_000


class _TeeStream:
    """Writes to both the original stream and a shared log buffer."""
    def __init__(self, original):
        self._original = original
        self._history = deque(maxlen=CONSOLE_HISTORY_MAX_CHUNKS)
        self._callbacks = []  # list of callables notified on each write

    def write(self, text):
        self._history.append(text)
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        for cb in self._callbacks:
            try:
                cb(text)
            except Exception:
                pass

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def fileno(self):
        try:
            return self._original.fileno()
        except Exception:
            return -1

    def isatty(self):
        try:
            return self._original.isatty()
        except Exception:
            return False

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8")

    @property
    def errors(self):
        return getattr(self._original, "errors", "replace")

_stdout_tee = _TeeStream(sys.stdout)
_stderr_tee = _TeeStream(sys.stderr)
sys.stdout = _stdout_tee
sys.stderr = _stderr_tee
