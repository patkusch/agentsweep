# agentsweep

[![ci](https://github.com/patkusch/agentsweep/actions/workflows/ci.yml/badge.svg)](https://github.com/patkusch/agentsweep/actions/workflows/ci.yml)

See what your AI agent tools have piled up on your disk, and clear it safely.

> Agent tools quietly keep old conversations, logs, caches and model downloads. agentsweep shows you what is taking space and moves what you choose to a trash folder. You can put it all back.

No dependencies. Python 3.9+. Nothing leaves your machine.

## Use it

```bash
pip install git+https://github.com/patkusch/agentsweep
agentsweep                                   # what is taking space
agentsweep clean --kind cache                # show what would move
agentsweep clean --kind cache --yes          # move it to the trash folder
agentsweep clean --kind history --older-than 60 --yes
agentsweep restore 20260929-220746           # changed your mind
agentsweep empty-trash --older-than 7 --yes  # only now is anything really deleted
```

What the report looks like:

```
Claude Code   221.8 MB
  Caches and logs                  139.4 KB   20 item(s)
      safe to clear, rebuilt automatically
  Old conversations                215.5 MB   48 item(s), oldest 2026-08-16
      safe to clear, but you lose the old conversations
  Memory, settings, skills, plugins  6.2 MB   5 item(s)
      yours, never touched
```

## What is safe, and why

Every item is one of five kinds:

| Kind | Meaning | What `clean` does |
|---|---|---|
| cache | Rebuilt automatically | Moves it (default kind) |
| history | Old conversations and logs. You lose the ability to look back. | Moves it if older than 30 days (change with `--older-than`) |
| model | Big downloads. They have to be fetched again. | Moves it if older than 30 days |
| manual | Owned by another program, for example Ollama models | Shows it, never moves it. It tells you the right command instead. |
| keep | Memory, settings, skills, keys, sign-in | Never touched |

Extra guards, all tested:

- **Nothing is deleted.** Clean-ups go to `~/.agentsweep-trash/<time>/` with a list of what moved. `restore` puts them back, and it won't overwrite anything new.
- **Dry run first.** Without `--yes`, `clean` only shows what would move.
- **Protected names win over every rule.** Anything called `memory`, `settings*`, `skills`, `plugins`, `CLAUDE.md`, `id_*`, `*.key`, `.env`, `auth.json` and similar is refused, even inside a folder a rule would otherwise clear. A conversation folder that contains one is kept whole.
- **Recent files are skipped** (touched in the last hour), so a session you have open is safe.
- **Links are not followed**, so a shortcut can't lead it outside the agent folders.

## Covers

Claude Code, Codex, Ollama, Hugging Face, LM Studio, Gemini CLI, Cursor. The list is one file: [`agentsweep/catalog.py`](agentsweep/catalog.py). Adding a tool is a few lines.

## Honest limits

- Ages use "last changed", not "last opened", because the computer doesn't reliably record the second one.
- The catalog reflects where these tools keep things today. If a tool moves its files, the report simply won't see them; it never guesses.
- It only knows the tools in the catalog. Unknown folders are left alone.

## Tests

```bash
python3 -m unittest discover -s tests
```

MIT licensed.
