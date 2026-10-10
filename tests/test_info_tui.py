import json
import os
import tempfile
import unittest

import info_tui


class InfoTuiDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = self.temp_dir.name
        self.saves = os.path.join(self.root, "saves")
        self.system_mods = os.path.join(self.root, "system-mods")
        self.user_mods = os.path.join(self.root, "user-mods")
        os.makedirs(self.saves)
        os.makedirs(self.system_mods)
        os.makedirs(self.user_mods)
        self.settings = os.path.join(self.root, "settings.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_json(self, path, value):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(value, handle)

    def make_mod(self, root, mod_id, manifest, enabled=None, mod_code="raise RuntimeError('executed')"):
        mod_dir = os.path.join(root, mod_id)
        os.makedirs(mod_dir)
        self.write_json(os.path.join(mod_dir, "manifest.json"), manifest)
        with open(os.path.join(mod_dir, "mod.py"), "w", encoding="utf-8") as handle:
            handle.write(mod_code)
        if enabled is not None:
            with open(os.path.join(mod_dir, "enabled.txt"), "w", encoding="utf-8") as handle:
                handle.write("true\n" if enabled else "false\n")
        return mod_dir

    def test_loads_saves_marks_active_and_skips_broken_json(self):
        self.write_json(self.settings, {"active_save_id": "second"})
        self.write_json(
            os.path.join(self.saves, "second.json"),
            {
                "id": "second",
                "name": "Second Save",
                "updated_at": "2026-09-25 12:00:00",
                "state": {"currencies": {"flesh": 42}, "upgrades_owned": {}},
            },
        )
        with open(os.path.join(self.saves, "broken.json"), "w", encoding="utf-8") as handle:
            handle.write("not json")

        settings, saves = info_tui.load_saves(self.saves, self.settings)

        self.assertEqual(settings["active_save_id"], "second")
        self.assertEqual([save["id"] for save in saves], ["second"])
        self.assertTrue(saves[0]["_active"])
        self.assertEqual(saves[0]["save_kind"], "singleplayer")

    def test_discovers_mods_without_executing_them(self):
        marker = os.path.join(self.root, "mod-was-executed")
        self.make_mod(
            self.user_mods,
            "example",
            {"name": "Example", "version": "1.2.0", "author": "Tester"},
            enabled=None,
            mod_code=f"open({marker!r}, 'w').close()",
        )

        mods = info_tui.discover_mods(self.system_mods, self.user_mods)

        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0]["name"], "Example")
        self.assertTrue(mods[0]["enabled"])
        self.assertFalse(mods[0]["has_enabled_file"])
        self.assertFalse(os.path.exists(marker))

    def test_reports_disabled_mod_and_missing_dependency(self):
        self.make_mod(self.user_mods, "disabled-api", {"version": "2.0"}, enabled=False)
        self.make_mod(
            self.user_mods,
            "consumer",
            {"dependencies": [{"id": "disabled-api", "version": "1.0"}]},
            enabled=True,
        )

        mods = info_tui.discover_mods(self.system_mods, self.user_mods)
        by_id = {mod["id"]: mod for mod in mods}

        self.assertFalse(by_id["disabled-api"]["enabled"])
        self.assertEqual(by_id["consumer"]["missing_dependencies"], ["disabled-api >= 1.0"])

    def test_marks_a_broken_manifest_without_loading_mod_code(self):
        mod_dir = os.path.join(self.user_mods, "broken")
        os.makedirs(mod_dir)
        with open(os.path.join(mod_dir, "mod.py"), "w", encoding="utf-8") as handle:
            handle.write("raise RuntimeError('executed')")
        with open(os.path.join(mod_dir, "manifest.json"), "w", encoding="utf-8") as handle:
            handle.write("{broken")

        mods = info_tui.discover_mods(self.system_mods, self.user_mods)

        self.assertEqual(len(mods), 1)
        self.assertTrue(mods[0]["manifest_error"])

    def test_save_details_include_stats_upgrades_and_mod_requirements(self):
        save = {
            "id": "main",
            "name": "Main Save",
            "save_kind": "singleplayer",
            "created_at": "today",
            "updated_at": "today",
            "required_mods": [{"id": "missing", "name": "Missing Mod", "version": "1.0"}],
            "mod_data": {"example": {"value": 4}},
            "state": {
                "currencies": {"flesh": 60},
                "flesh_per_click": 1,
                "upgrades_owned": {"bigger_clicks": 2},
                "total_clicks": 12,
            },
            "achievements": {"first_click": {"name": "First Click", "unlocked": True}},
            "_path": "main.json",
            "_active": True,
        }

        output = "\n".join(info_tui.save_detail_lines(save, []))

        self.assertIn("Total clicks: 12", output)
        self.assertIn("per click: 3", output)
        self.assertIn("Bigger Clicks: 2", output)
        self.assertIn("Missing Mod 1.0 [MISSING]", output)
        self.assertIn("example: 1 key(s): value", output)

    def test_invalid_numeric_save_fields_do_not_break_details(self):
        save = {
            "id": "broken",
            "name": "Broken Save",
            "state": {
                "currencies": {"flesh": "unknown"},
                "flesh_per_click": "invalid",
                "upgrades_owned": {"bigger_clicks": "also invalid"},
            },
            "_path": "broken.json",
        }

        output = "\n".join(info_tui.save_detail_lines(save, []))

        self.assertIn("Broken Save", output)
        self.assertIn("per click: 1", output)


if __name__ == "__main__":
    unittest.main()
