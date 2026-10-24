"""Build a small Debian 13 package using distro-provided Python/Qt libraries."""

import argparse
import gzip
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent
VERSION = "1.4.0-1"
DEPENDENCIES = (
    "python3 (>= 3.10)", "python3-requests",
    "python3-pyside6.qtcore (>= 6.8)", "python3-pyside6.qtgui (>= 6.8)",
    "python3-pyside6.qtwidgets (>= 6.8)", "python3-pyside6.qtqml (>= 6.8)",
    "python3-pyside6.qtquick (>= 6.8)", "python3-pyside6.qtquickcontrols2 (>= 6.8)",
    "python3-pyside6.qtmultimedia (>= 6.8)",
    "qml6-module-qtquick", "qml6-module-qtquick-controls",
    "qml6-module-qtquick-templates", "qml6-module-qtquick-layouts",
    "qml6-module-qtquick-window", "qml6-module-qtqml-workerscript",
)
BUILD_MODULES = {
    "build_windows.py", "build_debian.py", "package_source.py",
    "restore_nuitka_payload.py", "update_reference_14.py",
}


def stage_package(stage):
    app = stage / "usr/share/fleshfetch"
    app.mkdir(parents=True)
    for module in ROOT.glob("*.py"):
        if module.name not in BUILD_MODULES and "_OLD" not in module.name:
            shutil.copyfile(module, app / module.name)
    for folder in ("qml", "assets"):
        shutil.copytree(ROOT / folder, app / folder,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("flesh.png", "click.wav", "flesh.ico"):
        shutil.copyfile(ROOT / name, app / "assets" / name)
    shutil.copyfile(ROOT / "default.conf", app / "default.conf")

    launcher = stage / "usr/bin/fleshfetch"
    launcher.parent.mkdir(parents=True)
    launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 /usr/share/fleshfetch/main.py "$@"\n',
                        encoding="utf-8")
    desktop = stage / "usr/share/applications/dev.xtexecute.fleshfetch.desktop"
    desktop.parent.mkdir(parents=True)
    desktop.write_text((ROOT / desktop.name).read_text(encoding="utf-8"), encoding="utf-8")
    icon = stage / "usr/share/icons/hicolor/256x256/apps/dev.xtexecute.fleshfetch.png"
    icon.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / icon.name, icon)
    doc = stage / "usr/share/doc/fleshfetch"
    doc.mkdir(parents=True)
    shutil.copyfile(ROOT / "LICENSE", doc / "copyright")
    (doc / "changelog.gz").write_bytes(gzip.compress(
        (ROOT / "CHANGELOG_v1.4.0.md").read_bytes(), mtime=0))

    files = sorted(path for path in stage.rglob("*") if path.is_file())
    installed_size = sum(math.ceil(path.stat().st_size / 1024) for path in files)
    control = stage / "DEBIAN"
    control.mkdir()
    (control / "control").write_text(
        f"Package: fleshfetch\nVersion: {VERSION}\nArchitecture: all\n"
        "Maintainer: xtexecute <146252866+xtexecute@users.noreply.github.com>\n"
        "Section: games\nPriority: optional\n"
        f"Installed-Size: {installed_size}\nDepends: {', '.join(DEPENDENCIES)}\n"
        "Recommends: fonts-dejavu-core\n"
        "Homepage: https://github.com/xtexecute/fleshfetch\n"
        "Description: Python clicker game and modding framework\n"
        " Qt Quick frontend with saves, upgrades and Python mod support.\n",
        encoding="utf-8")
    (control / "md5sums").write_text("".join(
        f"{hashlib.md5(path.read_bytes(), usedforsecurity=False).hexdigest()}  "
        f"{path.relative_to(stage).as_posix()}\n" for path in files), encoding="ascii")
    for path in stage.rglob("*"):
        path.chmod(0o755 if path.is_dir() or path == launcher else 0o644)
    stage.chmod(0o755)


def archive_filter(info):
    info.uid = info.gid = 0
    info.uname = info.gname = "root"
    info.mtime = 0
    return info


def build(output):
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    with tempfile.TemporaryDirectory(prefix="fleshfetch-deb-") as temp:
        temp = Path(temp)
        stage = temp / "root"
        stage_package(stage)
        dpkg = shutil.which("dpkg-deb")
        if dpkg:
            subprocess.run([dpkg, "--build", "--root-owner-group", "-Zgzip",
                            str(stage), str(output)], check=True)
        else:
            ar = shutil.which("ar")
            if not ar:
                raise RuntimeError("Install dpkg-deb or GNU ar to build the package")
            (temp / "debian-binary").write_bytes(b"2.0\n")
            with tarfile.open(temp / "control.tar.gz", "w:gz", format=tarfile.GNU_FORMAT) as archive:
                for path in sorted((stage / "DEBIAN").iterdir()):
                    archive.add(path, arcname="./" + path.name, filter=archive_filter)
            with tarfile.open(temp / "data.tar.gz", "w:gz", format=tarfile.GNU_FORMAT) as archive:
                archive.add(stage / "usr", arcname="./usr", filter=archive_filter)
            subprocess.run([ar, "rcD", str(output), "debian-binary",
                            "control.tar.gz", "data.tar.gz"], cwd=temp, check=True)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=ROOT / "output" / f"fleshfetch_{VERSION}_all.deb")
    print(build(parser.parse_args().output))


if __name__ == "__main__":
    main()
