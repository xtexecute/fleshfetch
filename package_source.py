"""Create a source archive without environments, caches, saves or build output."""

from pathlib import Path
import zipfile

from app_version import VERSION

ROOT = Path(__file__).resolve().parent


def main():
    output = ROOT / "output" / f"ff_v{VERSION}_source.zip"
    output.parent.mkdir(exist_ok=True)
    if output.exists():
        raise FileExistsError(output)
    paths = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in (".py", ".md", ".txt", ".conf", ".png", ".wav", ".ico", ".desktop", ".c", ".rc", ".bat")]
    paths.extend(ROOT / name for name in ("LICENSE", "fleshfetch"))
    for folder in ("qml", "assets", "example_mods", "packaging", "docs"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file())
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            if ("__pycache__" in path.parts or path.suffix == ".pyc" or "_OLD" in path.name
                    or path.name in {"update_reference_14.py"}):
                continue
            archive.write(path, Path("fleshfetch") / path.relative_to(ROOT))
    print(output)


if __name__ == "__main__":
    main()
