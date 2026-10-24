"""Check a .deb's archived metadata and smoke-test its extracted Qt payload."""

import hashlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    package = ROOT / "output/fleshfetch_1.4.0-1_all.deb"
    def member(name):
        return subprocess.check_output(["ar", "p", str(package), name])
    assert member("debian-binary") == b"2.0\n"
    with tarfile.open(fileobj=io.BytesIO(member("control.tar.gz"))) as archive:
        control = archive.extractfile("./control").read().decode()
        sums = archive.extractfile("./md5sums").read().decode()
    assert "Package: fleshfetch\n" in control
    with tempfile.TemporaryDirectory(prefix="fleshfetch-deb-check-") as temp:
        temp = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(member("data.tar.gz"))) as archive:
            for info in archive.getmembers():
                assert info.uid == info.gid == 0
                if info.name == "./usr/bin/fleshfetch":
                    assert info.mode == 0o755
            archive.extractall(temp, filter="data")
        for line in sums.splitlines():
            digest, name = line.split("  ", 1)
            assert digest == hashlib.md5((temp / name).read_bytes(),
                                        usedforsecurity=False).hexdigest(), name
        app = temp / "usr/share/fleshfetch"
        env = dict(os.environ, XDG_CONFIG_HOME=str(temp / "profile"),
                   APPDATA=str(temp / "profile"), QT_QPA_PLATFORM="offscreen",
                   QT_QUICK_BACKEND="software")
        code = '''
import sys
from PySide6.QtCore import QTimer
from qt_frontend import create_application
sys.excepthook = sys.__excepthook__
app, engine, game = create_application([])
assert engine.rootObjects()
game.click()
assert game.flesh == 1
QTimer.singleShot(150, app.quit)
app.exec()
for window in engine.rootObjects():
    window.close()
app.processEvents()
print('Extracted Debian payload opened its Qt window, clicked and saved.')
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=app, env=env,
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        print(result.stdout.strip())
    print("Debian archive structure, ownership, permissions and checksums passed.")


if __name__ == "__main__":
    main()
