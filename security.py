import ast
import hashlib
import os

# ---------- MOD SECURITY SCAN ----------

MOD_SECURITY_MAX_FILE_BYTES = 512 * 1024
MOD_SECURITY_MAX_REASONS = 20
MOD_SECURITY_DISMISSAL_VERSION = 2
MOD_SECURITY_PY_EXTENSIONS = {".py", ".pyw"}
MOD_SECURITY_LEVEL_NAMES = {
    0: "Safe",
    1: "Suspicious",
    2: "Extremely Suspicious",
}
MOD_SECURITY_WARN_PAYLOAD_EXTENSIONS = {
    ".bat", ".cmd", ".com", ".dll", ".exe", ".hta", ".js", ".msi",
    ".ps1", ".pyd", ".scr", ".vbs",
}

MOD_SECURITY_IMPORT_WARNINGS = {
    "aiohttp": (1, "network access", "network"),
    "base64": (1, "obfuscation helper", "base64"),
    "builtins": (1, "dynamic code access", "dynamic"),
    "cffi": (1, "native code access", "native"),
    "comtypes": (1, "Windows COM/native access", "native"),
    "ctypes": (1, "native OS access", "ctypes"),
    "dill": (1, "code/object loading", "dynamic"),
    "ftplib": (1, "network exfiltration", "network"),
    "http": (1, "network access", "network"),
    "imaplib": (1, "network exfiltration", "network"),
    "importlib": (1, "dynamic imports", "dynamic_import"),
    "marshal": (1, "obfuscated code loading", "dynamic"),
    "multiprocessing": (1, "process spawning", "process"),
    "pickle": (1, "unsafe object loading", "dynamic"),
    "poplib": (1, "network exfiltration", "network"),
    "pyperclip": (1, "clipboard access", "clipboard"),
    "requests": (1, "network access", "network"),
    "runpy": (1, "dynamic code execution", "dynamic_exec"),
    "shutil": (1, "filesystem modification", "filesystem"),
    "smtplib": (1, "network exfiltration", "network"),
    "socket": (1, "network access", "network"),
    "ssl": (1, "network access", "network"),
    "subprocess": (1, "process spawning", "process"),
    "telnetlib": (1, "network exfiltration", "network"),
    "urllib": (1, "network access", "network"),
    "webbrowser": (1, "external process launch", "process"),
    "websocket": (1, "network access", "network"),
    "websockets": (1, "network access", "network"),
    "win32api": (1, "Windows API access", "win32_api"),
    "win32clipboard": (1, "clipboard access", "clipboard"),
    "win32con": (1, "Windows API access", "win32_api"),
    "win32gui": (1, "Windows API access", "win32_api"),
    "winreg": (1, "registry modification", "registry"),
    "keyboard": (2, "keyboard capture", "input_capture"),
    "mouse": (2, "mouse capture", "input_capture"),
    "pyhook": (2, "keyboard hooks", "input_capture"),
    "pywinhook": (2, "keyboard hooks", "input_capture"),
    "pynput": (2, "keyboard/mouse capture", "input_capture"),
    "win32process": (2, "process access", "win32_process"),
}

