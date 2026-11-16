import contextlib
import io
import os
import tempfile
import time
import unittest
from pathlib import Path

from agentsweep import cli, core

OLD = time.time() - 90 * 86400


def put(home, rel, size=100, mtime=OLD):
    p = Path(home) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x" * size)
    os.utime(p, (mtime, mtime))
    return p


class Output(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.home = self._t.name
        self.addCleanup(self._t.cleanup)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(["--home", self.home, *argv])
        return code, out.getvalue(), err.getvalue()


class Sizes(unittest.TestCase):
    def test_sizes_read_naturally_in_decimal_units(self):
        self.assertEqual(cli.human(0), "0 B")
        self.assertEqual(cli.human(999), "999 B")
        self.assertEqual(cli.human(1000), "1.0 KB")
        self.assertEqual(cli.human(1_500_000), "1.5 MB")
        self.assertEqual(cli.human(2_000_000_000), "2.0 GB")
        self.assertEqual(cli.human(5_000_000_000_000), "5000.0 GB", "nothing bigger than GB is invented")


class Report(Output):
    def test_an_empty_home_says_so_and_still_exits_cleanly(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "No agent folders found.")

    def test_the_report_groups_by_tool_biggest_first_and_explains_each_kind(self):
        put(self.home, ".claude/debug/d.txt", 100)
        put(self.home, ".claude/projects/-p/a.jsonl", 2000)
        put(self.home, ".cache/huggingface/hub/models--a--b/snap/w.bin", 5000)
        put(self.home, ".ollama/models/blobs/big", 9000)
        code, out, _ = self.run_cli("report")
        self.assertEqual(code, 0)
        tools = [l.split("   ")[0] for l in out.splitlines() if "   " in l and not l.startswith(" ") and not l.startswith("You") and not l.startswith("Try")]
        self.assertEqual(tools, ["Ollama", "Hugging Face", "Claude Code"], "largest tool first")
        self.assertIn("safe to clear, rebuilt automatically", out)
        self.assertIn("safe to clear, but you lose the old conversations", out)
        self.assertIn("safe to clear, but it has to be downloaded again", out)
        self.assertIn("yours to clear with that program's own command", out)

    def test_only_old_conversations_and_models_show_how_old_they_are(self):
        put(self.home, ".claude/projects/-p/a.jsonl")
        put(self.home, ".claude/debug/d.txt")
        _, out, _ = self.run_cli()
        stamp = time.strftime("%Y-%m-%d", time.localtime(OLD))
        history = next(l for l in out.splitlines() if "Old conversations" in l)
        cache = next(l for l in out.splitlines() if "Caches and logs" in l)
        self.assertIn(f"oldest {stamp}", history)
        self.assertNotIn("oldest", cache)

    def test_the_total_counts_only_what_could_be_cleared_never_manual_or_kept_items(self):
        put(self.home, ".claude/debug/d.txt", 1000)       # cache: counts
        put(self.home, ".ollama/models/blobs/big", 50_000)  # manual: does not count
        put(self.home, ".claude/settings.json", 70_000)    # keep: does not count
        _, out, _ = self.run_cli()
        self.assertIn("You could clear up to 1.0 KB.", out)
        self.assertIn("Nothing is deleted: it all goes to a trash folder you can restore from.", out)
        self.assertIn("agentsweep clean --kind cache", out)


class Clean(Output):
    def test_nothing_to_clear_is_said_plainly(self):
        put(self.home, ".claude/projects/-p/a.jsonl")  # history only; the default is cache
        code, out, _ = self.run_cli("clean")
        self.assertEqual((code, out.strip()), (0, "Nothing to clear with those settings."))

    def test_the_preview_lists_the_biggest_fifteen_and_counts_the_rest(self):
        for i in range(18):
            put(self.home, f".claude/debug/log{i:02d}.txt", 100 + i)
        code, out, _ = self.run_cli("clean")
        self.assertEqual(code, 0)
        self.assertEqual(sum("Claude Code: " in l for l in out.splitlines()), 15)
        self.assertIn("... and 3 more", out)
        self.assertIn("Would move 18 item(s)", out)
        self.assertIn("Add --yes to do it.", out)
        self.assertTrue(all(Path(self.home, f".claude/debug/log{i:02d}.txt").exists() for i in range(18)), "a preview moves nothing")

    def test_history_defaults_to_things_untouched_for_thirty_days_but_cache_to_any_age(self):
        put(self.home, ".claude/projects/-p/new.jsonl", mtime=time.time() - 5 * 86400)
        put(self.home, ".claude/projects/-p/old.jsonl", mtime=time.time() - 60 * 86400)
        _, out, _ = self.run_cli("clean", "--kind", "history")
        self.assertIn("old.jsonl", out)
        self.assertNotIn("new.jsonl", out)
        _, out, _ = self.run_cli("clean", "--kind", "history", "--older-than", "1")
        self.assertIn("new.jsonl", out)

    def test_cleaning_for_real_says_where_things_went_and_how_to_undo_it(self):
        put(self.home, ".claude/debug/d.txt", 1000)
        code, out, _ = self.run_cli("clean", "--yes")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"Moved 1 item\(s\), 1\.0 KB, to ~/\.agentsweep-trash/\d{8}-\d{6}")
        self.assertRegex(out, r"Changed your mind\?  agentsweep restore \d{8}-\d{6}")
        self.assertFalse(Path(self.home, ".claude/debug/d.txt").exists())


