import unittest

from agentsweep import core
from agentsweep.catalog import CATALOG, PROTECTED_NAMES

KINDS = {"cache", "history", "model", "manual", "keep"}
CLEARABLE = {"cache", "history", "model"}


class CatalogRules(unittest.TestCase):
    def test_every_group_has_a_known_kind(self):
        for g in CATALOG:
            self.assertIn(g.kind, KINDS, f"{g.tool}: {g.label}")

    def test_every_group_has_something_to_match(self):
        for g in CATALOG:
            self.assertTrue(g.globs, f"{g.tool}: {g.label}")

    def test_patterns_stay_inside_the_home_folder(self):
        for g in CATALOG:
            for pattern in g.globs:
                self.assertFalse(pattern.startswith(("/", "~")), pattern)
                self.assertNotIn("..", pattern.split("/"), pattern)

    def test_groups_that_can_be_cleared_explain_what_you_lose_or_regain(self):
        for g in CATALOG:
            if g.kind in CLEARABLE or g.kind == "manual":
                self.assertTrue(g.note, f"{g.tool}: {g.label} has no note")

    def test_no_clearable_pattern_ends_on_a_protected_name(self):
        # A rule that points straight at memory, skills, keys or settings would be
        # refused at run time anyway. Catching it here shows the mistake sooner.
        for g in CATALOG:
            if g.kind not in CLEARABLE:
                continue
            for pattern in g.globs:
                last = pattern.rstrip("/").split("/")[-1]
                self.assertFalse(core.name_protected(last), f"{g.tool}: {pattern}")

    def test_the_protected_names_include_the_things_people_cannot_get_back(self):
        for name in ("memory", "skills", ".ssh", ".aws", "auth.json", ".credentials.json", ".env"):
            self.assertIn(name, PROTECTED_NAMES)

    def test_keys_and_settings_are_protected_by_pattern_not_only_by_name(self):
        for name in ("settings.json", "settings.local.json", "id_ed25519", "server.pem", "signing.key", "me.pub"):
            self.assertTrue(core.name_protected(name), name)

    def test_ordinary_cache_files_are_not_protected(self):
        for name in ("shell-snapshots", "debug.log", "abc123.jsonl"):
            self.assertFalse(core.name_protected(name), name)


if __name__ == "__main__":
    unittest.main()
