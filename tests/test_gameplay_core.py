import sys
import unittest
from unittest.mock import Mock

from console_commands import ConsoleCommandsMixin
from gameplay_core import GameplayCoreMixin


class StubGame(GameplayCoreMixin):
    def __init__(self):
        self.state = {"total_clicks": 0}
        self.primary_currency = "flesh"
        self.currencies = {"flesh": {}, "wood": {}, "idle": {}}
        self.amounts = {"flesh": 100.0, "wood": 0.0, "idle": 0.0}
        self.upgrades = {"tool": {"cost_currency": "flesh"}}
        self.counts = {}
        self.achievements = {
            key: {} for key in (
                "first_click", "ten_clicks", "hundred_clicks", "hundred_flesh",
                "thousand_flesh", "first_upgrade", "five_upgrades",
            )
        }
        self.effects = []
        self.events = []
        self.update_labels = Mock()
        self.play_squish = Mock()
        self.play_click_sound = Mock()
        self._apply_upgrade_visibility = Mock()
        self.refresh_achievements_ui = Mock()
        self.mark_save_dirty = Mock()
        self._achievement_is_active = Mock(return_value=True)
        self._apply_click_modifiers = Mock(side_effect=lambda gains, context: (gains, []))

    @property
    def flesh(self):
        return self.amounts["flesh"]

    def get_currency(self, name):
        return self.amounts.get(name, 0)

    def add_currency(self, name, amount):
        self.amounts[name] = self.get_currency(name) + amount

    def get_upgrade_count(self, uid):
        return self.counts.get(uid, 0)

    def set_upgrade_count(self, uid, count):
        self.counts[uid] = count

    def get_upgrade_cost(self, uid, owned):
        return 10 * (owned + 1)

    def _get_effects(self, uid):
        return self.effects

    def total_upgrades_owned(self):
        return sum(self.counts.values())

    def _emit_event(self, name, payload):
        self.events.append((name, payload))

    def effective_fpc(self):
        return 2

    def compute_cpc(self, name):
        return 3 if name == "wood" else 0

    def compute_cps(self, name):
        return {"flesh": 2, "wood": 0, "idle": -1}[name]

    def _coerce_modifier_number(self, value, default):
        return float(value) if value is not None else default


