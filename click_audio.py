"""Cache small playback-rate variants for low-latency click sounds."""

from functools import lru_cache
import hashlib
import os
from pathlib import Path
import threading
import wave


PITCH_SPREAD = {"default": 0.03, "organic": 0.05, "mechanical": 0.02}


def _cache_dir():
    if os.name == "nt":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or Path.home()
    else:
        root = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(root) / "fleshfetch" / "audio"


@lru_cache(maxsize=32)
def _build_variants(source, profile, mtime_ns, size, cache_dir):
    spread = PITCH_SPREAD[profile]
    with wave.open(source, "rb") as audio:
        params = audio.getparams()
        frames = audio.readframes(params.nframes)
    cache = Path(cache_dir)
    cache.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(f"{source}:{mtime_ns}:{size}".encode()).hexdigest()[:16]
    paths = []
    for step in range(-3, 4):
        if step == 0:
            paths.append(source)
            continue
        target = cache / f"{fingerprint}-{profile}-{step:+d}.wav"
        if not target.exists():
            temporary = target.with_name(f"{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
            try:
                with wave.open(str(temporary), "wb") as output:
                    output.setparams(params._replace(
                        framerate=round(params.framerate * (1 + spread * step / 3))))
                    output.writeframes(frames)
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        paths.append(str(target))
    return tuple(paths)


def pitch_variant_paths(path, profile="default", cache_dir=None):
    """Return seven WAVs spanning the profile's pitch range, or the source alone."""
    if profile not in PITCH_SPREAD:
        raise ValueError(f"Unknown click pitch profile: {profile}")
    source = os.path.abspath(os.fspath(path))
    try:
        stat = os.stat(source)
        return _build_variants(source, profile, stat.st_mtime_ns, stat.st_size,
                               str(cache_dir or _cache_dir()))
    except (OSError, wave.Error):
        return (source,)
