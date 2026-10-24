import unittest

from mod_api import version_meets_requirement


class ModVersionTests(unittest.TestCase):
    def test_semver_precedence(self):
        ordered = ["1.4.0-alpha", "1.4.0-alpha.1", "1.4.0-alpha.beta",
                   "1.4.0-beta", "1.4.0-beta.2", "1.4.0-beta.11",
                   "1.4.0-rc.1", "1.4.0-rc.2", "1.4.0-rc.10", "1.4.0"]
        for i, current in enumerate(ordered):
            for j, required in enumerate(ordered):
                with self.subTest(current=current, required=required):
                    self.assertEqual(version_meets_requirement(current, required), i >= j)

    def test_rc_shorthand_is_older_than_final(self):
        self.assertFalse(version_meets_requirement("1.4.0-rc1", "1.4.0"))
        self.assertTrue(version_meets_requirement("1.4.0", "1.4.0-rc1"))
        self.assertTrue(version_meets_requirement("1.4.0-rc2", "1.4.0-rc1"))
        self.assertTrue(version_meets_requirement("1.5.0-alpha", "1.4.0"))

    def test_build_metadata_is_ignored(self):
        for current, required in [("1.4.0+build.1", "1.4.0+build.2"),
                                  ("1.4.0", "1.4.0+build.2"),
                                  ("1.4.0-rc1+build.2", "1.4.0-rc1")]:
            with self.subTest(current=current, required=required):
                self.assertTrue(version_meets_requirement(current, required))

    def test_existing_numeric_version_forms(self):
        for current, required in [("1", "1.0.0"), ("1.4", "1.4.0"),
                                  ("v1.4.0", "1.4"), ("1.4.0.1", "1.4.0"),
                                  ("1.10", "1.9"), (" 1.4.0 ", "1.4.0")]:
            with self.subTest(current=current, required=required):
                self.assertTrue(version_meets_requirement(current, required))

    def test_unknown_versions_do_not_satisfy_numeric_minimum(self):
        for current, required in [("", "1.0"), ("unknown", "1.0"),
                                  ("1.4.0", ">=1.0"), ("1.4..0", "1.0")]:
            with self.subTest(current=current, required=required):
                self.assertFalse(version_meets_requirement(current, required))
        self.assertTrue(version_meets_requirement("custom", "custom"))
        self.assertTrue(version_meets_requirement("", ""))


if __name__ == "__main__":
    unittest.main()
