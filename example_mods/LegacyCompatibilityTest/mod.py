"""Intentionally old-fashioned mod for testing the Qt compatibility layer."""

import gi
import cairo
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib


def register(game):
    page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    game.add_tab("legacy_test", "Legacy Test", page)
    status = Gtk.Label(label="Legacy controls loaded", xalign=0)
    page.append(status)
    entry = Gtk.Entry()
    entry.set_placeholder_text("Type here, then press Add")
    entry.set_text("5")
    page.append(entry)
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    page.append(row)
    button = Gtk.Button(label="Add")
    def add(button, currency):
        try:
            amount = float(entry.get_text())
        except ValueError:
            status.set_text("Enter a number")
            return
        game.add_currency(currency, amount)
        status.set_text(f"Added {amount:g} {currency}")
    button.connect("clicked", add, "flesh")
    row.append(button)
    switch = Gtk.Switch()
    switch.set_active(True)
    switch.connect("notify::active", lambda widget, prop: button.set_sensitive(widget.get_active()))
    row.append(switch)
    combo = Gtk.ComboBoxText()
    combo.append("a", "Option A")
    combo.append("b", "Option B")
    combo.set_active_id("a")
    combo.connect("changed", lambda widget: status.set_text(widget.get_active_text()))
    page.append(combo)
    spin = Gtk.SpinButton.new_with_range(0, 1000, 0.5)
    spin.set_value(2.5)
    spin.connect("value-changed", lambda widget: entry.set_text(str(widget.get_value())))
    page.append(spin)
    expander = Gtk.Expander(label="Old text buffer")
    text = Gtk.TextView()
    text.set_editable(False)
    text.set_monospace(True)
    buffer = text.get_buffer()
    buffer.set_text("TextBuffer.set_text works\n", -1)
    buffer.insert(buffer.get_end_iter(), "TextBuffer.insert works", -1)
    expander.set_child(text)
    expander.set_expanded(True)
    page.append(expander)
    counter = [0]
    timer_label = Gtk.Label(label="Timer waiting", xalign=0)
    page.append(timer_label)
    def tick():
        counter[0] += 1
        timer_label.set_text(f"GLib timer ticks: {counter[0]}")
        return True
    GLib.timeout_add(250, tick)
    GLib.idle_add(lambda: status.set_text("GTK imports and GLib idle callback work"))
    game.add_button("legacy_test", "Old add_button alias", lambda button: status.set_text("Legacy alias clicked"))
    game.register_upgrade("legacy_test_click", {
        "name": "Legacy Click", "desc": "Uses the old fpc/fps/type fields",
        "base_cost": 5, "cost_mult": 1.1, "type": "click", "fpc": 2, "fps": 0,
    })
    game.on_flesh_clicked(lambda event: status.set_text("Legacy click event received"))
    game.on_bought(lambda event: status.set_text("Legacy purchase event received"))
    area = Gtk.DrawingArea()
    area.set_content_height(72)
    def draw(widget, cr, width, height):
        cr.set_source_rgb(0.2, 0.7, 0.4)
        cr.rectangle(8, 8, width - 16, height - 16)
        cr.fill()
        cr.set_source_rgb(0, 0, 0)
        cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(14)
        cr.move_to(18, 40)
        cr.show_text("Legacy Cairo drawing on Qt")
    area.set_draw_func(draw)
    page.append(area)
    def dialog_clicked(button):
        dialog = Gtk.Dialog()
        dialog.set_title("Legacy dialog")
        dialog.get_content_area().append(Gtk.Label(label="This is a Qt dialog opened through the old API."))
        dialog.add_button("Close", Gtk.ResponseType.CANCEL)
        dialog.connect("response", lambda widget, response: widget.destroy())
        dialog.present()
    dialog_button = Gtk.Button(label="Test dialog")
    dialog_button.connect("clicked", dialog_clicked)
    page.append(dialog_button)
    game._legacy_test_controls = dict(entry=entry, button=button, switch=switch,
        combo=combo, spin=spin, buffer=buffer, status=status, timer=timer_label)