MOD_SECURITY_CALL_WARNINGS = {
    "__import__": (1, "dynamic imports", "dynamic_import"),
    "compile": (1, "dynamic code compilation", "dynamic_exec"),
    "eval": (1, "dynamic code execution", "dynamic_exec"),
    "exec": (1, "dynamic code execution", "dynamic_exec"),
    "importlib.import_module": (1, "dynamic imports", "dynamic_import"),
    "os.execl": (1, "process replacement", "process"),
    "os.execle": (1, "process replacement", "process"),
    "os.execlp": (1, "process replacement", "process"),
    "os.execlpe": (1, "process replacement", "process"),
    "os.execv": (1, "process replacement", "process"),
    "os.execve": (1, "process replacement", "process"),
    "os.execvp": (1, "process replacement", "process"),
    "os.execvpe": (1, "process replacement", "process"),
    "os.fork": (1, "process spawning", "process"),
    "os.kill": (1, "process control", "process"),
    "os.popen": (1, "process spawning", "process"),
    "os.remove": (1, "file deletion", "filesystem"),
    "os.removedirs": (1, "file deletion", "filesystem"),
    "os.rename": (1, "filesystem modification", "filesystem"),
    "os.replace": (1, "filesystem modification", "filesystem"),
    "os.rmdir": (1, "file deletion", "filesystem"),
    "os.spawnl": (1, "process spawning", "process"),
    "os.spawnle": (1, "process spawning", "process"),
    "os.spawnlp": (1, "process spawning", "process"),
    "os.spawnlpe": (1, "process spawning", "process"),
    "os.spawnv": (1, "process spawning", "process"),
    "os.spawnve": (1, "process spawning", "process"),
    "os.spawnvp": (1, "process spawning", "process"),
    "os.spawnvpe": (1, "process spawning", "process"),
    "os.startfile": (1, "external process launch", "process"),
    "os.system": (1, "shell command execution", "process"),
    "os.unlink": (1, "file deletion", "filesystem"),
    "pathlib.Path.chmod": (1, "filesystem permission changes", "filesystem"),
    "pathlib.Path.rename": (1, "filesystem modification", "filesystem"),
    "pathlib.Path.replace": (1, "filesystem modification", "filesystem"),
    "pathlib.Path.rmdir": (1, "file deletion", "filesystem"),
    "pathlib.Path.unlink": (1, "file deletion", "filesystem"),
    "runpy.run_module": (1, "dynamic code execution", "dynamic_exec"),
    "runpy.run_path": (1, "dynamic code execution", "dynamic_exec"),
    "requests.delete": (1, "network request", "network"),
    "requests.get": (1, "network request", "network"),
    "requests.patch": (1, "network request", "network"),
    "requests.post": (1, "network request", "network"),
    "requests.put": (1, "network request", "network"),
    "socket.create_connection": (1, "network connection", "network"),
    "socket.socket": (1, "network socket", "network"),
    "subprocess.call": (1, "process spawning", "process"),
    "subprocess.check_call": (1, "process spawning", "process"),
    "subprocess.check_output": (1, "process spawning", "process"),
    "subprocess.Popen": (1, "process spawning", "process"),
    "subprocess.run": (1, "process spawning", "process"),
}

MOD_SECURITY_TEXT_WARNINGS = {
    "__import__": (1, "dynamic imports", "dynamic_import"),
    "__globals__": (2, "runtime object graph access", "object_escape"),
    "__mro__": (2, "runtime object graph access", "object_escape"),
    "__subclasses__": (2, "runtime object graph access", "object_escape"),
    "b64decode": (1, "base64 decoding", "base64"),
    "discord.com/api/webhooks": (2, "webhook exfiltration", "network"),
    "getasynckeystate": (2, "keyboard polling", "input_capture"),
    "keyboard.listener": (2, "keyboard capture", "input_capture"),
    "read_key": (2, "keyboard capture", "input_capture"),
    "setwindowshookex": (2, "Windows keyboard hooks", "input_capture"),
    "startup folder": (2, "persistence behavior", "persistence"),
    "sys.modules": (2, "module registry access", "module_registry"),
    "wh_keyboard_ll": (2, "low-level keyboard hook", "input_capture"),
}


def _mod_security_add_warning(warnings: list, level: int, reason: str, feature: str = ""):
    item = (max(0, min(2, int(level))), reason, feature)
    if item not in warnings:
        warnings.append(item)


def _mod_security_module_root(module_name: str) -> str:
    return (module_name or "").split(".", 1)[0].lower()


def _mod_security_resolve_name(node, aliases: dict):
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _mod_security_resolve_name(node.value, aliases)
        if base:
            return f"{base}.{node.attr}"
    if isinstance(node, ast.Call):
        return _mod_security_resolve_name(node.func, aliases)
    return ""


def _mod_security_const_string(node, constants: dict):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _mod_security_const_string(node.left, constants)
        right = _mod_security_const_string(node.right, constants)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif isinstance(value, ast.FormattedValue):
                part = _mod_security_const_string(value.value, constants)
                if part is None:
                    return None
                parts.append(part)
            else:
                return None
        return "".join(parts)
    return None


