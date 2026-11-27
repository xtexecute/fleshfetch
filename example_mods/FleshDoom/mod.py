"""Small libretro host for PrBoom. The engine and game data are separate files."""

import ctypes
from pathlib import Path
import sys


ROOT = Path(MOD_DIR)
WIDTH, HEIGHT = 320, 200
CALLBACK = ctypes.CFUNCTYPE


class GameInfo(ctypes.Structure):
    _fields_ = [("path", ctypes.c_char_p), ("data", ctypes.c_void_p),
                ("size", ctypes.c_size_t), ("meta", ctypes.c_char_p)]


class Variable(ctypes.Structure):
    _fields_ = [("key", ctypes.c_char_p), ("value", ctypes.c_char_p)]


class Geometry(ctypes.Structure):
    _fields_ = [("base_width", ctypes.c_uint), ("base_height", ctypes.c_uint),
                ("max_width", ctypes.c_uint), ("max_height", ctypes.c_uint),
                ("aspect_ratio", ctypes.c_float)]


class Timing(ctypes.Structure):
    _fields_ = [("fps", ctypes.c_double), ("sample_rate", ctypes.c_double)]


class AvInfo(ctypes.Structure):
    _fields_ = [("geometry", Geometry), ("timing", Timing)]


KeyboardEvent = CALLBACK(None, ctypes.c_bool, ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint16)
LogEvent = CALLBACK(None, ctypes.c_int, ctypes.c_char_p)


class LogCallback(ctypes.Structure):
    _fields_ = [("log", LogEvent)]


class KeyboardCallback(ctypes.Structure):
    _fields_ = [("callback", KeyboardEvent)]


QT_TO_RETRO = {
    0x01000000: 27,  # Escape
    0x01000004: 13,  # Return
    0x01000005: 13,  # Keypad Enter
    0x01000012: 276,  # Left
    0x01000013: 273,  # Up
    0x01000014: 275,  # Right
    0x01000015: 274,  # Down
    0x01000020: 304,  # Shift
    0x01000021: 306,  # Control
    0x01000023: 308,  # Alt
}


def _retro_key(qt_key):
    key = QT_TO_RETRO.get(qt_key, qt_key)
    return key + 32 if 65 <= key <= 90 else key


def _find_core():
    names = ("prboom_libretro.dll",) if sys.platform == "win32" else ("prboom_libretro.so",)
    for folder in (ROOT, ROOT / "cores"):
        for name in names:
            candidate = folder / name
            if candidate.is_file():
                return candidate
    return None


def _find_wad():
    for name in ("freedoom1.wad", "freedoom2.wad", "DOOM.WAD", "DOOM2.WAD", "doom.wad", "doom2.wad"):
        candidate = ROOT / name
        if candidate.is_file():
            return candidate
    return None


