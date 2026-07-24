#!/usr/bin/env python3
"""AutoLibrary — SessionStart loader.

Reads a per-machine config listing the Library's Volumes, and injects the
compact INDEX of each *enabled* Volume into the session context via
`hookSpecificOutput.additionalContext`. Character caps keep the injected
context small; the full detail stays on disk in each Volume's Entries.

Model: Library ⊃ Volume ⊃ Entry
  - Library      = the whole system (this plugin)
  - Volume       = one module you register (a folder), e.g. "capabilities"
  - Entry        = one item inside a Volume
  - <name>.md    = the compact, injected index of a Volume, named after it
                   (a Volume named "workspace" → workspace.md, not INDEX.md)
  - charter      = the opening lines of <name>.md: what the Volume holds, where
                   its items live, how they are named. A Volume is a contract,
                   not just a listing — without it an agent reads the index and
                   still creates the next item in the wrong place. The loader
                   prepends each Volume's path from the config so the "where"
                   is always present even if the charter forgets to say it.

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
    // Both caps bound Volume content. The fixed preamble that states the
    // Library's rules sits outside them: capping it away would leave the
    // Volumes injected with nothing telling the agent how to treat them.
    "volumes": [
      {"name": "capability", "path": "/abs/capabilities"},                 // loads
      {"name": "workspace",  "path": "/abs/workspace", "enabled": false}   // off here
    ]
  }
"enabled" is optional and defaults to true — it exists to switch a Volume OFF on
one machine, not to arm it.

Fail-safe: any error (missing/broken config, unreadable index) degrades to an
empty injection rather than breaking the session.
"""
import datetime
import json
import os
import sys

# Fraction of per_volume_char_cap at which a Volume is reported as needing
# compaction. Derived rather than configured: one number to tune, and the
# warning line always tracks whatever cap is in force.
SOFT_RATIO = 0.8


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
    """Trim text to at most `cap` characters, marker included.

    The marker is part of the budget, not an extra on top of it: a cap that
    silently overshoots by the size of its own truncation notice is not a cap.
    """
    if not cap or len(text) <= cap:
        return text
    marker = f"\n…[truncated {len(text)}→{cap} chars]"
    if cap <= len(marker):
        # Too small to even announce the truncation — an absurd cap, but it
        # must still be obeyed rather than overrun by the notice about it.
        return "…"[:cap]
    return text[:cap - len(marker)].rstrip() + marker


def build_context(conf):
    """Return (context, report) — the injected text, and what went into it.

    The report is what the user is shown: injection is otherwise invisible, and
    a Library you cannot see loading is one you cannot trust is loading.
    """
    per_cap = conf.get("per_volume_char_cap", 1500)
    total_cap = conf.get("total_char_cap", 8000)
    # The "cap reached" notice is itself injected text, so reserve room for it
    # up front rather than appending it past the limit it announces — including
    # the blank line that joins it on.
    notice = f"\n…[AutoLibrary total cap {total_cap} reached; remaining Volumes not loaded]"
    notice_cost = len(notice) + 2
    parts, used, report = [], 0, []
    for vol in conf.get("volumes", []):
        # Registering a Volume is the act of wanting it; "enabled" exists to
        # turn one OFF per machine. Defaulting a missing key to disabled made
        # the documented minimal form ({name, path}) load nothing, silently —
        # the worst failure mode for a tool whose whole job is to speak up.
        if not vol.get("enabled", True):
            continue
        name = vol.get("name", "?")
        # Index file is named after the Volume: <path>/<name>.md (not a generic
        # INDEX.md). An explicit "index" overrides this if given.
        index_path = vol.get("index")
        if not index_path and vol.get("path"):
            index_path = os.path.join(vol["path"], name + ".md")
        if not index_path:
            # Registered with neither "path" nor "index": the Volume has no
            # location, so nothing loads and nothing new can be filed into it.
            # Name the missing keys instead of leaking a bare None.
            body = (f"# [{name}] Volume misconfigured: set \"path\" (its index "
                    f"is then <path>/{name}.md), or an explicit \"index\".")
            status = "misconfigured (no path/index)"
        else:
            try:
                with open(index_path, encoding="utf-8") as f:
                    body = f.read().rstrip()
                status = ""
            except Exception:
                body = f"# [{name}] Volume index missing: {index_path}"
                status = f"index missing: {index_path}"
        # The Volume's location is machine state, not prose: emit it from the
        # config so every Volume always carries its own path, whatever the
        # index author remembered to write. Without it an agent knows a Volume
        # exists but not where to put things — and scatters them elsewhere.
        location = vol.get("path") or (os.path.dirname(index_path) if index_path else "")
        tag = f"[Volume · {name} · {location}]" if location else f"[Volume · {name}]"
        # One terse line per Entry is the index convention, so "- " lines are
        # the honest entry count; it is a display figure, never a limit.
        entries = sum(1 for ln in body.splitlines() if ln.startswith("- "))
        # Clip the body, never the tag.
        block = tag + "\n" + clip(body, per_cap)
        # Volumes are joined with a blank line; count it, or total_char_cap
        # drifts by 2 chars per Volume and stops being the bound it claims.
        sep = 2 if parts else 0
        if total_cap and used + sep + len(block) + notice_cost > total_cap:
            remaining = total_cap - used - sep - len(tag) - 1 - notice_cost
            if remaining > 0:
                block = tag + "\n" + clip(body, remaining)
                parts.append(block)
                report.append((name, location, entries, len(block), status or "clipped (total cap)"))
            # Even the notice is subject to the cap it announces.
            if used + (2 if parts else 0) + len(notice) <= total_cap:
                parts.append(notice)
            break
        parts.append(block)
        used += sep + len(block)
        if len(block) < len(tag) + 1 + len(body):
            status = status or "clipped (volume cap)"
        elif per_cap and len(body) >= per_cap * SOFT_RATIO:
            # Warn before the cliff. Truncation cuts the tail of the file, not
            # the least useful entries, so by the time a Volume is clipped the
            # damage is already arbitrary — say it while there is still room to
            # compact the index deliberately.
            status = status or (f"{len(body):,}/{per_cap:,} chars — compact this "
                                "index before it gets truncated")
        report.append((name, location, entries, len(block), status))
    body_text = "\n\n".join(parts)
    if not body_text:
        return "", report
    # Two first-class Library principles, stated once per session:
    #  - a Volume is a contract (where its items live), not just a listing;
    #  - the Library is time-sensitive, and a static index goes stale silently.
    today = datetime.date.today().isoformat()
    header = (
        f"[AutoLibrary · today is {today}] Each Volume below is tagged with its "
        "name and its path on this machine, and opens with its charter — what "
        "the Volume holds, where its items live, how they are named. The "
        "charter is binding: create a new item inside that Volume's own path, "
        "follow its naming rule, then add it to that Volume's index. Never put "
        "a Volume's item somewhere else. The Library is also time-sensitive: "
        "entries record when they were created/added and, where it applies, "
        "when they expire or were last verified. Treat undated or long-stale "
        "entries as possibly out of date — a machine past its expiry may be "
        "gone, a 'LIVE' date may have aged; re-verify before relying. When you "
        "add or change an entry, record the date."
    )
    return header + "\n\n" + body_text, report


