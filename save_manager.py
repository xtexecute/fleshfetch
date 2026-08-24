import hashlib
import json
import os
import time

from defaults import DEFAULT_ACHIEVEMENTS, DEFAULT_SETTINGS, DEFAULT_STATE
from paths import (
    ACHIEVEMENTS_FILE,
    COUNTER_FILE,
    LEGACY_ACHIEVEMENTS_FILE,
    LEGACY_COUNTER_FILE,
    LEGACY_STATE_FILE,
    SAVES_DIR,
    SAVE_BACKUPS_DIR,
    SETTINGS_FILE,
    STATE_FILE,
)

# ---------- JSON HELPERS ----------

def load_json(path, default, legacy_path=None):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default.copy()
    if legacy_path and os.path.exists(legacy_path):
        try:
            with open(legacy_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            try:
                save_json(path, data)
            except Exception:
                pass
            return data
        except Exception:
            return default.copy()
    return default.copy()


def save_json(path, data):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def load_legacy_counter():
    for p in (COUNTER_FILE, LEGACY_COUNTER_FILE):
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    return int(f.read().strip())
            except Exception:
                continue
    return 0


def save_legacy_counter(value):
    try:
        os.makedirs(os.path.dirname(COUNTER_FILE), exist_ok=True)
        with open(COUNTER_FILE, "w") as f:
            f.write(str(int(value)))
    except Exception:
        pass


# ---------- SAVE SLOTS ----------

DEFAULT_SAVE_ID = "main"
DEFAULT_SAVE_NAME = "Main Save"
DEFAULT_SAVE_KIND = "singleplayer"
SAVE_BACKUP_LIMIT = 10
SAVE_AUTO_BACKUP_INTERVAL_SECONDS = 300
SAVE_DIRTY_FLUSH_INTERVAL_MS = 750


def clone_json_data(data):
    try:
        return json.loads(json.dumps(data))
    except Exception:
        return data.copy() if isinstance(data, dict) else data


def current_save_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def normalize_save_name(name: str) -> str:
    text = " ".join(str(name or "").replace("\r", " ").replace("\n", " ").split())
    return text[:48] or "Unnamed Save"


def normalize_save_id(save_id: str) -> str:
    text = str(save_id or "").strip().lower()
    safe = "".join(ch for ch in text if ch.isalnum() or ch in ("-", "_"))
    return safe or DEFAULT_SAVE_ID


def normalize_save_kind(save_kind: str) -> str:
    text = str(save_kind or "").strip().lower()
    safe = "".join(ch for ch in text if ch.isalnum() or ch in ("-", "_"))
    return safe or DEFAULT_SAVE_KIND


def make_save_id(name: str) -> str:
    base = normalize_save_name(name).lower().replace(" ", "-")
    slug = "".join(ch for ch in base if ch.isalnum() or ch in ("-", "_")).strip("-_")
    slug = slug[:24] or "save"
    suffix = hashlib.sha1(f"{name}-{time.time()}".encode("utf-8", errors="replace")).hexdigest()[:8]
    return normalize_save_id(f"{slug}-{suffix}")


def save_slot_path(save_id: str) -> str:
    return os.path.join(SAVES_DIR, f"{normalize_save_id(save_id)}.json")


def save_backup_dir(save_id: str) -> str:
    return os.path.join(SAVE_BACKUPS_DIR, normalize_save_id(save_id))


def save_slot_exists(save_id: str) -> bool:
    return os.path.exists(save_slot_path(save_id))


def build_save_slot_data(
    save_id: str,
    name: str,
    state: dict,
    achievements: dict,
    required_mods=None,
    mod_data=None,
    previous=None,
    save_kind=None,
) -> dict:
    previous = previous if isinstance(previous, dict) else {}
    now = current_save_timestamp()
    previous_mod_data = previous.get("mod_data") if isinstance(previous.get("mod_data"), dict) else {}
    return {
        "id": normalize_save_id(save_id),
        "name": normalize_save_name(name),
        "save_kind": normalize_save_kind(save_kind or previous.get("save_kind")),
        "created_at": previous.get("created_at") or now,
        "updated_at": now,
        "last_auto_backup_at": previous.get("last_auto_backup_at", 0),
        "required_mods": list(required_mods or previous.get("required_mods") or []),
        "mod_data": clone_json_data(mod_data if isinstance(mod_data, dict) else previous_mod_data),
        "state": clone_json_data(state),
        "achievements": clone_json_data(achievements),
    }


def load_save_slot_data(save_id: str):
    data = load_json(save_slot_path(save_id), {})
    if not isinstance(data, dict):
        return None
    slot_id = normalize_save_id(data.get("id") or save_id)
    data.setdefault("id", slot_id)
    data.setdefault("name", DEFAULT_SAVE_NAME if slot_id == DEFAULT_SAVE_ID else slot_id)
    data["save_kind"] = normalize_save_kind(data.get("save_kind"))
    data.setdefault("created_at", current_save_timestamp())
    data.setdefault("updated_at", data["created_at"])
    data.setdefault("last_auto_backup_at", 0)
    data.setdefault("required_mods", [])
    data.setdefault("mod_data", {})
    if not isinstance(data["mod_data"], dict):
        data["mod_data"] = {}
    data.setdefault("state", clone_json_data(DEFAULT_STATE))
    data.setdefault("achievements", clone_json_data(DEFAULT_ACHIEVEMENTS))
    return data


def write_save_slot_data(slot_data: dict):
    os.makedirs(SAVES_DIR, exist_ok=True)
    save_json(save_slot_path(slot_data["id"]), slot_data)


def list_save_slots(save_kind=None):
    os.makedirs(SAVES_DIR, exist_ok=True)
    wanted_kind = normalize_save_kind(save_kind) if save_kind is not None else None
    slots = []
    for filename in sorted(os.listdir(SAVES_DIR)):
        path = os.path.join(SAVES_DIR, filename)
        if not filename.lower().endswith(".json") or not os.path.isfile(path):
            continue
        save_id = os.path.splitext(filename)[0]
        slot = load_save_slot_data(save_id)
        if slot and (wanted_kind is None or slot.get("save_kind") == wanted_kind):
            slots.append(slot)
    slots.sort(key=lambda slot: str(slot.get("updated_at", "")), reverse=True)
    return slots


def backup_save_slot(save_id: str, reason: str = "manual"):
    source = save_slot_path(save_id)
    if not os.path.exists(source):
        return ""
    backup_dir = save_backup_dir(save_id)
    os.makedirs(backup_dir, exist_ok=True)
    safe_reason = "".join(ch for ch in reason if ch.isalnum() or ch in ("-", "_")) or "backup"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    millis = int((time.time() % 1) * 1000)
    target = os.path.join(backup_dir, f"{stamp}-{millis:03d}-{safe_reason}.json")
    try:
        with open(source, "rb") as src, open(target, "wb") as dst:
            while True:
                chunk = src.read(65536)
                if not chunk:
                    break
                dst.write(chunk)
    except Exception:
        return ""
    trim_save_backups(save_id)
    return target


def trim_save_backups(save_id: str):
    backup_dir = save_backup_dir(save_id)
    if not os.path.isdir(backup_dir):
        return
    backups = [
        os.path.join(backup_dir, filename)
        for filename in os.listdir(backup_dir)
        if filename.lower().endswith(".json")
    ]
    backups.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    for old_path in backups[SAVE_BACKUP_LIMIT:]:
        try:
            os.unlink(old_path)
        except Exception:
            pass


def list_save_backups(save_id: str):
    backup_dir = save_backup_dir(save_id)
    if not os.path.isdir(backup_dir):
        return []
    backups = [
        os.path.join(backup_dir, filename)
        for filename in os.listdir(backup_dir)
        if filename.lower().endswith(".json")
    ]
    backups.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    return backups


def latest_save_backup(save_id: str):
    backups = list_save_backups(save_id)
    return backups[0] if backups else ""


def save_name_to_filename(name: str) -> str:
    safe = normalize_save_name(name).replace(" ", "_")
    safe = "".join(ch for ch in safe if ch.isalnum() or ch in ("-", "_"))
    return f"{safe or 'save'}.fleshsave.json"


def normalize_export_path(path: str) -> str:
    path = str(path or "").strip()
    lower = path.lower()
    if not lower.endswith((".json", ".fleshsave")):
        path += ".json"
    return path


def backup_display_name(path: str) -> str:
    filename = os.path.basename(path)
    stem = os.path.splitext(filename)[0]
    parts = stem.split("-")
    if len(parts) >= 4 and len(parts[0]) == 8 and len(parts[1]) == 6:
        date = f"{parts[0][0:4]}-{parts[0][4:6]}-{parts[0][6:8]}"
        clock = f"{parts[1][0:2]}:{parts[1][2:4]}:{parts[1][4:6]}"
        reason = "-".join(parts[3:])
        return f"{date} {clock} ({reason})"
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))
    except Exception:
        return filename


