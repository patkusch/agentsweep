"""What each tool leaves on disk, and what is safe to do about it.

Kinds:
  cache   rebuilt automatically. Safe to clear.
  history old conversations and logs. Safe, but you lose the ability to look back at them.
  model   big downloads. Safe, but they have to be downloaded again.
  manual  belongs to another program. We show it; you clear it with that program's own command.
  keep    yours (memory, settings, keys). Never touched.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Group:
    tool: str
    kind: str
    label: str
    globs: tuple  # each match is one item; paths are relative to the home folder
    note: str = ""


CATALOG = [
    # --- Claude Code
    Group("Claude Code", "cache", "Caches and logs",
          (".claude/cache/*", ".claude/debug/*", ".claude/shell-snapshots/*", ".claude/session-env/*",
           ".claude/paste-cache/*", ".claude/statsig/*", ".claude/telemetry/*"),
          "Rebuilt automatically."),
    Group("Claude Code", "history", "Old conversations",
          (".claude/projects/*/*.jsonl", ".claude/projects/*/????????-????-????-????-????????????",
           ".claude/file-history/*", ".claude/backups/*", ".claude/todos/*"),
          "You can no longer resume or search these."),
    Group("Claude Code", "keep", "Memory, settings, skills, plugins",
          (".claude/projects/*/memory", ".claude/settings*.json", ".claude/CLAUDE.md", ".claude/skills",
           ".claude/agents", ".claude/commands", ".claude/plugins", ".claude.json", ".claude/.credentials.json")),
    # --- Codex
    Group("Codex", "cache", "Caches and logs",
          (".codex/tmp/*", ".codex/cache/*", ".codex/log/*", ".codex/logs_*.sqlite*"),
          "Rebuilt automatically."),
    Group("Codex", "history", "Old conversations",
          (".codex/sessions/*", ".codex/archived_sessions/*", ".codex/history.jsonl"),
          "You can no longer resume or search these."),
    Group("Codex", "manual", "Installed plugins and helpers",
          (".codex/plugins", ".codex/computer-use"), "Remove with Codex itself."),
    Group("Codex", "keep", "Settings, sign-in, skills",
          (".codex/config.toml", ".codex/auth.json", ".codex/skills", ".codex/AGENTS.md", ".codex/state_*.sqlite*")),
    # --- Ollama
    Group("Ollama", "manual", "Downloaded models", (".ollama/models",), "Remove one with: ollama rm <name>"),
    Group("Ollama", "keep", "Your Ollama key", (".ollama/id_ed25519*",)),
    # --- Hugging Face
    Group("Hugging Face", "model", "Downloaded models", (".cache/huggingface/hub/models--*", ".cache/huggingface/hub/datasets--*"),
          "Downloaded again the next time something asks for it."),
    # --- LM Studio
    Group("LM Studio", "manual", "Downloaded models", (".lmstudio/models",), "Remove in LM Studio's My Models tab."),
    # --- Gemini CLI, Cursor
    Group("Gemini CLI", "cache", "Caches and logs", (".gemini/tmp/*",), "Rebuilt automatically."),
    Group("Cursor", "cache", "Caches and logs", (".cursor/logs/*",), "Rebuilt automatically."),
]

# Refused whatever a rule matches. This is the safety net.
PROTECTED_NAMES = {
    "memory", "skills", "agents", "commands", "plugins", "hooks", ".ssh", ".aws", ".gnupg",
    "CLAUDE.md", "AGENTS.md", "auth.json", "config.toml", ".credentials.json", ".claude.json", ".env", ".netrc",
}
PROTECTED_PREFIXES = ("settings", "id_", "credentials")
PROTECTED_SUFFIXES = (".pem", ".key", ".p12", ".pub")
