#!/usr/bin/env python3
"""AutoLibrary — SessionStart loader.

Reads a per-machine config listing the Library's Volumes, and injects the
compact INDEX of each *enabled* Volume into the session context via
`hookSpecificOutput.additionalContext`. Character caps keep the injected
context small; the full detail stays on disk in each Volume's Entries.

Model: Library ⊃ Volume ⊃ Entry
  - Library      = the whole system (this plugin)
  - Volume       = one knowledge domain (a folder), e.g. "capabilities"
  - Entry        = one topic inside a Volume (a folder)
  - <name>.md    = the compact, injected index of a Volume, named after it
                   (a Volume named "workspace" → workspace.md, not INDEX.md)

Config lookup order (first found wins), so different machines load different
Volumes just by shipping a different config file — no code changes:
  1. $AUTOLIBRARY_CONFIG
  2. $CLAUDE_CONFIG_DIR/autolibrary.json
  3. ~/.claude/autolibrary.json

Config shape — register each Volume by name + its folder; the index loaded is
<path>/<name>.md (an explicit "index" path overrides this):
  {
    "per_volume_char_cap": 1500,   // optional, default 1500
    "total_char_cap": 8000,        // optional, default 8000
    "volumes": [
      {"name": "capability", "path": "/abs/capabilities", "enabled": true},
      {"name": "workspace",  "path": "/abs/workspace",    "enabled": false}
    ]
  }

Fail-safe: any error (missing/broken config, unreadable index) degrades to an
empty injection rather than breaking the session.
"""
import json
import os
import sys


def find_config():
    """Locate the config from USER-controlled, machine-global locations only.

    Deliberately does NOT read a per-project config (e.g. $CLAUDE_PROJECT_DIR):
    the hook runs globally with no per-project trust gate, so honoring a config
    shipped inside a cloned repo would let that repo point `index` at arbitrary
    files (~/.ssh/id_rsa, .env, …) and exfiltrate them into the model context,
    or inject attacker-controlled prose as trusted context. Config lives with
    the user, never with the project.
    """
    candidates = [os.environ.get("AUTOLIBRARY_CONFIG")]
    for env_dir in ("CLAUDE_CONFIG_DIR", "CODEX_HOME"):
        d = os.environ.get(env_dir)
        if d:
            candidates.append(os.path.join(d, "autolibrary.json"))
    candidates.append(os.path.expanduser("~/.claude/autolibrary.json"))
    candidates.append(os.path.expanduser("~/.codex/autolibrary.json"))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def clip(text, cap):
    if cap and len(text) > cap:
        return text[:cap].rstrip() + f"\n…[truncated {len(text)}→{cap} chars]"
    return text


def build_context(conf):
    per_cap = conf.get("per_volume_char_cap", 1500)
    total_cap = conf.get("total_char_cap", 8000)
    parts, used = [], 0
    for vol in conf.get("volumes", []):
        if not vol.get("enabled"):
            continue
        name = vol.get("name", "?")
        # Index file is named after the Volume: <path>/<name>.md (not a generic
        # INDEX.md). An explicit "index" overrides this if given.
        index_path = vol.get("index")
        if not index_path and vol.get("path"):
            index_path = os.path.join(vol["path"], name + ".md")
        try:
            with open(index_path, encoding="utf-8") as f:
                body = f.read().rstrip()
        except Exception:
            body = f"# [{name}] Volume index missing: {index_path}"
        body = clip(body, per_cap)
        if total_cap and used + len(body) > total_cap:
            remaining = total_cap - used
            if remaining > 0:
                parts.append(clip(body, remaining))
            parts.append(f"\n…[AutoLibrary total cap {total_cap} reached; remaining Volumes not loaded]")
            break
        parts.append(body)
        used += len(body)
    return "\n\n".join(parts)


def main():
    # Host mode: "claude" (default) emits the Claude Code hook JSON envelope;
    # "codex" emits plain text on stdout — both inject it as SessionStart context.
    host = sys.argv[1].lower() if len(sys.argv) > 1 else "claude"

    # Consume (and ignore) the hook's stdin payload.
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    ctx = ""
    path = find_config()
    if path:
        try:
            with open(path, encoding="utf-8") as f:
                ctx = build_context(json.load(f))
        except Exception:
            ctx = ""

    if host == "codex":
        # Codex SessionStart accepts plain text on stdout as additionalContext.
        sys.stdout.write(ctx)
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
