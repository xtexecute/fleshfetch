import cairo
import gi


gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
try:
    gi.require_version("GdkPixbuf", "2.0")
except ValueError:
    pass
gi.require_foreign("cairo")

from gi.repository import Gdk, Gio, GLib, Gtk

try:
    from gi.repository import GdkPixbuf
except (ImportError, ValueError):
    GdkPixbuf = None
