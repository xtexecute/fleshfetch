"""Launch an extracted Windows ZIP with a clean PATH and isolated player data."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class ProcessEntry(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("pid", wintypes.DWORD), ("heap", ctypes.c_size_t),
                ("module", wintypes.DWORD), ("threads", wintypes.DWORD),
                ("parent", wintypes.DWORD), ("priority", wintypes.LONG),
                ("flags", wintypes.DWORD), ("exe", wintypes.WCHAR * 260)]


def process_tree(parent):
    kernel = ctypes.windll.kernel32
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessEntry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    entries = []
    entry = ProcessEntry()
    entry.dwSize = ctypes.sizeof(entry)
    ok = kernel.Process32FirstW(handle, ctypes.byref(entry))
    while ok:
        entries.append((entry.pid, entry.parent))
        ok = kernel.Process32NextW(handle, ctypes.byref(entry))
    kernel.CloseHandle(handle)
    owned = {parent}
    for _ in entries:
        children = {pid for pid, owner in entries if owner in owned}
        if children <= owned:
            break
        owned |= children
    return owned


def own_window(pids):
    user = ctypes.windll.user32
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.IsWindowVisible.argtypes = [wintypes.HWND]
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    @callback_type
    def visit(handle, param):
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        if pid.value in pids and user.IsWindowVisible(handle):
            text = ctypes.create_unicode_buffer(512)
            user.GetWindowTextW(handle, text, len(text))
            if text.value == "Flesh Clicker":
                found.append(handle)
        return True
    user.EnumWindows(visit, 0)
    return found[0] if found else None


def main():
    from PySide6.QtGui import QGuiApplication
    app = QGuiApplication([])
    archive = ROOT / "output" / "ff_v1.4.0-rc2_win.zip"
    test_root = ROOT / ".qt-test-data"
    test_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=test_root) as temp:
        base = Path(temp)
        unpacked = base / "portable test"
        with zipfile.ZipFile(archive) as package:
            package.extractall(unpacked)
        release = unpacked / "fleshfetch"
        profile = base / "profile"
        mod = profile / "fleshfetch" / "mods" / "LegacyCompatibilityTest"
        shutil.copytree(ROOT / "example_mods" / "LegacyCompatibilityTest", mod)
        (mod / "enabled.txt").write_text("true\n", encoding="utf-8")
        env = dict(os.environ, APPDATA=str(profile), PATH=os.pathsep.join([
            str(Path(os.environ["WINDIR"]) / "System32"), os.environ["WINDIR"]]))
        for name in list(env):
            if name.startswith(("PYTHON", "QT_", "QML_", "GI_", "GIO_", "GTK_")) or name == "FLESHFETCH_ROOT":
                env.pop(name, None)
        process = subprocess.Popen([str(release / "fleshfetch.exe")], cwd=release, env=env)
        try:
            handle = None
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline and process.poll() is None:
                handle = own_window(process_tree(process.pid))
                if handle:
                    break
                time.sleep(.1)
            if not handle:
                log = profile / "fleshfetch" / "startup.log"
                raise AssertionError(f"No game window; exit={process.poll()}; log={log.read_text(errors='replace') if log.exists() else 'none'}")
            time.sleep(1.2)
            screenshot = app.primaryScreen().grabWindow(int(handle))
            assert not screenshot.isNull()
            screenshot.save(str(ROOT / "output" / "windows-package-smoke.png"))
            user = ctypes.windll.user32
            user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user.PostMessageW(handle, 0x201, 1, (420 << 16) | 160)
            user.PostMessageW(handle, 0x202, 0, (420 << 16) | 160)
            time.sleep(.4)
            user.PostMessageW(handle, 0x10, 0, 0)
            assert process.wait(timeout=20) == 0
            saves = profile / "fleshfetch" / "saves"
            slots = [json.loads(path.read_text(encoding="utf-8")) for path in saves.glob("*.json")]
            assert any(slot.get("state", {}).get("total_clicks", 0) >= 1 for slot in slots), slots
            assert any(any(m.get("id") == "LegacyCompatibilityTest" for m in slot.get("required_mods", []) if isinstance(m, dict)) for slot in slots), slots
            log = profile / "fleshfetch" / "startup.log"
            assert not log.exists() or "Traceback" not in log.read_text(errors="replace")
            print("Extracted ZIP launched with a clean PATH; legacy mod loaded, click and close/save passed.")
        finally:
            if process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
                process.wait(timeout=10)


if __name__ == "__main__":
    main()
