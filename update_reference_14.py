"""Preserve the existing reference and add the Qt 1.4 UI documentation."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                               Preformatted, Table, TableStyle, KeepTogether)

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf"
OLD = ROOT / "docs" / "reference-core-1.3.2.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("Body14", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=8))
styles.add(ParagraphStyle("Code14", fontName="Courier", fontSize=8.3, leading=11,
                         backColor=colors.HexColor("#f2f2f2"), borderPadding=9,
                         spaceBefore=5, spaceAfter=14))
styles.add(ParagraphStyle("Cover14", fontName="Helvetica-Bold", fontSize=26, leading=32, spaceAfter=16))


def para(text):
    return Paragraph(escape(text), styles["Body14"])


def heading(text):
    return Paragraph(escape(text), styles["Heading2"])


def code(text):
    return Preformatted(text.strip(), styles["Code14"])


def table(rows, widths):
    data = [[para(str(value)) for value in row] for row in rows]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
                               ("GRID", (0, 0), (-1, -1), .4, colors.HexColor("#bbbbbb")),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("LEFTPADDING", (0, 0), (-1, -1), 8),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                               ("TOPPADDING", (0, 0), (-1, -1), 7)]))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    pages += [heading("23. Framework Tabs and Buttons"),
        para("New UI code should use game methods and the handles they return. These controls use the current theme without importing GTK or Qt."),
        code('''def register(game):
    garden = game.add_tab("garden", "Garden")
    garden.add_label("Seeds")

    def plant(button):
        game.add_currency("flesh", 1)

    garden.add_button("Plant", plant)
    game.add_tab_button("garden", "Plant again", plant)'''),
        para("Callbacks receive the button handle. add_tab_button also accepts built-in tab IDs: upgrades, saves, stats, achievements, settings, console and leaderboard."),
        para("Named buttons use the new add_button form. The button ID must be unique within the mod. The older add_button(tab_id, label, callback) form still works and emits a deprecation warning."),
        code('''button = game.add_button(
    "plant", tab="garden", text="Plant", on_click=plant,
)
button.set_label("Plant seed")
button.set_sensitive(False)
button.set_tooltip_text("Needs a seed")
button.hide()
button.show()'''),
        para("Use button.remove() or tab.remove() to remove framework controls. A mod reload removes controls owned by the unloaded mods."), PageBreak(),
        heading("24. Tab-Specific Colors"),
        para("set_tab_theme changes only the supplied colors. Omitted colors inherit the player's Light, Dark or System appearance. Colors use #RRGGBB."),
        code('''game.set_tab_theme(
    "garden",
    canvas="#142820", surface="#224030",
    raised="#2b4d39", hover="#386848",
    pressed="#1b3c29", accent="#48ba78",
    text="#e0ffe8", muted="#accbb7",
)
# The returned tab handle also supports:
garden.set_theme(accent="#48ba78", text="#e0ffe8")'''),
        table([["Colors", "Use"], ["canvas, surface", "Page and panel backgrounds."],
               ["raised, hover, pressed", "Standard button states."],
               ["text, muted", "Normal and secondary text."],
               ["accent, accentHover", "Pixel borders and hover accents."],
               ["line, focus, warning, danger", "Other palette entries used by controls."]], [165, 330]),
        Spacer(1, 10), para("The active tab's palette also colors the surrounding window. Each tab header uses its own palette. Custom button artwork keeps the colors drawn in its spritesheet."),
        para("When multiple mods override the same tab color, the last registered value wins. Calling set_tab_theme with no colors removes that mod's override. Mod reload clears mod-owned overrides."),
        code('''game.set_tab_theme("garden")  # remove this mod's override'''), PageBreak(),
        heading("25. Nine-Slice Button Spritesheets"),
        para("Draw the button states in one image. For this example, use a 192 by 48 PNG containing four 48 by 48 states placed side by side."),
        code('''game.add_button(
    "plant", tab="garden", text="Plant",
    sprites={
        "sheet": "assets/buttons.png",
        "border": 8,
        "normal": [0, 0, 48, 48],
        "hover": [48, 0, 48, 48],
        "pressed": [96, 0, 48, 48],
        "disabled": [144, 0, 48, 48],
    },
    on_click=plant,
)'''),
        para("Each region is [x, y, width, height] in source pixels. The origin is the sheet's top-left corner. Regions must fit within the image, and the borders must fit inside each region."),
        table([["Part", "Resizing behavior"], ["Four corners", "Keep their size."],
               ["Top and bottom edges", "Stretch horizontally."], ["Left and right edges", "Stretch vertically."],
               ["Center", "Stretches in both directions."]], [165, 330]),
        Spacer(1, 10), para("With border 8, the corners are 8 by 8 pixels and the center is 32 by 32 pixels. Keep important decoration out of the center if it must not stretch. Use the same region size for all states."),
        para("For unequal borders, replace the integer with a mapping:"),
        code('''"border": {"left": 8, "top": 6, "right": 8, "bottom": 6}'''), PageBreak(),
        heading("25. Nine-Slice Buttons (Continued)"),
        para("Separate images also work. Omit sheet and give paths for the states. Paths are resolved relative to the owning mod's folder."),
        code('''button = game.add_button(
    "plant", tab="garden", text="Plant",
    sprites={
        "border": 8,
        "normal": "assets/plant.png",
        "hover": "assets/plant_hover.png",
        "pressed": "assets/plant_pressed.png",
        "disabled": "assets/plant_disabled.png",
    },
    on_click=plant,
)'''),
        para("Text is drawn over the sprite. A missing hover, pressed or disabled state falls back to normal. An image that cannot be loaded uses the standard button frame. Pixel filtering is disabled."),
        para("Use button.set_sprites({...}) to replace the complete skin later. The old set_sprite(path, hover=None, pressed=None, disabled=None) method is also available."),
        heading("26. Sprite Movement"),
        para("Sprite changes are sent to persistent Qt image items on a separate 16 ms update path. Game statistics do not need rebuilding for every movement frame."),
        code('''sprite = game.create_sprite(
    "assets/logo.png", size=(120, 60), pos=(20, 20),
)
sprite.set_velocity(80, 40)  # pixels per second
sprite.set_rotation(15)
sprite.set_opacity(0.8)'''),
        para("Calling step() or bounce() selects manual motion. This preserves older mods that advance their own physics and then store a velocity for reporting. The frontend does not move those sprites a second time."),
        code('''sprite.step(0.016)          # manual elapsed-time step
sprite.bounce(2, 1)          # manual per-call displacement
sprite.set_auto_motion(True)  # resume velocity-driven movement'''), PageBreak(),
        heading("27. Legacy Compatibility"),
        para("Common older GTK interfaces run through a compatibility adapter. It translates their controls and callbacks into Qt; it does not install or launch GTK."),
        table([["Older feature", "Qt behavior"],
               ["Gtk.Box, Grid, Label, Button", "Nested layouts, text and button callbacks."],
               ["Entry, ComboBoxText, Switch, SpinButton", "Editable values and change signals."],
               ["TextView, TextBuffer, Expander", "Text buffers and expandable content."],
               ["Dialog, FileChooserNative", "Qt dialogs and file selection."],
               ["GLib timers and idle callbacks", "Qt scheduling with mod ownership and cleanup."],
               ["Motion and drag controllers", "Pointer events mapped to the game area."],
               ["Common Cairo paths and text", "Translated into QPainter drawing."],
               ["GTK CSS and advanced Cairo APIs", "Need porting; not the full GTK/Cairo runtime."]], [185, 310]),
        Spacer(1, 12), para("GTK CSS class requests produce deprecation warnings. They do not apply GTK styling to Qt controls. Use set_tab_theme and button skins instead. Direct native widget access and Cairo image surfaces are not provided by this adapter."),
        para("Legacy warnings appear in bright yellow in the console. The mod list marks mods that use deprecated features. A security warning is separate from a compatibility warning."),
    ]
    additions = BytesIO()
    SimpleDocTemplate(additions, pagesize=A4, leftMargin=48, rightMargin=48,
                      topMargin=42, bottomMargin=44).build(pages)
    writer = PdfWriter()
    for source in (OLD, additions):
        writer.append(PdfReader(source))
    writer.add_metadata({"/Title": "Fleshfetch 1.4 Modding Reference", "/Subject": "Core mod API and Qt UI"})
    final = OUT / "ff-v1.4_modding_reference.pdf"
    with final.open("wb") as stream:
        writer.write(stream)
    import pypdfium2 as pdfium
    document = pdfium.PdfDocument(str(final))
    for index in (0, 15, 16, 17, 18, len(document)-1):
        document[index].render(scale=1.25).to_pil().save(OUT / f"reference-review-{index+1}.png")
    print(f"{final} ({len(document)} pages)")


if __name__ == "__main__":
    main()
