import argparse
import sys
import time
from pathlib import Path

from . import core

KIND_TEXT = {
    "cache": "safe to clear, rebuilt automatically",
    "history": "safe to clear, but you lose the old conversations",
    "model": "safe to clear, but it has to be downloaded again",
    "manual": "yours to clear with that program's own command",
    "keep": "yours, never touched",
}
ORDER = ["cache", "history", "model", "manual", "keep"]


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1000 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1000


def report(items):
    if not items:
        print("No agent folders found.")
        return
    tools = {}
    for it in items:
        tools.setdefault(it["tool"], []).append(it)
    total_free = 0
    for tool, its in sorted(tools.items(), key=lambda kv: -sum(i["bytes"] for i in kv[1])):
        print(f"{tool}   {human(sum(i['bytes'] for i in its))}")
        groups = {}
        for it in its:
            groups.setdefault((it["kind"], it["label"]), []).append(it)
        for (kind, label), g in sorted(groups.items(), key=lambda kv: (ORDER.index(kv[0][0]), -sum(i["bytes"] for i in kv[1]))):
            size = sum(i["bytes"] for i in g)
            oldest = min(i["mtime"] for i in g)
            age = f", oldest {time.strftime('%Y-%m-%d', time.localtime(oldest))}" if kind in ("history", "model") else ""
            print(f"  {label:<34}{human(size):>10}   {len(g)} item(s){age}")
            print(f"      {KIND_TEXT[kind]}")
            if kind in ("cache", "history", "model"):
                total_free += size
        print()
    print(f"You could clear up to {human(total_free)}. Nothing is deleted: it all goes to a trash folder you can restore from.")
    print("Try:  agentsweep clean --kind cache        (see what would move; add --yes to do it)")


def main(argv=None):
    p = argparse.ArgumentParser(prog="agentsweep", description="See what your AI agent tools have piled up, and clear it safely.")
    p.add_argument("--home", default=str(Path.home()), help=argparse.SUPPRESS)
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("report", help="show what is taking space (default)")
    c = sub.add_parser("clean", help="move things to the trash folder")
    c.add_argument("--kind", default="cache", help="cache, history, model (comma separated). Default: cache")
    c.add_argument("--tool", help="only this tool, e.g. claude")
    c.add_argument("--older-than", type=int, default=None, metavar="DAYS", help="only things not touched for this many days")
    c.add_argument("--yes", action="store_true", help="actually move them; without this it only shows what would move")
    sub.add_parser("trash", help="list what is in the trash folder")
    r = sub.add_parser("restore", help="put a clean-up back where it came from")
    r.add_argument("stamp")
    e = sub.add_parser("empty-trash", help="permanently delete old trash")
    e.add_argument("--older-than", type=int, default=7, metavar="DAYS")
    e.add_argument("--yes", action="store_true")
    args = p.parse_args(argv)
    home = args.home

    if args.cmd in (None, "report"):
        report(core.scan(home))
        return 0

    if args.cmd == "clean":
        kinds = {k.strip() for k in args.kind.split(",")}
        bad = kinds - {"cache", "history", "model"}
        if bad:
            print(f"Can't clean: {', '.join(sorted(bad))}. Choose from cache, history, model.", file=sys.stderr)
            return 2
        days = args.older_than if args.older_than is not None else (0 if kinds == {"cache"} else 30)
        picked = core.select(core.scan(home), kinds, args.tool, days)
        if not picked:
            print("Nothing to clear with those settings.")
            return 0
        size = sum(i["bytes"] for i in picked)
        if not args.yes:
            for it in sorted(picked, key=lambda i: -i["bytes"])[:15]:
                print(f"  {human(it['bytes']):>9}  {it['tool']}: {it['rel']}")
            if len(picked) > 15:
                print(f"  ... and {len(picked) - 15} more")
            print(f"\nWould move {len(picked)} item(s), {human(size)}. Add --yes to do it.")
            return 0
        stamp, moved = core.move_to_trash(picked, home)
        print(f"Moved {len(moved)} item(s), {human(size)}, to ~/{core.TRASH}/{stamp}")
        print(f"Changed your mind?  agentsweep restore {stamp}")
        return 0

    if args.cmd == "trash":
        rows = core.list_trash(home)
        for r_ in rows:
            print(f"{r_['stamp']}   {r_['count']} item(s)   {human(r_['bytes'])}")
        if not rows:
            print("The trash is empty.")
        return 0

    if args.cmd == "restore":
        try:
            n, skipped = core.restore(home, args.stamp)
        except FileNotFoundError:
            print(f"No clean-up called {args.stamp}. See: agentsweep trash", file=sys.stderr)
            return 2
        print(f"Put back {n} item(s).")
        for s in skipped:
            print(f"  left alone (something new is already there): {s}")
        return 0

    if args.cmd == "empty-trash":
        if not args.yes:
            print(f"This permanently deletes trash older than {args.older_than} days. Add --yes to do it.")
            return 0
        print(f"Freed {human(core.empty_trash(home, args.older_than))}.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
