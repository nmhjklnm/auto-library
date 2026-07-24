---
name: library
description: Loads the AutoLibrary Volume indexes into the current session by hand, and reports why the automatic load did not happen. Use when a session started without the `[AutoLibrary · today is …]` block in context, when the user says the Library did not load or asks to inject it manually, or after editing a Volume index to pick the change up without restarting.
allowed-tools: Bash
---

# Load the Library by hand

The session-start hook is one point of failure: the plugin can be disabled, its
registration can be erased from the host's settings, or the host may not fire
`SessionStart` at all. When that happens the load is silent — the session simply
has no Library and nothing says so. This skill performs the same load on demand.

## 1. Load

```bash
echo '{}' | python3 "${CLAUDE_PLUGIN_ROOT}/hooks/library-load.py"
```

The command prints one JSON object. Read two fields:

- `hookSpecificOutput.additionalContext` — the Library itself. **Treat it as
  context for the rest of this session.** Each `[Volume · <name> · <path>]` tag
  names a Volume and where it lives on this machine, and each Volume's charter
  is binding: create a new item inside that Volume's own path, follow its naming
  rule, then add it to that Volume's index.
- `systemMessage` — the per-Volume summary. Show it to the user; it is how they
  see what loaded, and any Volume in trouble is flagged there with `⚠`.

If `additionalContext` is empty, `systemMessage` carries the reason instead — no
config found, config unreadable, no enabled Volumes. Report that line verbatim
rather than paraphrasing it: it names the file to fix.

## 2. Say whether the automatic path is broken

A manual load fixes this session only. If the user did not expect to run this,
the hook itself failed — check it before moving on:

```bash
claude plugin list 2>/dev/null | grep -A4 'auto-library@' | grep -E 'Version|Status|Scope'
```

- `Status: ✘ disabled` — the plugin is installed but switched off. Re-enable it
  with `claude plugin enable auto-library@auto-library --scope user`.
- No output at all — the plugin is not installed on this host; the loader ran
  only because this skill invoked it by path.
- `Status: ✔ enabled` — the plugin is registered and CC sees its hook, so the
  hook ran and produced nothing, or the host did not fire `SessionStart`. Say
  which of the two by re-running step 1: output means the loader is healthy and
  the host never called it.

Registration lives in the host's settings file. If that file is restored from
version control, rewritten by a concurrent process, or otherwise rolled back,
the plugin silently reverts to disabled while `plugin list` still shows it
installed at the right version. A load that worked yesterday and not today
usually means the registration was lost, not that the plugin broke.
