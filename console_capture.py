import sys
import shlex
from collections import deque

from gtk_compat import GLib, Gtk

from save_manager import list_save_slots, normalize_save_id, normalize_save_name

# ---------- CONSOLE CAPTURE ----------
# Intercept stdout and stderr so we can show them in the in-game Console tab.
# The original streams are preserved so output still goes to the terminal too.

CONSOLE_HISTORY_MAX_CHUNKS = 2000
CONSOLE_FLUSH_INTERVAL_MS = 50
CONSOLE_MAX_BUFFER_CHARS = 1_000_000


class _TeeStream:
    """Writes to both the original stream and a shared log buffer."""
    def __init__(self, original):
        self._original = original
        self._history = deque(maxlen=CONSOLE_HISTORY_MAX_CHUNKS)
        self._callbacks = []  # list of callables notified on each write

    def write(self, text):
        self._history.append(text)
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        for cb in self._callbacks:
            try:
                cb(text)
            except Exception:
                pass

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def fileno(self):
        try:
            return self._original.fileno()
        except Exception:
            return -1

    def isatty(self):
        try:
            return self._original.isatty()
        except Exception:
            return False

    @property
    def encoding(self):
        return getattr(self._original, "encoding", "utf-8")

    @property
    def errors(self):
        return getattr(self._original, "errors", "replace")

_stdout_tee = _TeeStream(sys.stdout)
_stderr_tee = _TeeStream(sys.stderr)
sys.stdout = _stdout_tee
sys.stderr = _stderr_tee