class Trash(Output):
    def test_an_empty_trash_says_so(self):
        self.assertEqual(self.run_cli("trash")[1].strip(), "The trash is empty.")

    def test_trash_lists_each_clean_up_with_its_count_and_size(self):
        put(self.home, ".claude/debug/d.txt", 1500)
        self.run_cli("clean", "--yes")
        _, out, _ = self.run_cli("trash")
        self.assertRegex(out, r"\d{8}-\d{6}   1 item\(s\)   1\.5 KB")

    def test_restoring_an_unknown_name_is_refused_with_a_pointer_to_the_list(self):
        code, out, err = self.run_cli("restore", "19990101-000000")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("No clean-up called 19990101-000000. See: agentsweep trash", err)

    def test_restore_reports_what_it_put_back_and_what_it_left_alone(self):
        put(self.home, ".claude/debug/d.txt", 100)
        self.run_cli("clean", "--yes")
        stamp = core.list_trash(self.home)[0]["stamp"]
        put(self.home, ".claude/debug/d.txt", 5, mtime=time.time())  # something new is already there
        code, out, _ = self.run_cli("restore", stamp)
        self.assertEqual(code, 0)
        self.assertIn("Put back 0 item(s).", out)
        self.assertIn("left alone (something new is already there): .claude/debug/d.txt", out)
        self.assertEqual(Path(self.home, ".claude/debug/d.txt").read_text(), "x" * 5, "the new file was not overwritten")

    def test_emptying_the_trash_needs_yes_and_then_says_how_much_was_freed(self):
        put(self.home, ".claude/debug/d.txt", 2000)
        self.run_cli("clean", "--yes")
        stamp = core.list_trash(self.home)[0]["stamp"]
        manifest = Path(self.home, core.TRASH, stamp, "manifest.json")
        long_ago = time.time() - 30 * 86400
        os.utime(manifest, (long_ago, long_ago))
        code, out, _ = self.run_cli("empty-trash")
        self.assertEqual(code, 0)
        self.assertIn("permanently deletes trash older than 7 days. Add --yes to do it.", out)
        self.assertEqual(len(core.list_trash(self.home)), 1, "nothing was deleted without --yes")
        code, out, _ = self.run_cli("empty-trash", "--older-than", "14", "--yes")
        self.assertEqual(out.strip(), "Freed 2.0 KB.")
        self.assertEqual(core.list_trash(self.home), [])


if __name__ == "__main__":
    unittest.main()