def write_json_file(path: str, data: dict):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_save_slot_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and isinstance(data.get("slot"), dict):
        data = data["slot"]
    if not isinstance(data, dict):
        raise ValueError("Save file is not a JSON object.")
    if not isinstance(data.get("state"), dict):
        raise ValueError("Save file is missing state data.")
    if not isinstance(data.get("achievements"), dict):
        raise ValueError("Save file is missing achievement data.")
    if not isinstance(data.get("mod_data", {}), dict):
        data["mod_data"] = {}
    return data


def copy_file_bytes(source: str, target: str):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(source, "rb") as src, open(target, "wb") as dst:
        while True:
            chunk = src.read(65536)
            if not chunk:
                break
            dst.write(chunk)

def maybe_auto_backup_save_slot(slot_data: dict):
    try:
        last_backup = float(slot_data.get("last_auto_backup_at", 0) or 0)
    except Exception:
        last_backup = 0
    now = time.time()
    if now - last_backup < SAVE_AUTO_BACKUP_INTERVAL_SECONDS:
        return False
    if backup_save_slot(slot_data["id"], reason="auto"):
        slot_data["last_auto_backup_at"] = now
        return True
    return False


def ensure_save_storage(settings: dict):
    os.makedirs(SAVES_DIR, exist_ok=True)
    os.makedirs(SAVE_BACKUPS_DIR, exist_ok=True)

    slots = list_save_slots()
    singleplayer_slots = list_save_slots(DEFAULT_SAVE_KIND)
    if not singleplayer_slots:
        legacy_state = load_json(STATE_FILE, DEFAULT_STATE, legacy_path=LEGACY_STATE_FILE)
        legacy_achievements = load_json(
            ACHIEVEMENTS_FILE,
            DEFAULT_ACHIEVEMENTS,
            legacy_path=LEGACY_ACHIEVEMENTS_FILE,
        )
        main_slot = build_save_slot_data(
            DEFAULT_SAVE_ID,
            DEFAULT_SAVE_NAME,
            legacy_state,
            legacy_achievements,
            required_mods=[],
        )
        write_save_slot_data(main_slot)
        slots.append(main_slot)
        singleplayer_slots = [main_slot]

    active_id = normalize_save_id(settings.get("active_save_id") or DEFAULT_SAVE_ID)
    if not save_slot_exists(active_id):
        active_id = normalize_save_id(singleplayer_slots[0]["id"])
    if settings.get("active_save_id") != active_id:
        settings["active_save_id"] = active_id
        save_json(SETTINGS_FILE, settings)
    return active_id
