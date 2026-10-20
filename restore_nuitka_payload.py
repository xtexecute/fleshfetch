"""Restore report-listed runtime files when retrying only the C compiler."""

from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
DIST = ROOT / ".build" / "main.dist"


def restore():
    report = ET.parse(ROOT / ".build" / "nuitka-report.xml").getroot()
    variables = {"${cwd}": str(ROOT), "${sys.prefix}": sys.prefix,
                 "${sys.real_prefix}": getattr(sys, "real_prefix", sys.base_prefix)}
    count = 0
    for entry in report:
        if entry.tag not in ("included_extension", "included_dll", "data_file") or entry.get("ignored") == "yes":
            continue
        source_text = entry.get("source_path") or entry.get("source")
        target_text = entry.get("dest_path") or entry.get("name")
        if not source_text or not target_text:
            raise ValueError(f"Incomplete build report entry: {entry.attrib}")
        for name, value in variables.items():
            source_text = source_text.replace(name, value)
        source = Path(source_text)
        target = (DIST / target_text).resolve()
        if not target.is_relative_to(DIST.resolve()):
            raise ValueError(f"Unexpected runtime path: {target}")
        if not source.is_file():
            raise FileNotFoundError(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        count += 1
    print(f"Restored {count} runtime and data files from the Nuitka report.")


if __name__ == "__main__":
    restore()
