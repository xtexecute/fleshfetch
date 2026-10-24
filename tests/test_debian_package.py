import hashlib
from pathlib import Path
import tempfile
import unittest

from build_debian import DEPENDENCIES, stage_package


class DebianPackageTests(unittest.TestCase):
    def test_payload_permissions_dependencies_and_checksums(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "root"
            stage_package(root)
            control = (root / "DEBIAN/control").read_text()
            self.assertIn("Architecture: all\n", control)
            self.assertIn("Version: 1.4.0-1\n", control)
            for dependency in DEPENDENCIES:
                self.assertIn(dependency, control)
            app = root / "usr/share/fleshfetch"
            for name in ("main.py", "qt_frontend.py", "qt_legacy_ui.py",
                         "qml/Main.qml", "assets/flesh.png", "assets/click.wav",
                         "assets/ui/red-frame.png"):
                self.assertTrue((app / name).is_file(), name)
            self.assertFalse((app / "build_debian.py").exists())
            self.assertFalse((app / "fleshfetch_nonmodular_OLD.py").exists())
            launcher = root / "usr/bin/fleshfetch"
            self.assertIn(b'/usr/share/fleshfetch/main.py "$@"', launcher.read_bytes())
            self.assertNotIn(b'\r', launcher.read_bytes())
            self.assertTrue(launcher.stat().st_mode & 0o111)
            self.assertFalse((app / "settings.json").exists())
            for line in (root / "DEBIAN/md5sums").read_text().splitlines():
                digest, name = line.split("  ", 1)
                self.assertEqual(digest, hashlib.md5(
                    (root / name).read_bytes(), usedforsecurity=False).hexdigest())


if __name__ == "__main__":
    unittest.main()