class DoomCore:
    def __init__(self, core_path, wad_path, surface):
        from PySide6.QtGui import QImage

        self.image_type = QImage
        self.surface = surface
        self.core_path = core_path
        self.wad_path = wad_path
        self.core = ctypes.CDLL(str(core_path))
        self.pixel_format = 0
        self.variables = {}
        self.held_keys = set()
        self.mouse_buttons = set()
        self.mouse_x = self.mouse_y = 0
        self.pending_x = self.pending_y = 0
        self.poll_x = self.poll_y = 0
        self.keyboard_callback = None
        self.log_cb = LogEvent(lambda _level, _message: None)
        self.audio_sink = self.audio_device = None
        self.loaded = self.initialized = False
        self.system_dir = str(ROOT).encode("utf-8")
        self.save_dir = str(ROOT / "saves").encode("utf-8")
        self.content_dir = str(wad_path.parent).encode("utf-8")
        self.core_path_bytes = str(core_path).encode("utf-8")
        self.wad_path_bytes = str(wad_path).encode("utf-8")
        (ROOT / "saves").mkdir(exist_ok=True)

        self.env_cb = CALLBACK(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)(self._environment)
        self.video_cb = CALLBACK(None, ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                                 ctypes.c_size_t)(self._video)
        self.audio_cb = CALLBACK(None, ctypes.c_int16, ctypes.c_int16)(self._audio_sample)
        self.audio_batch_cb = CALLBACK(ctypes.c_size_t, ctypes.c_void_p,
                                       ctypes.c_size_t)(self._audio_batch)
        self.poll_cb = CALLBACK(None)(self._poll)
        self.input_cb = CALLBACK(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint,
                                 ctypes.c_uint, ctypes.c_uint)(self._input)
        self._bind("retro_set_environment", None, type(self.env_cb))(self.env_cb)
        self._bind("retro_set_video_refresh", None, type(self.video_cb))(self.video_cb)
        self._bind("retro_set_audio_sample", None, type(self.audio_cb))(self.audio_cb)
        self._bind("retro_set_audio_sample_batch", None, type(self.audio_batch_cb))(self.audio_batch_cb)
        self._bind("retro_set_input_poll", None, type(self.poll_cb))(self.poll_cb)
        self._bind("retro_set_input_state", None, type(self.input_cb))(self.input_cb)
        self._bind("retro_init", None)()
        self.initialized = True
        info = GameInfo(self.wad_path_bytes, None, 0, None)
        if not self._bind("retro_load_game", ctypes.c_bool, ctypes.POINTER(GameInfo))(ctypes.byref(info)):
            self.stop()
            raise RuntimeError("PrBoom could not load this WAD")
        self.loaded = True
        self._bind("retro_set_controller_port_device", None, ctypes.c_uint, ctypes.c_uint)(0, 3)
        av = AvInfo()
        self._bind("retro_get_system_av_info", None, ctypes.POINTER(AvInfo))(ctypes.byref(av))
        self.fps = max(1, min(120, av.timing.fps or 60))
        self._start_audio(int(av.timing.sample_rate or 44100))

    def _bind(self, name, result, *args):
        fn = getattr(self.core, name)
        fn.restype, fn.argtypes = result, list(args)
        return fn

    def _environment(self, command, data):
        if command == 27:
            ctypes.cast(data, ctypes.POINTER(LogCallback))[0].log = self.log_cb
            return True
        if command in (9, 30, 31, 19):
            value = {9: self.system_dir, 30: self.content_dir,
                     31: self.save_dir, 19: self.core_path_bytes}[command]
            ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))[0] = value
            return True
        if command == 10:
            value = ctypes.cast(data, ctypes.POINTER(ctypes.c_int))[0]
            if value in (0, 1, 2):
                self.pixel_format = value
                return True
        elif command == 3:
            ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))[0] = True
            return True
        elif command == 12:
            self.keyboard_callback = ctypes.cast(data, ctypes.POINTER(KeyboardCallback))[0].callback
            return True
        elif command == 16:
            options = ctypes.cast(data, ctypes.POINTER(Variable))
            for index in range(256):
                option = options[index]
                if not option.key:
                    break
                first = (option.value or b"").partition(b";")[2].strip().split(b"|")[0]
                self.variables[option.key] = b"320x200" if option.key == b"prboom-resolution" else first
            return True
        elif command == 15:
            option = ctypes.cast(data, ctypes.POINTER(Variable))[0]
            value = self.variables.get(option.key)
            if value is not None:
                option.value = value
                return True
        elif command == 17:
            ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))[0] = False
            return True
        elif command == 52:
            ctypes.cast(data, ctypes.POINTER(ctypes.c_uint))[0] = 0
            return True
        return False

    def _video(self, data, width, height, pitch):
        if not data or width != WIDTH or height != HEIGHT or pitch < width * 2:
            return
        formats = {0: self.image_type.Format.Format_RGB555,
                   1: self.image_type.Format.Format_RGB32,
                   2: self.image_type.Format.Format_RGB16}
        pixels = ctypes.string_at(data, pitch * height)
        image = self.image_type(pixels, width, height,
                                pitch, formats[self.pixel_format])
        rgba = image.convertToFormat(self.image_type.Format.Format_RGBA8888)
        self.surface.set_frame(rgba.constBits().tobytes())

    def _start_audio(self, rate):
        try:
            from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
            device = QMediaDevices.defaultAudioOutput()
            if device.isNull():
                return
            format = QAudioFormat()
            format.setSampleRate(rate)
            format.setChannelCount(2)
            format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            if not device.isFormatSupported(format):
                return
            self.audio_sink = QAudioSink(device, format)
            self.audio_sink.setBufferSize(rate // 5 * 4)
            self.audio_device = self.audio_sink.start()
        except Exception as exc:
            print(f"[FleshDoom] Audio unavailable: {exc}")

    def _audio_sample(self, left, right):
        samples = (ctypes.c_int16 * 2)(left, right)
        self._audio_batch(ctypes.addressof(samples), 1)

    def _audio_batch(self, data, frames):
        if self.audio_device is not None and data:
            count = frames * 4
            if self.audio_sink.bytesFree() >= count:
                self.audio_device.write(ctypes.string_at(data, count))
        return frames

    def _poll(self):
        self.poll_x, self.poll_y = self.pending_x, self.pending_y
        self.pending_x = self.pending_y = 0

    def _input(self, port, device, index, input_id):
        if port != 0:
            return 0
        if device == 3:
            return int(input_id in self.held_keys)
        if device == 2:
            if input_id == 0:
                return max(-32768, min(32767, self.poll_x))
            if input_id == 1:
                return max(-32768, min(32767, self.poll_y))
            return int(input_id in self.mouse_buttons)
        if device == 1:
            controls = {0: 32, 3: 27, 4: 273, 5: 274, 6: 276, 7: 275,
                        8: 306, 9: 304}
            return int(controls.get(input_id) in self.held_keys)
        return 0

    def key(self, event):
        key = _retro_key(event["key"])
        if event["pressed"]:
            self.held_keys.add(key)
        else:
            self.held_keys.discard(key)
        if self.keyboard_callback:
            self.keyboard_callback(bool(event["pressed"]), key,
                                   key if 32 <= key < 127 else 0, 0)

    def pointer(self, event):
        if event["kind"] == "move":
            self.pending_x += event["x"] - self.mouse_x
            self.pending_y += event["y"] - self.mouse_y
        self.mouse_x, self.mouse_y = event["x"], event["y"]
        button = {1: 2, 2: 3, 4: 6}.get(event["button"])
        if button is not None:
            if event["kind"] == "press":
                self.mouse_buttons.add(button)
            elif event["kind"] == "release":
                self.mouse_buttons.discard(button)

    def run(self):
        self._bind("retro_run", None)()

    def stop(self):
        if self.loaded:
            self._bind("retro_unload_game", None)()
            self.loaded = False
        if self.initialized:
            self._bind("retro_deinit", None)()
            self.initialized = False
        if self.audio_sink is not None:
            self.audio_sink.stop()
            self.audio_sink = self.audio_device = None


def register(game):
    tab = game.add_tab("fleshdoom", "DOOM")
    if not hasattr(game, "create_surface"):
        tab.add_label("DOOM needs the Qt frontend.")
        return
    core_path, wad_path = _find_core(), _find_wad()
    if core_path is None or wad_path is None:
        tab.add_label("Put a PrBoom libretro core and a DOOM-compatible WAD in this mod's folder, then reload mods.")
        print("[FleshDoom] Missing PrBoom core or WAD. See README.md in the mod folder.")
        return

    session = {"core": None, "timer": None}

    def key(event):
        if session["core"] is not None:
            session["core"].key(event)

    def pointer(event):
        if session["core"] is not None:
            session["core"].pointer(event)

    surface = game.create_surface("fleshdoom", WIDTH, HEIGHT,
                                  on_key=key, on_pointer=pointer)

    def stop(_button=None):
        if session["timer"] is not None:
            game.cancel_timer(session["timer"])
            session["timer"] = None
        if session["core"] is not None:
            session["core"].stop()
            session["core"] = None
        start_button.set_sensitive(True)
        stop_button.set_sensitive(False)

    def tick():
        if session["core"] is None:
            return False
        try:
            session["core"].run()
        except Exception as exc:
            print(f"[FleshDoom] Core stopped: {exc}")
            stop()
            return False
        return True

    def start(_button=None):
        if session["core"] is not None:
            return
        try:
            session["core"] = DoomCore(core_path, wad_path, surface)
            session["timer"] = game.set_timer(1 / session["core"].fps, tick)
            start_button.set_sensitive(False)
            stop_button.set_sensitive(True)
        except Exception as exc:
            print(f"[FleshDoom] Could not start: {exc}")
            stop()

    start_button = tab.add_button("Start DOOM", start)
    stop_button = tab.add_button("Stop DOOM", stop)
    stop_button.set_sensitive(False)
    tab.add_label("Click the game view for keyboard control. Arrow keys move, Ctrl fires, Space opens doors, Esc opens the menu.")

    class SessionCleanup:
        def cleanup(self):
            stop()

    game.register_api("fleshdoom_session", SessionCleanup(), version="0.1.0")