def format_summary(report, ctx):
    """A few lines the user actually sees: which Volumes loaded, from where.

    Injection is silent by design, which makes a broken Volume indistinguishable
    from a working one. Anything degraded is named on its own line rather than
    folded into a total.
    """
    if not report:
        return "AutoLibrary — no Volumes loaded (check your autolibrary.json)"
    width = max(len(name) for name, *_ in report)
    lines = [f"AutoLibrary — {len(report)} volume(s), {len(ctx):,} chars (~{len(ctx)//4:,} tokens)"]
    for name, location, entries, chars, status in report:
        line = f"  {name:<{width}}  {entries:>3} entries  {location or '(no path)'}"
        if status:
            line += f"  ⚠ {status}"
        lines.append(line)
    return "\n".join(lines)


def main():
    # Host mode: "claude" (default) emits the Claude Code hook JSON envelope;
    # "codex" emits plain text on stdout — both inject it as SessionStart context.
    host = sys.argv[1].lower() if len(sys.argv) > 1 else "claude"

    # Consume (and ignore) the hook's stdin payload.
    try:
        json.load(sys.stdin)
    except Exception:
        pass

    # Every way this can come up empty gets said out loud. A freshly installed
    # Library that injects nothing looks identical to one that is working, and
    # a stray comma in the config would otherwise disable everything in silence.
    ctx, report, note = "", [], ""
    default_config = os.path.join(
        os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"),
        "autolibrary.json")
    path = find_config()
    if not path:
        note = ("AutoLibrary — installed, but no config found, so nothing was "
                f"loaded.\n  Create {default_config} to register your first "
                "Volume:\n  {\"volumes\": [{\"name\": \"notes\", \"path\": "
                "\"/absolute/path/to/notes\"}]}  → loads /absolute/path/to/notes/notes.md")
    else:
        try:
            with open(path, encoding="utf-8") as f:
                conf = json.load(f)
        except Exception as exc:
            conf = None
            note = f"AutoLibrary — config unreadable, nothing loaded: {path}\n  {exc}"
        if conf is not None:
            try:
                ctx, report = build_context(conf)
            except Exception as exc:
                note = f"AutoLibrary — failed to build context from {path}\n  {exc}"
            if not report:
                note = (f"AutoLibrary — config at {path} has no enabled Volumes, "
                        "so nothing was loaded.")

    if host == "codex":
        # Codex SessionStart accepts plain text on stdout as additionalContext.
        sys.stdout.write(ctx)
        # Its stdout is the context itself, so the summary goes to stderr —
        # visible in the host's log without contaminating the injection.
        sys.stderr.write((format_summary(report, ctx) if report else note) + "\n")
    else:
        out = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": ctx,
            }
        }
        # systemMessage is the user-facing channel: additionalContext goes to
        # the model and is never shown, so without this the load is invisible.
        summary = format_summary(report, ctx) if report else note
        if summary:
            out["systemMessage"] = summary
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
