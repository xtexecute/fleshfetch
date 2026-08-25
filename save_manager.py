import hashlib
import json
import os
import time

from gtk_compat import GLib

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


class SaveManagerMixin:
    def _current_required_mods(self):
        required = []
        by_id = {}
        for mod_req in getattr(self, "active_save_required_mods", []) or []:
            if isinstance(mod_req, dict):
                mod_id = str(mod_req.get("id") or "")
                if mod_id:
                    by_id[mod_id] = {
                        "id": mod_id,
                        "name": mod_req.get("name") or mod_id,
                        "version": mod_req.get("version") or "",
                    }
            elif mod_req:
                mod_id = str(mod_req)
                by_id[mod_id] = {"id": mod_id, "name": mod_id, "version": ""}

        loaded_ids = set(getattr(self, "loaded_mod_ids", set()))
        for mod_info in getattr(self, "installed_mods", []):
            mod_id = mod_info.get("id")
            if not mod_id or mod_id not in loaded_ids:
                continue
            by_id[mod_id] = {
                "id": mod_id,
                "name": mod_info.get("name") or mod_id,
                "version": mod_info.get("version") or "",
            }
        for mod_id in sorted(by_id):
            required.append(by_id[mod_id])
        return required

    def _loaded_mod_ids(self):
        return set(getattr(self, "loaded_mod_ids", set()))

    def _save_slot_missing_mods(self, slot_data: dict):
        loaded_ids = self._loaded_mod_ids()
        missing = []
        for mod_req in slot_data.get("required_mods", []) or []:
            mod_id = str(mod_req.get("id") if isinstance(mod_req, dict) else mod_req)
            if mod_id and mod_id not in loaded_ids:
                if isinstance(mod_req, dict):
                    label = mod_req.get("name") or mod_id
                    version = mod_req.get("version") or ""
                    if version:
                        label = f"{label} {version}"
                else:
                    label = mod_id
                missing.append(label)
        return missing

    def _startup_missing_active_save(self):
        slot = load_save_slot_data(self.active_save_id)
        if not slot:
            return None
        missing_mods = self._save_slot_missing_mods(slot)
        if not missing_mods:
            return None
        return {
            "save_id": normalize_save_id(slot.get("id") or self.active_save_id),
            "save_name": normalize_save_name(slot.get("name") or self.active_save_id),
            "save_kind": normalize_save_kind(slot.get("save_kind")),
            "missing_mods": missing_mods,
        }

    def mark_save_dirty(self, auto_backup=True):
        self._save_dirty = True
        self._save_dirty_auto_backup = bool(self._save_dirty_auto_backup or auto_backup)
        if self._dirty_save_timer_id is None:
            self._dirty_save_timer_id = GLib.timeout_add(
                SAVE_DIRTY_FLUSH_INTERVAL_MS,
                self._flush_dirty_save_from_timer,
            )

    def _flush_dirty_save_from_timer(self):
        self._dirty_save_timer_id = None
        self.flush_dirty_save()
        return False

    def flush_dirty_save(self, auto_backup=None):
        if not getattr(self, "_save_dirty", False):
            return False
        flush_auto_backup = self._save_dirty_auto_backup if auto_backup is None else bool(auto_backup)
        self._save_dirty = False
        self._save_dirty_auto_backup = False
        self.save_current_progress(auto_backup=flush_auto_backup)
        return True

    def on_close_request(self, *args):
        self.flush_dirty_save(auto_backup=True)
        return False

    def _apply_save_slot_without_presaving_current(self, slot: dict, reason="load", emit_load_event=True):
        self.active_save_id = normalize_save_id(slot["id"])
        self.active_save_name = normalize_save_name(slot.get("name") or self.active_save_id)
        self.active_save_kind = normalize_save_kind(slot.get("save_kind"))
        self.active_save_created_at = slot.get("created_at") or current_save_timestamp()
        self.active_save_updated_at = slot.get("updated_at") or self.active_save_created_at
        self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
        self.active_save_required_mods = list(slot.get("required_mods", []))
        self.settings["active_save_id"] = self.active_save_id
        save_json(SETTINGS_FILE, self.settings)

        self.state = clone_json_data(slot.get("state", DEFAULT_STATE))
        self.achievements = clone_json_data(slot.get("achievements", DEFAULT_ACHIEVEMENTS))
        self.save_namespaces = clone_json_data(slot.get("mod_data", {}))
        if not isinstance(self.save_namespaces, dict):
            self.save_namespaces = {}
        self._normalize_progress_after_load()
        self.invalidate_rate_cache()
        self.save_current_progress(auto_backup=False)
        self.update_labels()
        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        self.refresh_stats_tab(force=True)
        if hasattr(self, "saves_list_box"):
            self.refresh_saves_list()
        if emit_load_event:
            self._emit_event("load", {
                "save_id": self.active_save_id,
                "save_name": self.active_save_name,
                "save_kind": self.active_save_kind,
                "reason": reason,
            })

    def _switch_to_startup_safe_save(self, skipped_info: dict):
        skipped_id = normalize_save_id(skipped_info.get("save_id"))
        skipped_name = normalize_save_name(skipped_info.get("save_name") or skipped_id)
        missing_text = ", ".join(skipped_info.get("missing_mods", []))
        backup_save_slot(skipped_id, reason="missingmods")

        for slot in list_save_slots():
            save_id = normalize_save_id(slot.get("id"))
            if save_id == skipped_id:
                continue
            if self._save_slot_missing_mods(slot):
                continue
            self._apply_save_slot_without_presaving_current(slot, reason="startup_fallback")
            return (
                f"Skipped save '{skipped_name}' because it requires missing mods: {missing_text}. "
                f"Loaded '{self.active_save_name}' instead."
            )

        recovery_name = "Recovery Save"
        recovery_id = make_save_id(recovery_name)
        recovery_slot = build_save_slot_data(
            recovery_id,
            recovery_name,
            DEFAULT_STATE,
            DEFAULT_ACHIEVEMENTS,
            required_mods=[],
        )
        write_save_slot_data(recovery_slot)
        self._apply_save_slot_without_presaving_current(recovery_slot, reason="startup_recovery")
        return (
            f"Skipped save '{skipped_name}' because it requires missing mods: {missing_text}. "
            "Created a clean Recovery Save instead."
        )

    def save_current_progress(self, auto_backup=True):
        previous = {
            "created_at": getattr(self, "active_save_created_at", current_save_timestamp()),
            "updated_at": getattr(self, "active_save_updated_at", current_save_timestamp()),
            "last_auto_backup_at": getattr(self, "active_save_last_auto_backup_at", 0),
            "required_mods": getattr(self, "active_save_required_mods", []),
            "mod_data": getattr(self, "save_namespaces", {}),
            "save_kind": getattr(self, "active_save_kind", DEFAULT_SAVE_KIND),
        }
        slot = build_save_slot_data(
            self.active_save_id,
            self.active_save_name,
            self.state,
            self.achievements,
            required_mods=self._current_required_mods(),
            mod_data=self.save_namespaces,
            previous=previous,
            save_kind=self.active_save_kind,
        )
        if auto_backup:
            maybe_auto_backup_save_slot(slot)
        write_save_slot_data(slot)
        self.active_save_name = slot["name"]
        self.active_save_kind = normalize_save_kind(slot.get("save_kind"))
        self.active_save_created_at = slot["created_at"]
        self.active_save_updated_at = slot["updated_at"]
        self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
        self.active_save_required_mods = list(slot.get("required_mods", []))
        if self.active_save_kind == DEFAULT_SAVE_KIND:
            save_json(STATE_FILE, self.state)
            save_json(ACHIEVEMENTS_FILE, self.achievements)
            save_legacy_counter(self.state.get("currencies", {}).get("flesh", 0.0))
        if hasattr(self, "_save_dirty"):
            self._save_dirty = False
            self._save_dirty_auto_backup = False
        if hasattr(self, "_event_hooks") and not getattr(self, "_in_save_event", False):
            self._in_save_event = True
            try:
                self._emit_event("save", {
                    "save_id": self.active_save_id,
                    "save_name": self.active_save_name,
                    "save_kind": self.active_save_kind,
                    "slot": slot,
                    "auto_backup": bool(auto_backup),
                })
            finally:
                self._in_save_event = False

    def _normalize_progress_after_load(self):
        if not isinstance(self.state, dict):
            self.state = clone_json_data(DEFAULT_STATE)
        if not isinstance(self.achievements, dict):
            self.achievements = clone_json_data(DEFAULT_ACHIEVEMENTS)
        self.achievements = {
            k: dict(v) if isinstance(v, dict) else v
            for k, v in self.achievements.items()
        }

        for k, v in DEFAULT_STATE.items():
            if k not in self.state:
                self.state[k] = clone_json_data(v)
        if "upgrades_owned" not in self.state or not isinstance(self.state["upgrades_owned"], dict):
            self.state["upgrades_owned"] = {}
        if "flesh" in self.state and not isinstance(self.state.get("currencies"), dict):
            self.state["currencies"] = {"flesh": float(self.state.pop("flesh", 0.0))}
        if "currencies" not in self.state or not isinstance(self.state["currencies"], dict):
            self.state["currencies"] = {"flesh": 0.0}
        self.state["currencies"].setdefault("flesh", 0.0)

        for k, v in DEFAULT_ACHIEVEMENTS.items():
            if k not in self.achievements:
                self.achievements[k] = dict(v)
        self._normalize_achievement_sources()

    def _fresh_save_state(self):
        state = clone_json_data(DEFAULT_STATE)
        state["currencies"] = clone_json_data(DEFAULT_STATE.get("currencies", {"flesh": 0.0}))
        for registry_name in self.currencies:
            state["currencies"].setdefault(registry_name, 0.0)
        state["upgrades_owned"] = {}
        state["total_clicks"] = 0
        return state

    def _fresh_save_achievements(self):
        achievements = clone_json_data(DEFAULT_ACHIEVEMENTS)
        for data in achievements.values():
            if isinstance(data, dict):
                data["unlocked"] = False

        for key, data in self.achievements.items():
            if key in DEFAULT_ACHIEVEMENTS or not isinstance(data, dict):
                continue
            if not self._achievement_is_active(key, data):
                continue
            fresh_data = dict(data)
            fresh_data["unlocked"] = False
            achievements[key] = fresh_data
        return achievements

    def load_save_slot(self, save_id: str, allow_missing_mods=False):
        slot = load_save_slot_data(save_id)
        if not slot:
            return False, "Save could not be loaded."
        if normalize_save_id(slot["id"]) == self.active_save_id:
            return True, f"'{self.active_save_name}' is already active."
        missing_mods = self._save_slot_missing_mods(slot)
        if missing_mods and not allow_missing_mods:
            return False, "Missing required mods: " + ", ".join(missing_mods)

        self.save_current_progress(auto_backup=True)
        backup_save_slot(slot["id"], reason="preload")
        self.active_save_id = normalize_save_id(slot["id"])
        self.active_save_name = normalize_save_name(slot.get("name") or self.active_save_id)
        self.active_save_kind = normalize_save_kind(slot.get("save_kind"))
        self.active_save_created_at = slot.get("created_at") or current_save_timestamp()
        self.active_save_updated_at = slot.get("updated_at") or self.active_save_created_at
        self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
        self.active_save_required_mods = list(slot.get("required_mods", []))
        self.settings["active_save_id"] = self.active_save_id
        save_json(SETTINGS_FILE, self.settings)

        self.state = clone_json_data(slot.get("state", DEFAULT_STATE))
        self.achievements = clone_json_data(slot.get("achievements", DEFAULT_ACHIEVEMENTS))
        self.save_namespaces = clone_json_data(slot.get("mod_data", {}))
        if not isinstance(self.save_namespaces, dict):
            self.save_namespaces = {}
        self._normalize_progress_after_load()
        self.invalidate_rate_cache()
        self.save_current_progress(auto_backup=False)
        self.update_labels()
        self.refresh_upgrades_ui()
        self.refresh_achievements_ui()
        self.refresh_stats_tab(force=True)
        if hasattr(self, "saves_list_box"):
            self.refresh_saves_list()
        self._emit_event("load", {
            "save_id": self.active_save_id,
            "save_name": self.active_save_name,
            "save_kind": self.active_save_kind,
            "reason": "manual",
        })
        return True, f"Loaded save '{self.active_save_name}'."

    def create_save_slot(self, name: str, save_kind=DEFAULT_SAVE_KIND):
        self.save_current_progress(auto_backup=True)
        save_name = normalize_save_name(name)
        save_id = make_save_id(save_name)
        fresh_state = self._fresh_save_state()
        fresh_achievements = self._fresh_save_achievements()
        slot = build_save_slot_data(
            save_id,
            save_name,
            fresh_state,
            fresh_achievements,
            required_mods=self._current_required_mods(),
            mod_data={},
            save_kind=save_kind,
        )
        write_save_slot_data(slot)
        self._apply_save_slot_without_presaving_current(slot, reason="create")
        self._emit_event("save_created", {
            "save_id": slot["id"],
            "save_name": slot["name"],
            "save_kind": slot["save_kind"],
        })
        return slot

    def rename_save_slot(self, save_id: str, new_name: str):
        slot = load_save_slot_data(save_id)
        if not slot:
            return False, "Save could not be renamed."
        slot["name"] = normalize_save_name(new_name)
        slot["updated_at"] = current_save_timestamp()
        backup_save_slot(slot["id"], reason="rename")
        write_save_slot_data(slot)
        if normalize_save_id(save_id) == self.active_save_id:
            self.active_save_name = slot["name"]
            self.active_save_updated_at = slot["updated_at"]
        return True, f"Renamed save to '{slot['name']}'."

    def duplicate_save_slot(self, save_id: str):
        source_id = normalize_save_id(save_id)
        if source_id == self.active_save_id:
            self.save_current_progress(auto_backup=False)
        source = load_save_slot_data(source_id)
        if not source:
            return False, "Save could not be duplicated.", None

        source_name = normalize_save_name(source.get("name") or source_id)
        copy_name = normalize_save_name(f"Copy of {source_name}")
        copy_id = make_save_id(copy_name)
        slot = build_save_slot_data(
            copy_id,
            copy_name,
            source.get("state", DEFAULT_STATE),
            source.get("achievements", DEFAULT_ACHIEVEMENTS),
            required_mods=source.get("required_mods", []),
            mod_data=source.get("mod_data", {}),
            save_kind=source.get("save_kind"),
        )
        write_save_slot_data(slot)
        return True, f"Duplicated save as '{slot['name']}'.", slot

    def delete_save_slot(self, save_id: str):
        target_id = normalize_save_id(save_id)
        if target_id == self.active_save_id:
            return False, "Load another save before deleting the active one."
        slot = load_save_slot_data(target_id)
        if not slot:
            return False, "Save could not be deleted."
        if (
            normalize_save_kind(slot.get("save_kind")) == DEFAULT_SAVE_KIND
            and len(list_save_slots(DEFAULT_SAVE_KIND)) <= 1
        ):
            return False, "Keep at least one normal save."

        backup_save_slot(target_id, reason="predelete")
        try:
            os.unlink(save_slot_path(target_id))
        except Exception as exc:
            return False, f"Failed to delete save: {exc}"
        return True, f"Deleted save '{normalize_save_name(slot.get('name') or target_id)}'. A final backup was kept."

    def export_save_slot(self, save_id: str, export_path: str):
        target_id = normalize_save_id(save_id)
        if target_id == self.active_save_id:
            self.save_current_progress(auto_backup=False)
        slot = load_save_slot_data(target_id)
        if not slot:
            return False, "Save could not be exported."
        try:
            write_json_file(normalize_export_path(export_path), slot)
        except Exception as exc:
            return False, f"Failed to export save: {exc}"
        return True, f"Exported save '{normalize_save_name(slot.get('name') or target_id)}'."

    def import_save_slot(self, import_path: str, expected_save_kind=None):
        try:
            imported = read_save_slot_file(import_path)
        except Exception as exc:
            return False, f"Failed to import save: {exc}", None

        original_name = normalize_save_name(imported.get("name") or "Imported Save")
        imported_kind = normalize_save_kind(imported.get("save_kind"))
        if expected_save_kind is not None:
            expected_kind = normalize_save_kind(expected_save_kind)
            if imported_kind != expected_kind:
                return False, f"This is a {imported_kind} save, not a {expected_kind} save.", None
        imported_id = normalize_save_id(imported.get("id") or make_save_id(original_name))
        save_name = original_name
        if save_slot_exists(imported_id):
            save_name = normalize_save_name(f"{original_name} Imported")
            imported_id = make_save_id(save_name)

        previous = {
            "created_at": imported.get("created_at"),
            "last_auto_backup_at": imported.get("last_auto_backup_at", 0),
            "required_mods": imported.get("required_mods", []),
        }
        slot = build_save_slot_data(
            imported_id,
            save_name,
            imported.get("state", DEFAULT_STATE),
            imported.get("achievements", DEFAULT_ACHIEVEMENTS),
            required_mods=imported.get("required_mods", []),
            mod_data=imported.get("mod_data", {}),
            previous=previous,
            save_kind=imported_kind,
        )
        write_save_slot_data(slot)
        return True, f"Imported save '{slot['name']}'.", slot

    def restore_save_backup(self, save_id: str, backup_path: str, allow_missing_mods=False):
        target_id = normalize_save_id(save_id)
        backup_path = os.path.abspath(str(backup_path or ""))
        allowed_backups = {os.path.abspath(path) for path in list_save_backups(target_id)}
        if backup_path not in allowed_backups:
            return False, "Selected backup could not be found."

        try:
            backup_slot = read_save_slot_file(backup_path)
        except Exception as exc:
            return False, f"Selected backup could not be read: {exc}"

        missing_mods = self._save_slot_missing_mods(backup_slot)
        if target_id == self.active_save_id and missing_mods and not allow_missing_mods:
            return False, "Restored backup needs missing mods: " + ", ".join(missing_mods)

        backup_save_slot(target_id, reason="prerestore")
        try:
            copy_file_bytes(backup_path, save_slot_path(target_id))
        except Exception as exc:
            return False, f"Failed to restore backup: {exc}"

        if target_id == self.active_save_id:
            slot = load_save_slot_data(target_id)
            if not slot:
                return False, "Restored backup could not be loaded."
            self.active_save_name = normalize_save_name(slot.get("name") or target_id)
            self.active_save_kind = normalize_save_kind(slot.get("save_kind"))
            self.active_save_created_at = slot.get("created_at") or current_save_timestamp()
            self.active_save_updated_at = slot.get("updated_at") or self.active_save_created_at
            self.active_save_last_auto_backup_at = slot.get("last_auto_backup_at", 0)
            self.active_save_required_mods = list(slot.get("required_mods", []))
            self.state = clone_json_data(slot.get("state", DEFAULT_STATE))
            self.achievements = clone_json_data(slot.get("achievements", DEFAULT_ACHIEVEMENTS))
            self.save_namespaces = clone_json_data(slot.get("mod_data", {}))
            if not isinstance(self.save_namespaces, dict):
                self.save_namespaces = {}
            self._normalize_progress_after_load()
            self.invalidate_rate_cache()
            self.save_current_progress(auto_backup=False)
            self.update_labels()
            self.refresh_upgrades_ui()
            self.refresh_achievements_ui()
            self.refresh_stats_tab(force=True)
            self._emit_event("load", {
                "save_id": self.active_save_id,
                "save_name": self.active_save_name,
                "save_kind": self.active_save_kind,
                "reason": "restore",
            })
        return True, f"Restored backup {backup_display_name(backup_path)}."

    def restore_latest_save_backup(self, save_id: str):
        latest = latest_save_backup(save_id)
        if not latest:
            return False, "No backup found for this save."
        return self.restore_save_backup(save_id, latest)

    def get_save_namespace(self, namespace=None):
        namespace = self._current_mod_namespace(namespace)
        data = self.save_namespaces.setdefault(namespace, {})
        if not isinstance(data, dict):
            data = {}
            self.save_namespaces[namespace] = data
        return data

    def set_save_namespace(self, namespace=None, data=None):
        if data is None and isinstance(namespace, dict):
            data = namespace
            namespace = None
        namespace = self._current_mod_namespace(namespace)
        self.save_namespaces[namespace] = clone_json_data(data if isinstance(data, dict) else {})
        self.mark_save_dirty(auto_backup=False)

    def get_save_data(self, namespace=None):
        return self.get_save_namespace(namespace)

    def set_save_data(self, data, namespace=None):
        self.set_save_namespace(namespace, data)

    def get_save_value(self, key: str, default=None, namespace=None):
        return self.get_save_namespace(namespace).get(key, default)

    def set_save_value(self, key: str, value, namespace=None):
        data = self.get_save_namespace(namespace)
        data[str(key)] = clone_json_data(value)
        self.mark_save_dirty(auto_backup=False)
        return value

    def delete_save_value(self, key: str, namespace=None):
        data = self.get_save_namespace(namespace)
        if str(key) in data:
            data.pop(str(key), None)
            self.mark_save_dirty(auto_backup=False)
            return True
        return False

    def get_mod_settings(self, namespace=None):
        namespace = self._current_mod_namespace(namespace)
        all_settings = self.settings.setdefault("mod_settings", {})
        if not isinstance(all_settings, dict):
            all_settings = {}
            self.settings["mod_settings"] = all_settings
        data = all_settings.setdefault(namespace, {})
        if not isinstance(data, dict):
            data = {}
            all_settings[namespace] = data
        return data

    def get_mod_setting(self, key: str, default=None, namespace=None):
        return self.get_mod_settings(namespace).get(key, default)

    def set_mod_setting(self, key: str, value, namespace=None):
        data = self.get_mod_settings(namespace)
        data[str(key)] = clone_json_data(value)
        save_json(SETTINGS_FILE, self.settings)
        return value

    def delete_mod_setting(self, key: str, namespace=None):
        data = self.get_mod_settings(namespace)
        if str(key) in data:
            data.pop(str(key), None)
            save_json(SETTINGS_FILE, self.settings)
            return True
        return False
