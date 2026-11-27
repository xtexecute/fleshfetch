"""Build a portable Qt/Nuitka Windows release."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import importlib.metadata
import hashlib
import json

from app_version import VERSION, WINDOWS_VERSION

ROOT = Path(__file__).resolve().parent
BUILD_MODULES = {"build_windows.py", "build_debian.py", "package_source.py",
                 "restore_nuitka_payload.py", "update_reference_14.py"}


def runtime_fingerprint():
    paths = [path for path in ROOT.glob("*.py") if path.name not in BUILD_MODULES and "_OLD" not in path.name]
    paths += list((ROOT / "qml").rglob("*")) + [ROOT / "default.conf"]
    digest = hashlib.sha256()
    for path in sorted(p for p in paths if p.is_file() and "__pycache__" not in p.parts):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zig", type=Path, required=True)
    parser.add_argument("--package-only", action="store_true")
    parser.add_argument("--recompile-c-only", action="store_true")
    parser.add_argument("--release-version", default=VERSION)
    args = parser.parse_args()
    zig = args.zig.resolve()
    if not zig.is_file():
        raise FileNotFoundError(zig)
    if args.release_version != VERSION:
        raise ValueError("Set app_version.py before building a different release")
    resource = (ROOT / "fleshfetch_launcher.rc").read_text(encoding="utf-8")
    if f'"FileVersion", "{VERSION}"' not in resource or f'"ProductVersion", "{VERSION}"' not in resource:
        raise ValueError("Launcher version does not match app_version.py")
    (ROOT / ".build").mkdir(exist_ok=True)
    fingerprint = runtime_fingerprint()
    manifest = ROOT / ".build" / "runtime-build.json"
    env = os.environ.copy()
    env["PATH"] = str(zig.parent) + os.pathsep + env["PATH"]
    cpu_flags = "-target x86_64-windows-gnu -march=x86_64 -mno-avx -mno-avx2 -mno-avx512f -mno-fma -mno-bmi -mno-bmi2"
    env["CCFLAGS"] = cpu_flags
    # Zig builds compiler-runtime helpers during linking as well as C compilation.
    env["LDFLAGS"] = cpu_flags
    env["NUITKA_CACHE_DIR"] = str(ROOT / ".build" / "cache")
    env["ZIG_GLOBAL_CACHE_DIR"] = str(ROOT / ".build" / "zig-global")
    env["ZIG_LOCAL_CACHE_DIR"] = str(ROOT / ".build" / "zig-local")
    if not args.package_only:
        command = [sys.executable, "-m", "nuitka", "--mode=standalone", "--zig",
                   "--enable-plugin=pyside6", "--include-qt-plugins=qml,multimedia",
                   "--assume-yes-for-downloads", "--update-check=never", "--windows-console-mode=disable",
                   "--output-dir=" + str(ROOT / ".build"), "--output-filename=fleshfetch-runtime.exe",
                   "--windows-product-name=fleshfetch", "--windows-company-name=xtexecute",
                   "--windows-file-version=" + WINDOWS_VERSION, "--windows-product-version=" + WINDOWS_VERSION,
                   "--windows-file-description=fleshfetch " + VERSION,
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
        if runtime_fingerprint() != fingerprint:
            raise RuntimeError("Source changed during compilation; rebuild before packaging")
    dist = ROOT / ".build" / "main.dist"
    if not (dist / "PySide6" / "QtCore.pyd").is_file():
        from restore_nuitka_payload import restore
        restore()
    runtime = dist / "fleshfetch-runtime.exe"
    runtime_hash = hashlib.sha256(runtime.read_bytes()).hexdigest()
    if args.package_only:
        built = json.loads(manifest.read_text(encoding="utf-8"))
        if built != {"version": VERSION, "fingerprint": fingerprint, "runtime_sha256": runtime_hash}:
            raise RuntimeError("Compiled runtime is stale; run a full build before packaging")
    else:
        manifest.write_text(json.dumps({"version": VERSION, "fingerprint": fingerprint,
                                       "runtime_sha256": runtime_hash}, indent=2) + "\n", encoding="utf-8")
    release = ROOT / "output" / f"fleshfetch-{args.release_version}-windows" / "fleshfetch"
    if release.exists():
        raise FileExistsError(f"Release folder already exists: {release}")
    shutil.copytree(dist, release / "runtime")
    shutil.copytree(ROOT / "assets", release / "assets")
    # QML resolves ../assets relative to runtime/qml; Python also supports the
    # user-replaceable assets next to the launcher.
    shutil.copytree(ROOT / "assets", release / "runtime" / "assets")
    for name in ("flesh.png", "click.wav", "flesh.ico"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, release / "assets" / name)
    resources = ROOT / ".build" / "launcher.res"
    subprocess.run([str(zig), "rc", "/fo", str(resources), str(ROOT / "fleshfetch_launcher.rc")], cwd=ROOT, env=env, check=True)
    subprocess.run([str(zig), "cc", "-target", "x86_64-windows-gnu", "-march=x86_64",
                    "-mno-avx", "-mno-avx2", "-O2", "-municode", "-Wl,--subsystem,windows",
                    str(ROOT / "fleshfetch_launcher.c"), str(resources), "-o", str(release / "fleshfetch.exe"), "-luser32"],
                   cwd=ROOT, env=env, check=True)
    for name in ("LICENSE", "README.md", "CHANGELOG.md"):
        if (ROOT / name).exists():
            shutil.copy2(ROOT / name, release / name)
    shutil.copytree(ROOT / "docs", release / "docs")
    for name in ("PySide6_Essentials", "PySide6_Addons", "shiboken6", "requests", "urllib3", "certifi", "idna", "charset-normalizer", "pypresence"):
        distribution = importlib.metadata.distribution(name)
        for item in distribution.files or []:
            if "licenses" in item.parts or item.name.upper().startswith(("LICENSE", "COPYING", "NOTICE")):
                source = distribution.locate_file(item)
                if source.is_file():
                    target = release / "runtime" / "licenses" / name / item.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    archive = ROOT / "output" / f"ff_v{args.release_version}_win.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as package:
        for path in sorted(release.rglob("*")):
            if path.is_file() and path.suffix.lower() != ".pdb":
                package.write(path, path.relative_to(release.parent))
    print(archive)


if __name__ == "__main__":
    main()