def _mod_security_dangerous_attr_level(full_name: str):
    if not full_name:
        return None
    if full_name in MOD_SECURITY_CALL_WARNINGS:
        return MOD_SECURITY_CALL_WARNINGS[full_name]
    attr = full_name.rsplit(".", 1)[-1].lower()
    dangerous_attrs = {
        "popen": (1, "dynamic process launch resolved through getattr", "process"),
        "remove": (1, "file deletion resolved through getattr", "filesystem"),
        "rename": (1, "filesystem modification resolved through getattr", "filesystem"),
        "replace": (1, "filesystem modification resolved through getattr", "filesystem"),
        "rmdir": (1, "file deletion resolved through getattr", "filesystem"),
        "run": (1, "process launch resolved through getattr", "process"),
        "startfile": (1, "external process launch resolved through getattr", "process"),
        "system": (1, "shell command execution resolved through getattr", "process"),
        "unlink": (1, "file deletion resolved through getattr", "filesystem"),
    }
    return dangerous_attrs.get(attr)


def _mod_security_sys_modules_name(node, aliases: dict, constants: dict):
    if isinstance(node, ast.Call):
        call_name = _mod_security_resolve_name(node.func, aliases)
        if call_name == "sys.modules.get" and node.args:
            return _mod_security_const_string(node.args[0], constants)
    if isinstance(node, ast.Subscript):
        target_name = _mod_security_resolve_name(node.value, aliases)
        if target_name == "sys.modules":
            return _mod_security_const_string(node.slice, constants)
    return None


def _mod_security_open_writes(call_node: ast.Call) -> bool:
    mode_node = None
    if len(call_node.args) >= 2:
        mode_node = call_node.args[1]
    for keyword in call_node.keywords:
        if keyword.arg == "mode":
            mode_node = keyword.value
            break
    if not isinstance(mode_node, ast.Constant) or not isinstance(mode_node.value, str):
        return False
    return any(flag in mode_node.value for flag in ("w", "a", "x", "+"))


