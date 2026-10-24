"""Console commands without UI imports or global stream capture."""

import inspect
import shlex

from save_manager import list_save_slots, normalize_save_id, normalize_save_name


class ConsoleCommandsMixin:
    """Use the mod API command registry; frontends may override console_print.

    Callbacks accept (args, raw), or legacy (args) when signature binding
    proves that two arguments are unsupported. Uninspectable callbacks use
    the documented (args, raw) contract. Callbacks are invoked at most once.
    """
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
            callback_args = (args, raw)
            try:
                signature = inspect.signature(callback)
            except (TypeError, ValueError):
                signature = None
            if signature is not None:
                try:
                    signature.bind(*callback_args)
                except TypeError:
                    signature.bind(args)
                    callback_args = (args,)
            result = self._run_with_mod_owner(owner, callback, *callback_args)
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
