"""Show the startup animation independently while the Qt game initializes."""

from contextlib import contextmanager
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import time

from bootstrap import CONFIG_DIR


@contextmanager
def show_startup_splash():
    Path(CONFIG_DIR).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="splash-", dir=CONFIG_DIR) as directory:
        root = Path(directory)
        close_signal = root / "close"
        shown_signal = root / "shown"
        script = Path(sys.argv[0]).resolve()
        command = [sys.executable]
        if script.suffix.lower() in (".py", ".pyw"):
            command.append(str(script))
        command.extend(("--splash-only", str(close_signal), str(shown_signal)))

        process = None
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            deadline = time.monotonic() + 2
            while not shown_signal.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
        except OSError:
            pass

        def close_splash():
            try:
                close_signal.touch()
            except OSError:
                pass

        try:
            yield close_splash
        finally:
            close_splash()
            if process is not None:
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=2)


def run_splash(close_path, shown_path):
    from PySide6.QtCore import QTimer, QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from paths import find_app_asset

    logo = Path(find_app_asset("ui/xtexecute-logo-sheet.png"))
    if not logo.is_file():
        return 1

    app = QGuiApplication(sys.argv[:1])
    app.setApplicationName("fleshfetch")
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("splashLogoUrl", QUrl.fromLocalFile(str(logo)).toString())
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / "qml" / "StartupSplash.qml")))
    if not engine.rootObjects():
        return 1

    shown = False

    def mark_shown():
        nonlocal shown
        if shown:
            return
        shown = True
        try:
            Path(shown_path).touch()
        except OSError:
            pass

    engine.rootObjects()[0].frameSwapped.connect(mark_shown)
    QTimer.singleShot(400, mark_shown)

    timer = QTimer()
    timer.setInterval(50)
    timer.timeout.connect(lambda: app.quit() if os.path.exists(close_path) else None)
    timer.start()
    QTimer.singleShot(60000, app.quit)
    return app.exec()
