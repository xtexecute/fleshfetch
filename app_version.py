"""Release identifiers shared by the app and package builders."""

VERSION = "1.5.0-rc1"
WINDOWS_VERSION = VERSION.split("-", 1)[0] + ".0"
DEBIAN_VERSION = VERSION.replace("-rc", "~rc") + "-1"
