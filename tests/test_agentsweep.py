import os
import tempfile
import time
import unittest
from pathlib import Path

from agentsweep import core
from agentsweep.cli import main

OLD = time.time() - 90 * 86400
SESSION = "1d75956a-4dd6-493f-b949-967ca1db7209"


def put(home, rel, text="x" * 100, mtime=OLD):
    p = Path(home) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    os.utime(p, (mtime, mtime))
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.home = self._t.name
        put(self.home, ".claude/projects/-p/a.jsonl")
        put(self.home, f".claude/projects/-p/{SESSION}/sub/log.txt")
        put(self.home, ".claude/projects/-p/memory/MEMORY.md")
        put(self.home, ".claude/settings.json")
        put(self.home, ".claude/debug/d.txt")
        put(self.home, ".ollama/id_ed25519", "secret")
        put(self.home, ".ollama/models/blobs/big", "y" * 500)
        put(self.home, ".cache/huggingface/hub/models--a--b/snap/w.bin", "z" * 300)
        put(self.home, ".claude/projects/-p/recent.jsonl", mtime=time.time())

    def tearDown(self):
        self._t.cleanup()

    def run_cli(self, *a):
        return main(["--home", self.home, *a])


class Safety(Base):
    def test_memory_settings_and_keys_are_never_cleanable(self):
        items = {i["rel"]: i["kind"] for i in core.scan(self.home)}
        self.assertEqual(items[".claude/projects/-p/memory"], "keep")
        self.assertEqual(items[".claude/settings.json"], "keep")
        self.assertEqual(items[".ollama/id_ed25519"], "keep")

    def test_clean_everything_leaves_protected_files_in_place(self):
        self.run_cli("clean", "--kind", "cache,history,model", "--older-than", "1", "--yes")
        for rel in (".claude/projects/-p/memory/MEMORY.md", ".claude/settings.json", ".ollama/id_ed25519"):
            self.assertTrue((Path(self.home) / rel).exists(), rel)

    def test_history_folder_holding_something_protected_is_kept_whole(self):
        put(self.home, f".claude/projects/-p/{SESSION}/skills/x.md")
        kinds = {i["rel"]: i["kind"] for i in core.scan(self.home)}
        self.assertEqual(kinds[f".claude/projects/-p/{SESSION}"], "keep")

    def test_recent_files_are_skipped(self):
        self.run_cli("clean", "--kind", "history", "--older-than", "0", "--yes")
        self.assertTrue((Path(self.home) / ".claude/projects/-p/recent.jsonl").exists())
        self.assertFalse((Path(self.home) / ".claude/projects/-p/a.jsonl").exists())

    def test_manual_items_are_never_moved(self):
        self.run_cli("clean", "--kind", "cache,history,model", "--older-than", "1", "--yes")
        self.assertTrue((Path(self.home) / ".ollama/models/blobs/big").exists())

    def test_symlinks_are_not_followed(self):
        target = Path(self._t.name + "_outside")
        target.mkdir()
        (target / "precious.txt").write_text("keep me")
        os.symlink(target, Path(self.home) / ".claude/debug/link")
        self.run_cli("clean", "--kind", "cache", "--yes")
        self.assertTrue((target / "precious.txt").exists())

    def test_unknown_kind_is_refused(self):
        self.assertEqual(self.run_cli("clean", "--kind", "keep"), 2)


class Behaviour(Base):
    def test_dry_run_moves_nothing(self):
        self.run_cli("clean", "--kind", "cache")
        self.assertTrue((Path(self.home) / ".claude/debug/d.txt").exists())

    def test_default_is_cache_only(self):
        self.run_cli("clean", "--yes")
        self.assertFalse((Path(self.home) / ".claude/debug/d.txt").exists())
        self.assertTrue((Path(self.home) / ".claude/projects/-p/a.jsonl").exists())

    def test_clean_then_restore_puts_everything_back(self):
        self.run_cli("clean", "--kind", "history", "--older-than", "30", "--yes")
        a = Path(self.home) / ".claude/projects/-p/a.jsonl"
        self.assertFalse(a.exists())
        stamp = core.list_trash(self.home)[0]["stamp"]
        self.assertEqual(self.run_cli("restore", stamp), 0)
        self.assertTrue(a.exists())
        self.assertTrue((Path(self.home) / f".claude/projects/-p/{SESSION}/sub/log.txt").exists())

    def test_restore_does_not_overwrite_new_files(self):
        self.run_cli("clean", "--kind", "cache", "--yes")
        stamp = core.list_trash(self.home)[0]["stamp"]
        put(self.home, ".claude/debug/d.txt", "new")
        self.run_cli("restore", stamp)
        self.assertEqual((Path(self.home) / ".claude/debug/d.txt").read_text(), "new")

    def test_tool_filter(self):
        self.run_cli("clean", "--kind", "model", "--tool", "ollama", "--older-than", "1", "--yes")
        self.assertTrue((Path(self.home) / ".cache/huggingface/hub/models--a--b").exists())
        self.run_cli("clean", "--kind", "model", "--tool", "hugging", "--older-than", "1", "--yes")
        self.assertFalse((Path(self.home) / ".cache/huggingface/hub/models--a--b").exists())

    def test_empty_trash_respects_age(self):
        self.run_cli("clean", "--kind", "cache", "--yes")
        self.assertEqual(core.empty_trash(self.home, 7), 0)
        self.assertEqual(len(core.list_trash(self.home)), 1)
        self.assertGreater(core.empty_trash(self.home, 0), 0)
        self.assertEqual(core.list_trash(self.home), [])

    def test_report_runs(self):
        self.assertEqual(self.run_cli(), 0)


if __name__ == "__main__":
    unittest.main()