class ConsoleMixin:
    def console_print(self, text=""):
        print(str(text))

    def _register_default_console_commands(self):
        self.register_console_command(
            "addcurrency",
            self._cmd_addcurrency,
            "Add currency: /addcurrency <currency> <amount>",
            aliases=["ac", "add"],
        )
        self.register_console_command(
            "takecurrency",
            self._cmd_takecurrency,
            "Take currency: /takecurrency <currency> <amount>",
            aliases=["tc", "take"],
        )
        self.register_console_command(
            "currencymodifier",
            self._cmd_currencymodifier,
            "Multiply a currency amount: /currencymodifier <currency> <multiplier>",
            aliases=["cm", "multcurrency", "multiplycurrency"],
        )
        self.register_console_command(
            "setcurrency",
            self._cmd_setcurrency,
            "Set currency: /setcurrency <currency> <amount>",
            aliases=["sc"],
        )
        self.register_console_command(
            "currencies",
            self._cmd_currencies,
            "List known currencies.",
            aliases=["currencylist", "cl"],
        )
        self.register_console_command(
            "clickmodifiers",
            self._cmd_clickmodifiers,
            "List active click gain modifiers.",
            aliases=["modifiers", "clickmods"],
        )
        self.register_console_command(
            "apis",
            self._cmd_apis,
            "List shared mod APIs.",
            aliases=["api", "listapis"],
        )
        self.register_console_command(
            "saves",
            self._cmd_saves,
            "List save slots.",
            aliases=["listsaves", "lsaves"],
        )
        self.register_console_command(
            "save",
            self._cmd_save,
            "Save active progress.",
            aliases=["savegame"],
        )
        self.register_console_command(
            "reload",
            self._cmd_reload,
            "Reload installed mods without restarting the game.",
            aliases=["reloadmods", "rl"],
        )
        self.register_console_command(
            "print",
            self._cmd_print,
            "Print text to the console: /print <text>",
            aliases=["p", "echo"],
        )
        self.register_console_command(
            "help",
            self._cmd_help,
            "Show help: /help [command]",
            aliases=["h", "?", "commands"],
        )

    def _resolve_console_command(self, command_name: str):
        command_name = str(command_name or "").strip().lower().lstrip("/")
        command_name = self.console_aliases.get(command_name, command_name)
        return command_name, self.console_commands.get(command_name)

    def execute_console_command(self, text: str):
        raw = str(text or "").strip()
        if not raw:
            return
        if not raw.startswith("/"):
            first = raw.split(None, 1)[0].lower() if raw.split(None, 1) else raw.lower()
            _canonical, info = self._resolve_console_command(first)
            if info:
                raw = "/" + raw
            else:
                raw = "/print " + raw

        self.console_print(f"> {raw}")
        try:
            parts = shlex.split(raw)
        except Exception as exc:
            self.console_print(f"Command parse error: {exc}")
            return
        if not parts:
            return

        _command_name, command_info = self._resolve_console_command(parts[0])
        if not command_info:
            self.console_print(f"Unknown command: {parts[0]}. Try /help.")
            return
        args = parts[1:]
        callback = command_info.get("callback")
        owner = command_info.get("owner")
        try:
            result = self._run_with_mod_owner(owner, callback, args, raw)
        except TypeError:
            try:
                result = self._run_with_mod_owner(owner, callback, args)
            except Exception as exc:
                self.console_print(f"Command failed: {exc}")
                return
        except Exception as exc:
            self.console_print(f"Command failed: {exc}")
            return
        if result is not None:
            self.console_print(result)

    def _parse_console_amount(self, args, usage):
        if len(args) < 2:
            raise ValueError(usage)
        currency = args[0]
        try:
            amount = float(args[1])
        except Exception:
            raise ValueError("Amount must be a number.")
        if currency not in self.currencies and currency not in self.state.get("currencies", {}):
            raise ValueError(f"Unknown currency: {currency}")
        return currency, amount

    def _cmd_addcurrency(self, args, raw):
        currency, amount = self._parse_console_amount(args, "Usage: /addcurrency <currency> <amount>")
        self.add_currency(currency, amount)
        self.update_labels()
        return f"Added {amount:g} {currency}. New amount: {self.get_currency(currency):g}"

    def _cmd_takecurrency(self, args, raw):
        currency, amount = self._parse_console_amount(args, "Usage: /takecurrency <currency> <amount>")
        self.add_currency(currency, -amount)
        self.update_labels()
        return f"Took {amount:g} {currency}. New amount: {self.get_currency(currency):g}"

    def _cmd_currencymodifier(self, args, raw):
        currency, multiplier = self._parse_console_amount(args, "Usage: /currencymodifier <currency> <multiplier>")
        self.set_currency(currency, self.get_currency(currency) * multiplier)
        self.update_labels()
        return f"Multiplied {currency} by {multiplier:g}. New amount: {self.get_currency(currency):g}"

    def _cmd_setcurrency(self, args, raw):
        currency, amount = self._parse_console_amount(args, "Usage: /setcurrency <currency> <amount>")
        self.set_currency(currency, amount)
        self.update_labels()
        return f"Set {currency} to {self.get_currency(currency):g}"

    def _cmd_currencies(self, args, raw):
        lines = ["Currencies:"]
        seen = set()
        for currency, data in self.currencies.items():
            seen.add(currency)
            display = data.get("display_name", currency)
            lines.append(f"  {currency} ({display}): {self.get_currency(currency):g}")
        for currency in sorted(set(self.state.get("currencies", {})) - seen):
            lines.append(f"  {currency}: {self.get_currency(currency):g}")
        return "\n".join(lines)

    def _cmd_clickmodifiers(self, args, raw):
        modifiers = self.get_click_modifiers()
        if not modifiers:
            return "No active click modifiers."
        lines = ["Click modifiers:"]
        for modifier in modifiers:
            description = modifier.get("description") or "No description"
            owner = modifier.get("owner") or "unknown"
            currency = modifier.get("currency") or "all click gains"
            lines.append(f"  {modifier.get('key')}: {description} ({currency}, owner: {owner})")
        return "\n".join(lines)

    def _cmd_apis(self, args, raw):
        apis = self.list_apis()
        if not apis:
            return "No shared mod APIs registered."
        lines = ["Shared mod APIs:"]
        for api_info in apis:
            version = api_info.get("version") or "unversioned"
            owner = api_info.get("owner") or "unknown"
            description = api_info.get("description") or "No description"
            aliases = api_info.get("aliases") or []
            alias_text = f", aliases: {', '.join(aliases)}" if aliases else ""
            lines.append(f"  {api_info.get('name')}: {version}, owner: {owner}{alias_text} - {description}")
        return "\n".join(lines)

    def _cmd_saves(self, args, raw):
        lines = ["Saves:"]
        for slot in list_save_slots():
            save_id = normalize_save_id(slot.get("id"))
            marker = "*" if save_id == self.active_save_id else " "
            lines.append(f" {marker} {save_id}: {normalize_save_name(slot.get('name') or save_id)}")
        return "\n".join(lines)

    def _cmd_save(self, args, raw):
        self.save_current_progress(auto_backup=True)
        return f"Saved '{self.active_save_name}'."

    def _cmd_reload(self, args, raw):
        return self.reload_mods()

    def _cmd_print(self, args, raw):
        return " ".join(args)

    def _cmd_help(self, args, raw):
        if args:
            command_name, command_info = self._resolve_console_command(args[0])
            if not command_info:
                return f"Unknown command: {args[0]}"
            aliases = command_info.get("aliases", [])
            alias_text = f" Aliases: {', '.join('/' + alias for alias in aliases)}." if aliases else ""
            help_text = command_info.get("help") or f"/{command_name}"
            return f"/{command_name}: {help_text}.{alias_text}"

        lines = ["Commands:"]
        for command_name in sorted(self.console_commands):
            info = self.console_commands[command_name]
            aliases = info.get("aliases", [])
            alias_text = f" ({', '.join('/' + alias for alias in aliases)})" if aliases else ""
            help_text = info.get("help") or ""
            lines.append(f"  /{command_name}{alias_text} - {help_text}")
        return "\n".join(lines)

    def build_console_page(self):
        self.console_page.set_margin_top(4)
        self.console_page.set_margin_bottom(4)
        self.console_page.set_margin_start(4)
        self.console_page.set_margin_end(4)

        # toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", self._on_console_clear)
        toolbar.append(clear_btn)

        self._console_command_entry = Gtk.Entry()
        self._console_command_entry.set_placeholder_text("/help")
        self._console_command_entry.set_hexpand(True)
        self._console_command_entry.connect("activate", self._on_console_command_activate)
        toolbar.append(self._console_command_entry)

        run_btn = Gtk.Button(label="Run")
        run_btn.connect("clicked", self._on_console_run_clicked)
        toolbar.append(run_btn)
        self.console_page.append(toolbar)

        # scrolled textview
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        self.console_page.append(scrolled)

        self._console_textview = Gtk.TextView()
        self._console_textview.set_editable(False)
        self._console_textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        try:
            self._console_textview.set_monospace(True)
        except Exception:
            pass
        scrolled.set_child(self._console_textview)
        self._console_buffer = self._console_textview.get_buffer()
        self._console_pending_chunks = []
        self._console_flush_pending = False

        # hook into the tee streams
        _stdout_tee._callbacks.append(self._console_append)
        _stderr_tee._callbacks.append(self._console_append)
        for text in list(_stdout_tee._history) + list(_stderr_tee._history):
            if text:
                self._console_append(text)

    def _console_append(self, text: str):
        """Append text to the console buffer in small batches."""
        if not hasattr(self, "_console_pending_chunks"):
            return
        self._console_pending_chunks.append(str(text))
        if not self._console_flush_pending:
            self._console_flush_pending = True
            GLib.timeout_add(CONSOLE_FLUSH_INTERVAL_MS, self._flush_console_pending)

    def _trim_console_buffer(self):
        try:
            char_count = self._console_buffer.get_char_count()
        except Exception:
            return
        excess = char_count - CONSOLE_MAX_BUFFER_CHARS
        if excess <= 0:
            return
        start = self._console_buffer.get_start_iter()
        cutoff = self._console_buffer.get_iter_at_offset(excess)
        self._console_buffer.delete(start, cutoff)

    def _flush_console_pending(self):
        self._console_flush_pending = False
        if not getattr(self, "_console_pending_chunks", None):
            return False
        text = "".join(self._console_pending_chunks)
        self._console_pending_chunks.clear()
        end = self._console_buffer.get_end_iter()
        self._console_buffer.insert(end, text, -1)
        self._trim_console_buffer()
        new_end = self._console_buffer.get_end_iter()
        self._console_buffer.place_cursor(new_end)
        mark = self._console_buffer.get_insert()
        self._console_textview.scroll_mark_onscreen(mark)
        return False

    def _on_console_clear(self, button):
        if hasattr(self, "_console_pending_chunks"):
            self._console_pending_chunks.clear()
        self._console_flush_pending = False
        self._console_buffer.set_text("", -1)

    def _run_console_entry(self):
        text = self._console_command_entry.get_text() if hasattr(self, "_console_command_entry") else ""
        self.execute_console_command(text)
        self._console_command_entry.set_text("")

    def _on_console_command_activate(self, entry):
        self._run_console_entry()

    def _on_console_run_clicked(self, button):
        self._run_console_entry()