def _mod_security_check_ast(tree, rel_path: str):
    warnings = []
    features = set()
    aliases = {}
    constants = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                root = _mod_security_module_root(module_name)
                aliases[alias.asname or root] = module_name
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                aliases[alias.asname or alias.name] = full_name

    for node in ast.walk(tree):
        targets = []
        value = None
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        if value is None:
            continue

        const_value = _mod_security_const_string(value, constants)
        for target in targets:
            if isinstance(target, ast.Name) and const_value is not None:
                constants[target.id] = const_value
        if const_value is not None:
            lowered_const = const_value.lower()
            if "discord.com/api/webhooks" in lowered_const:
                features.add("network")
                _mod_security_add_warning(
                    warnings,
                    2,
                    f"{rel_path}:{node.lineno}: reconstructed Discord webhook URL",
                    "network",
                )
            elif lowered_const.startswith(("http://", "https://")):
                features.add("network")
                _mod_security_add_warning(
                    warnings,
                    1,
                    f"{rel_path}:{node.lineno}: reconstructed URL string",
                    "network",
                )

        modules_name = _mod_security_sys_modules_name(value, aliases, constants)
        if modules_name:
            for target in targets:
                if isinstance(target, ast.Name):
                    aliases[target.id] = modules_name
            root = _mod_security_module_root(modules_name)
            level, reason, feature = MOD_SECURITY_IMPORT_WARNINGS.get(
                root,
                (2, "module registry access", "module_registry"),
            )
            features.add(feature)
            _mod_security_add_warning(
                warnings,
                max(2, level),
                f"{rel_path}:{node.lineno}: accesses already-loaded module '{modules_name}' through sys.modules ({reason})",
                feature,
            )

        if isinstance(value, ast.Call) and _mod_security_resolve_name(value.func, aliases) == "getattr":
            if len(value.args) >= 2:
                base_name = _mod_security_resolve_name(value.args[0], aliases)
                attr_name = _mod_security_const_string(value.args[1], constants)
                if attr_name:
                    full_name = f"{base_name}.{attr_name}" if base_name else attr_name
                    for target in targets:
                        if isinstance(target, ast.Name):
                            aliases[target.id] = full_name
                    danger = _mod_security_dangerous_attr_level(full_name)
                    if danger:
                        level, reason, feature = danger
                        features.add(feature)
                        _mod_security_add_warning(
                            warnings,
                            max(2, level),
                            f"{rel_path}:{node.lineno}: resolves dangerous attribute '{full_name}' through getattr ({reason})",
                            feature,
                        )
                else:
                    features.add("dynamic_attr")
                    _mod_security_add_warning(
                        warnings,
                        1,
                        f"{rel_path}:{node.lineno}: dynamic getattr with non-literal attribute",
                        "dynamic_attr",
                    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name
                root = _mod_security_module_root(module_name)
                aliases[alias.asname or root] = module_name
                if root in MOD_SECURITY_IMPORT_WARNINGS:
                    level, reason, feature = MOD_SECURITY_IMPORT_WARNINGS[root]
                    features.add(feature)
                    _mod_security_add_warning(
                        warnings,
                        level,
                        f"{rel_path}:{node.lineno}: import '{module_name}' ({reason})",
                        feature,
                    )
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            root = _mod_security_module_root(module_name)
            for alias in node.names:
                full_name = f"{module_name}.{alias.name}" if module_name else alias.name
                aliases[alias.asname or alias.name] = full_name
            if root in MOD_SECURITY_IMPORT_WARNINGS:
                level, reason, feature = MOD_SECURITY_IMPORT_WARNINGS[root]
                features.add(feature)
                _mod_security_add_warning(
                    warnings,
                    level,
                    f"{rel_path}:{node.lineno}: import '{module_name}' ({reason})",
                    feature,
                )
        elif isinstance(node, ast.Call):
            call_name = _mod_security_resolve_name(node.func, aliases)
            if call_name in MOD_SECURITY_CALL_WARNINGS:
                level, reason, feature = MOD_SECURITY_CALL_WARNINGS[call_name]
                features.add(feature)
                _mod_security_add_warning(
                    warnings,
                    level,
                    f"{rel_path}:{node.lineno}: call '{call_name}' ({reason})",
                    feature,
                )
            elif call_name == "open" and _mod_security_open_writes(node):
                features.add("filesystem")
                _mod_security_add_warning(
                    warnings,
                    1,
                    f"{rel_path}:{node.lineno}: writable file open",
                    "filesystem",
                )
            elif call_name == "getattr":
                if len(node.args) >= 2:
                    base_name = _mod_security_resolve_name(node.args[0], aliases)
                    attr_name = _mod_security_const_string(node.args[1], constants)
                    full_name = f"{base_name}.{attr_name}" if base_name and attr_name else ""
                    danger = _mod_security_dangerous_attr_level(full_name)
                    if danger:
                        level, reason, feature = danger
                        features.add(feature)
                        _mod_security_add_warning(
                            warnings,
                            max(2, level),
                            f"{rel_path}:{node.lineno}: resolves dangerous attribute '{full_name}' through getattr ({reason})",
                            feature,
                        )
                    elif attr_name:
                        features.add("dynamic_attr")
                        _mod_security_add_warning(
                            warnings,
                            1,
                            f"{rel_path}:{node.lineno}: dynamic getattr for attribute '{attr_name}'",
                            "dynamic_attr",
                        )
                    else:
                        features.add("dynamic_attr")
                        _mod_security_add_warning(
                            warnings,
                            1,
                            f"{rel_path}:{node.lineno}: dynamic getattr with non-literal attribute",
                            "dynamic_attr",
                        )
            modules_name = _mod_security_sys_modules_name(node, aliases, constants)
            if modules_name:
                root = _mod_security_module_root(modules_name)
                level, reason, feature = MOD_SECURITY_IMPORT_WARNINGS.get(
                    root,
                    (2, "module registry access", "module_registry"),
                )
                features.add(feature)
                _mod_security_add_warning(
                    warnings,
                    max(2, level),
                    f"{rel_path}:{node.lineno}: accesses already-loaded module '{modules_name}' through sys.modules ({reason})",
                    feature,
                )
        elif isinstance(node, ast.Attribute):
            attr_name = _mod_security_resolve_name(node, aliases)
            if attr_name == "sys.modules":
                features.add("module_registry")
                _mod_security_add_warning(
                    warnings,
                    2,
                    f"{rel_path}:{node.lineno}: accesses sys.modules module registry",
                    "module_registry",
                )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered_const = node.value.lower()
            if lowered_const.startswith(("http://", "https://")):
                features.add("network")
                _mod_security_add_warning(
                    warnings,
                    1,
                    f"{rel_path}:{node.lineno}: URL literal",
                    "network",
                )

    return warnings, features


def scan_mod_security(mod_dir: str) -> dict:
    """Return warning level, reasons, and fingerprint for a mod folder."""
    warnings = []
    features = set()
    python_files = []
    fingerprint = hashlib.sha256()
    fingerprint.update(f"fleshfetch-mod-security-v{MOD_SECURITY_DISMISSAL_VERSION}\n".encode("utf-8"))

    for root, dirs, files in os.walk(mod_dir):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", ".hg", ".svn"}]
        for filename in files:
            path = os.path.join(root, filename)
            rel_path = os.path.relpath(path, mod_dir)
            ext = os.path.splitext(filename)[1].lower()
            fingerprint.update(rel_path.replace("\\", "/").encode("utf-8", errors="replace"))
            fingerprint.update(b"\0")
            if ext in MOD_SECURITY_WARN_PAYLOAD_EXTENSIONS:
                try:
                    fingerprint.update(str(os.path.getsize(path)).encode("ascii"))
                    fingerprint.update(b"\0")
                    with open(path, "rb") as payload:
                        while True:
                            chunk = payload.read(65536)
                            if not chunk:
                                break
                            fingerprint.update(chunk)
                except Exception:
                    fingerprint.update(b"unreadable-payload")
                features.add("native_payload")
                _mod_security_add_warning(
                    warnings,
                    2,
                    f"{rel_path}: bundled executable/native payload '{ext}'",
                    "native_payload",
                )
            if ext in MOD_SECURITY_PY_EXTENSIONS:
                python_files.append((path, rel_path))

    for path, rel_path in sorted(python_files):
        try:
            size = os.path.getsize(path)
            fingerprint.update(str(size).encode("ascii"))
            fingerprint.update(b"\0")
        except Exception:
            _mod_security_add_warning(warnings, 1, f"{rel_path}: could not inspect file size")
            continue
        if size > MOD_SECURITY_MAX_FILE_BYTES:
            _mod_security_add_warning(warnings, 1, f"{rel_path}: Python file is too large to scan safely")
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
        except Exception as exc:
            _mod_security_add_warning(warnings, 1, f"{rel_path}: could not read file ({exc})")
            continue
        fingerprint.update(source.encode("utf-8", errors="replace"))

        lowered = source.lower()
        for needle, data in MOD_SECURITY_TEXT_WARNINGS.items():
            if needle in lowered:
                level, reason, feature = data
                features.add(feature)
                _mod_security_add_warning(
                    warnings,
                    level,
                    f"{rel_path}: text pattern '{needle}' ({reason})",
                    feature,
                )

        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError as exc:
            line = exc.lineno or "?"
            _mod_security_add_warning(warnings, 1, f"{rel_path}:{line}: syntax error during security scan")
            continue
        ast_warnings, ast_features = _mod_security_check_ast(tree, rel_path)
        warnings.extend(ast_warnings)
        features.update(ast_features)

    if "base64" in features and "dynamic_exec" in features:
        _mod_security_add_warning(
            warnings,
            2,
            "base64 decoding combined with dynamic code execution",
            "combo",
        )
    if "network" in features and ("dynamic_exec" in features or "dynamic_import" in features):
        _mod_security_add_warning(
            warnings,
            2,
            "network access combined with dynamic code loading",
            "combo",
        )
    if "ctypes" in features and ("win32_process" in features or "win32_api" in features):
        _mod_security_add_warning(
            warnings,
            2,
            "ctypes combined with Windows process/API access",
            "combo",
        )

    level = max((item[0] for item in warnings), default=0)
    reasons = []
    for item_level, reason, _feature in warnings:
        label = MOD_SECURITY_LEVEL_NAMES.get(item_level, "Suspicious")
        text = f"Level {item_level} {label}: {reason}"
        if text not in reasons:
            reasons.append(text)

    return {
        "level": level,
        "label": MOD_SECURITY_LEVEL_NAMES.get(level, "Suspicious"),
        "reasons": reasons[:MOD_SECURITY_MAX_REASONS],
        "fingerprint": fingerprint.hexdigest(),
    }