class GameplayCoreTests(unittest.TestCase):
    def setUp(self):
        self.game = StubGame()

    def test_purchase_cost_grants_event_and_refresh(self):
        game = self.game
        game.upgrades["tool"]["cost_currency"] = "wood"
        game.amounts["wood"] = 10
        game.effects = [{"currency": "flesh", "on_buy": 4}, {"currency": "wood"}]
        self.assertIs(game.on_buy_upgrade_clicked(None, "tool"), True)
        self.assertEqual(game.amounts, {"flesh": 104, "wood": 0, "idle": 0})
        self.assertEqual(game.counts, {"tool": 1})
        self.assertEqual(game.events, [("upgrade_bought", {
            "upgrade_id": "tool", "upgrade": {"cost_currency": "wood"},
            "owned_before": 0, "owned_after": 1, "cost": 10,
            "cost_currency": "wood",
        })])
        self.assertTrue(game.achievements["first_upgrade"]["unlocked"])
        game._apply_upgrade_visibility.assert_called_once_with()
        game.update_labels.assert_called_once_with()

    def test_rejected_purchases_have_no_side_effects(self):
        for reason in ("missing", "requires", "funds"):
            with self.subTest(reason=reason):
                game = StubGame()
                uid = "missing" if reason == "missing" else "tool"
                if reason == "requires":
                    game.upgrades["tool"]["requires"] = {"upgrade": "locked"}
                elif reason == "funds":
                    game.amounts["flesh"] = 9
                before = dict(game.amounts)
                self.assertIs(game.on_buy_upgrade_clicked(None, uid), False)
                self.assertEqual(game.amounts, before)
                self.assertEqual(game.counts, {})
                self.assertEqual(game.events, [])
                game.update_labels.assert_not_called()
                game._apply_upgrade_visibility.assert_not_called()
                game.mark_save_dirty.assert_not_called()

    def test_requires_and_within_or_between_conditions(self):
        game = self.game
        self.assertFalse(game.check_requires("missing"))
        self.assertTrue(game.check_requires("tool"))
        condition = {"upgrade": "seed", "count": 2, "currency": "wood", "amount": 5}
        game.upgrades["tool"]["requires"] = condition
        game.counts["seed"] = 2
        self.assertFalse(game.check_requires("tool"))
        game.amounts["wood"] = 5
        self.assertTrue(game.check_requires("tool"))
        game.upgrades["tool"]["requires"] = [{"upgrade": "absent"}, condition]
        self.assertTrue(game.check_requires("tool"))
        game.upgrades["tool"]["requires"] = []
        self.assertFalse(game.check_requires("tool"))

    def test_click_gains_context_events_and_milestones(self):
        game = self.game
        game.state["total_clicks"] = 99
        game.amounts["flesh"] = 999
        modifiers = [
            {"key": "__global__:critical_clicks", "multiplier": 2},
            {"key": "other", "multiplier": 99},
            {"key": "__global__:critical_clicks", "multiplier": 3},
        ]
        game._apply_click_modifiers.side_effect = None
        game._apply_click_modifiers.return_value = ({"flesh": 12, "wood": 18, "idle": 0}, modifiers)
        game.on_click(None, 2, 4, 5)
        game.play_squish.assert_called_once_with()
        game.play_click_sound.assert_called_once_with()
        game._apply_click_modifiers.assert_called_once_with(
            {"flesh": 2, "wood": 3},
            {"x": 4, "y": 5, "n_press": 2, "total_clicks": 100,
             "vanilla_multiplier": 1.0, "crit_multiplier": 1.0},
        )
        self.assertEqual(game.amounts, {"flesh": 1011, "wood": 18, "idle": 0})
        self.assertEqual(game.events, [("flesh_clicked", {
            "x": 4, "y": 5, "n_press": 2, "total_clicks": 100,
            "multiplier": 6, "vanilla_multiplier": 6, "crit_multiplier": 6,
            "base_gains": {"flesh": 2, "wood": 3},
            "gains": {"flesh": 12, "wood": 18, "idle": 0}, "modifiers": modifiers,
        })])
        game.mark_save_dirty.assert_any_call(auto_backup=True)
        for key in ("first_click", "ten_clicks", "hundred_clicks", "hundred_flesh", "thousand_flesh"):
            self.assertTrue(game.achievements[key]["unlocked"])
        game.update_labels.assert_called_once_with()

    def test_fifth_purchase_unlocks_milestone(self):
        self.game.counts["tool"] = 4
        self.assertTrue(self.game.on_buy_upgrade_clicked(None, "tool"))
        self.assertEqual(self.game.amounts["flesh"], 50)
        self.assertTrue(self.game.achievements["five_upgrades"]["unlocked"])

    def test_timer_adds_only_positive_cps(self):
        self.assertIs(self.game.on_timer_tick(), True)
        self.assertEqual(self.game.amounts, {"flesh": 102, "wood": 0, "idle": 0})
        self.game.update_labels.assert_called_once_with()

    def test_achievement_is_active_and_idempotent(self):
        game = self.game
        game.unlock_achievement("unknown")
        game._achievement_is_active.return_value = False
        game.unlock_achievement("first_click")
        game.mark_save_dirty.assert_not_called()
        game._achievement_is_active.return_value = True
        game.unlock_achievement("first_click")
        game.unlock_achievement("first_click")
        game.mark_save_dirty.assert_called_once_with(auto_backup=False)
        game.refresh_achievements_ui.assert_called_once_with()


class ConsoleCommandTests(unittest.TestCase):
    def setUp(self):
        self.console = ConsoleCommandsMixin()
        self.console.console_commands = {}
        self.console.console_aliases = {"alias": "test"}
        self.console.console_print = Mock()
        self.console._run_with_mod_owner = Mock(side_effect=lambda owner, callback, *args: callback(*args))

    def register(self, callback):
        self.console.console_commands["test"] = {"callback": callback, "owner": "mod"}

    def test_two_argument_callback_receives_parsed_args_and_raw(self):
        callback = Mock(return_value="done")
        self.register(callback)
        self.console.execute_console_command('alias "two words"')
        callback.assert_called_once_with(["two words"], '/alias "two words"')
        self.console.console_print.assert_any_call("done")

    def test_legacy_single_argument_callback(self):
        calls = []

        def callback(args):
            calls.append(args)

        self.register(callback)
        self.console.execute_console_command("/test value")
        self.assertEqual(calls, [["value"]])

    def test_internal_typeerror_does_not_retry_callback(self):
        calls = []

        def callback(args, raw=None):
            calls.append(args)
            raise TypeError("callback bug")

        self.register(callback)
        self.console.execute_console_command("/test value")
        self.assertEqual(calls, [["value"]])
        self.console.console_print.assert_any_call("Command failed: callback bug")
        self.console._run_with_mod_owner.assert_called_once()

    def test_imports_do_not_capture_streams_or_load_gtk(self):
        import subprocess

        result = subprocess.run([
            sys.executable, "-c",
            "import sys; before = (sys.stdout, sys.stderr); "
            "import gameplay_core, console_commands; "
            "assert before == (sys.stdout, sys.stderr); "
            "assert 'gtk_compat' not in sys.modules; "
            "assert 'gi' not in sys.modules; "
            "assert 'console_capture' not in sys.modules",
        ], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
