import fnmatch
import glob
import json
import os
import shutil
import time
from pathlib import Path

from .catalog import CATALOG, PROTECTED_NAMES, PROTECTED_PREFIXES, PROTECTED_SUFFIXES

DAY = 86400
TRASH = ".agentsweep-trash"


def name_protected(name):
    return name in PROTECTED_NAMES or name.startswith(PROTECTED_PREFIXES) or name.endswith(PROTECTED_SUFFIXES)


def contains_protected(path):
    """True if the path, or anything inside it, is something we must never move."""
    if name_protected(path.name):
        return True
    if path.is_dir() and not path.is_symlink():
        for dirpath, dirs, files in os.walk(path):
            if any(name_protected(n) for n in dirs + files):
                return True
    return False


def measure(path):
    """Return (bytes, newest modification time) for a file or folder, without following links."""
    try:
        st = path.lstat()
    except OSError:
        return 0, 0
    if not path.is_dir() or path.is_symlink():
        return st.st_size, st.st_mtime
    total, newest = 0, 0
    for dirpath, dirs, files in os.walk(path):
        for n in files:
            try:
                s = os.lstat(os.path.join(dirpath, n))
                total += s.st_size
                newest = max(newest, s.st_mtime)
            except OSError:
                pass
    return total, newest or st.st_mtime


def scan(home):
    """List every item the catalog knows about, with its size, age and kind."""
    home = Path(home)
    items, seen = [], set()
    # `keep` groups go first so a protected path is never claimed by a cleanable group.
    for g in sorted(CATALOG, key=lambda g: g.kind != "keep"):
        for pattern in g.globs:
            for m in sorted(glob.glob(str(home / pattern))):
                p = Path(m)
                if str(p) in seen:
                    continue
                seen.add(str(p))
                size, mtime = measure(p)
                kind = g.kind
                if kind in ("cache", "history", "model") and contains_protected(p):
                    kind = "keep"
                items.append({"tool": g.tool, "kind": kind, "label": g.label, "note": g.note,
                              "path": str(p), "rel": str(p.relative_to(home)), "bytes": size, "mtime": mtime})
    return items


def select(items, kinds, tool=None, older_than_days=0, min_age_hours=1, now=None):
    now = now or time.time()
    out = []
    for it in items:
        if it["kind"] not in kinds or it["kind"] in ("keep", "manual"):
            continue
        if tool and tool.lower() not in it["tool"].lower():
            continue
        age = now - it["mtime"]
        if age < min_age_hours * 3600 or age < older_than_days * DAY:
            continue  # too new: might be in use right now
        if os.path.islink(it["path"]):
            continue
        out.append(it)
    return out


def move_to_trash(items, home, now=None):
    now = now or time.time()
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    root = Path(home) / TRASH / stamp
    moved = []
    for it in items:
        src = Path(it["path"])
        if contains_protected(src):
            continue  # last line of defence
        dst = root / it["rel"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        moved.append({"rel": it["rel"], "bytes": it["bytes"], "tool": it["tool"], "label": it["label"]})
    if moved:
        (root / "manifest.json").write_text(json.dumps({"stamp": stamp, "moved": moved}, indent=2))
    return stamp, moved


def list_trash(home):
    root = Path(home) / TRASH
    out = []
    for m in sorted(root.glob("*/manifest.json")) if root.exists() else []:
        data = json.loads(m.read_text())
        out.append({"stamp": data["stamp"], "count": len(data["moved"]), "bytes": sum(x["bytes"] for x in data["moved"])})
    return out


def restore(home, stamp):
    root = Path(home) / TRASH / stamp
    data = json.loads((root / "manifest.json").read_text())
    restored, skipped = 0, []
    for it in data["moved"]:
        src, dst = root / it["rel"], Path(home) / it["rel"]
        if dst.exists():
            skipped.append(it["rel"])
            continue
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            restored += 1
    return restored, skipped


def empty_trash(home, older_than_days=7, now=None):
    now = now or time.time()
    root = Path(home) / TRASH
    freed = 0
    for entry in list_trash(home):
        d = root / entry["stamp"]
        if now - (d / "manifest.json").stat().st_mtime >= older_than_days * DAY:
            freed += entry["bytes"]
            shutil.rmtree(d)
    return freed
