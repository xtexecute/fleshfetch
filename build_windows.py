"""Build a portable Qt/Nuitka Windows release candidate."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import importlib.metadata

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zig", type=Path, required=True)
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--recompile-c-only", action="store_true")
    args = parser.parse_args()
    zig = args.zig.resolve()
    env = os.environ.copy()
    env["PATH"] = str(zig.parent) + os.pathsep + env["PATH"]
    env["CCFLAGS"] = "-march=x86_64 -mno-avx -mno-avx2 -mno-fma -mno-bmi -mno-bmi2"
    env["NUITKA_CACHE_DIR"] = str(ROOT / ".build" / "cache")
    env["ZIG_GLOBAL_CACHE_DIR"] = str(ROOT / ".build" / "zig-global")
    env["ZIG_LOCAL_CACHE_DIR"] = str(ROOT / ".build" / "zig-local")
    if not args.package_only:
        command = [sys.executable, "-m", "nuitka", "--mode=standalone", "--zig",
                   "--enable-plugin=pyside6", "--include-qt-plugins=qml,multimedia",
                   "--assume-yes-for-downloads", "--windows-console-mode=disable",
                   "--output-dir=" + str(ROOT / ".build"), "--output-filename=fleshfetch-runtime.exe",
                   "--windows-product-name=Fleshfetch", "--windows-company-name=xtexecute",
                   "--windows-file-version=1.4.0.0", "--windows-product-version=1.4.0",
                   "--include-data-dir=" + str(ROOT / "qml") + "=qml",
                   "--include-data-files=" + str(ROOT / "default.conf") + "=default.conf",
                   "--nofollow-import-to=ui,gtk_compat,rendering,gi,cairo,pygame",
                   "--report=" + str(ROOT / ".build" / "nuitka-report.xml"),
                   "--jobs=6", str(ROOT / "main.py")]
        if (ROOT / "flesh.ico").exists():
            command.insert(-1, "--windows-icon-from-ico=" + str(ROOT / "flesh.ico"))
        if args.recompile_c_only:
            command.insert(-1, "--devel-recompile-c-only")
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    dist = ROOT / ".build" / "main.dist"
    if not (dist / "PySide6" / "QtCore.pyd").is_file():
        from restore_nuitka_payload import restore
        restore()
    release = ROOT / "output" / "fleshfetch-1.4.0-rc2-windows" / "fleshfetch"
    if release.exists():
        raise FileExistsError(f"Release folder already exists: {release}")
    shutil.copytree(dist, release / "runtime")
    shutil.copytree(ROOT / "assets", release / "assets")
    for name in ("flesh.png", "click.wav", "flesh.ico"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, release / "assets" / name)
    resources = ROOT / ".build" / "launcher.res"
    subprocess.run([str(zig), "rc", "/fo", str(resources), str(ROOT / "fleshfetch_launcher.rc")], cwd=ROOT, env=env, check=True)
    subprocess.run([str(zig), "cc", "-target", "x86_64-windows-gnu", "-march=x86_64",
                    "-mno-avx", "-mno-avx2", "-O2", "-municode", "-Wl,--subsystem,windows",
                    str(ROOT / "fleshfetch_launcher.c"), str(resources), "-o", str(release / "fleshfetch.exe"), "-luser32"],
                   cwd=ROOT, env=env, check=True)
    for name in ("LICENSE", "TESTING_1.4.md", "MOD_UI_THEMES.md"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, release / "runtime" / name)
    if (ROOT / "output" / "pdf" / "ff-v1.4_modding_reference.pdf").exists():
        shutil.copy2(ROOT / "output" / "pdf" / "ff-v1.4_modding_reference.pdf", release / "runtime")
    for name in ("PySide6_Essentials", "PySide6_Addons", "shiboken6", "requests", "urllib3", "certifi", "idna", "charset-normalizer", "pypresence"):
        distribution = importlib.metadata.distribution(name)
        for item in distribution.files or []:
            if "licenses" in item.parts or item.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                source = distribution.locate_file(item)
                if source.is_file():
                    target = release / "runtime" / "licenses" / name / item.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    archive = ROOT / "output" / "ff_v1.4.0-rc2_win.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for path in sorted(release.rglob("*")):
            if path.is_file() and path.suffix.lower() != ".pdb":
                package.write(path, path.relative_to(release.parent))
    print(archive)


if __name__ == "__main__":
    main()
