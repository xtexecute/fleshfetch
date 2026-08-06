EVENT_ALIASES = {
    "click": "flesh_clicked",
    "clicked": "flesh_clicked",
    "flesh_click": "flesh_clicked",
    "flesh_clicked": "flesh_clicked",
    "on_flesh_clicked": "flesh_clicked",
    "buy": "upgrade_bought",
    "bought": "upgrade_bought",
    "upgrade_buy": "upgrade_bought",
    "upgrade_bought": "upgrade_bought",
    "on_upgrade_bought": "upgrade_bought",
    "save": "save",
    "saved": "save",
    "on_save": "save",
    "load": "load",
    "loaded": "load",
    "on_load": "load",
}


class ModDependencyError(RuntimeError):
    def __init__(self, message, missing=None):
        super().__init__(message)
        self.missing = list(missing or [])


def normalize_mod_id(mod_id: str) -> str:
    return str(mod_id or "").strip()


def normalize_mod_dependencies(raw_dependencies):
    dependencies = []
    if not raw_dependencies:
        return dependencies
    if isinstance(raw_dependencies, (str, dict)):
        raw_dependencies = [raw_dependencies]
    if not isinstance(raw_dependencies, list):
        return dependencies
    for dep in raw_dependencies:
        if isinstance(dep, str):
            dep_id = normalize_mod_id(dep)
            if dep_id:
                dependencies.append({"id": dep_id, "version": "", "optional": False})
        elif isinstance(dep, dict):
            dep_id = normalize_mod_id(dep.get("id") or dep.get("name") or dep.get("mod"))
            if dep_id:
                dependencies.append({
                    "id": dep_id,
                    "version": str(dep.get("version") or dep.get("min_version") or ""),
                    "optional": bool(dep.get("optional", False)),
                })
    return dependencies


def version_meets_requirement(version: str, required: str) -> bool:
    if not required:
        return True
    version = str(version or "")
    required = str(required or "")
    if version == required:
        return True

    def parts(text):
        values = []
        for piece in text.replace("-", ".").split("."):
            digits = "".join(ch for ch in piece if ch.isdigit())
            values.append(int(digits or 0))
        return values

    current_parts = parts(version)
    required_parts = parts(required)
    size = max(len(current_parts), len(required_parts))
    current_parts += [0] * (size - len(current_parts))
    required_parts += [0] * (size - len(required_parts))
    return current_parts >= required_parts
