# AutoLibrary

**Auto-load curated knowledge into every Claude Code session.**

You keep hand-written notes — how your infra works, your device setup, project
context, API playbooks. But Claude Code doesn't see them unless it goes looking,
and pasting them into `CLAUDE.md` bloats every session. AutoLibrary injects a
**compact index** of your knowledge at session start, so the model always knows
*what exists and where*, then reads the full detail only when it needs to.

Toggle what loads **per machine** — no `settings.json` editing, no code changes.

## The model: Library ⊃ Volume ⊃ Entry

| Term | What it is | On disk |
|---|---|---|
| **Library** | the whole system (this plugin) | — |
| **Volume** | one knowledge domain | a directory, e.g. `capabilities/` |
| **Entry** | one topic in a Volume | a folder, e.g. `capabilities/scholar-search/` |
| **INDEX.md** | a Volume's compact table of contents | injected at session start |

Only each Volume's `INDEX.md` (one terse line per Entry) enters the context.
The Entries themselves — full docs, assets — stay on disk and are read on demand.

## Install

This repo is a plugin **and** its own marketplace. In Claude Code:

```
/plugin marketplace add nmhjklnm/auto-library
/plugin install auto-library@auto-library
```

That's it — the bundled `SessionStart` hook registers itself. You never edit
`settings.json`.

**Try it without installing** (this session only):

```bash
claude --plugin-dir /path/to/auto-library
```

**Uninstall**: `/plugin uninstall auto-library@auto-library`

## Configure

Point AutoLibrary at your Volumes. Create a config at any of these (first found
wins) — `$AUTOLIBRARY_CONFIG`, `$CLAUDE_CONFIG_DIR/autolibrary.json`, or
`~/.claude/autolibrary.json`. See `autolibrary.example.json`:

```json
{
  "per_volume_char_cap": 1500,
  "total_char_cap": 8000,
  "volumes": [
    { "name": "capabilities", "index": "/path/to/capabilities/INDEX.md", "enabled": true },
    { "name": "devices",      "index": "/path/to/devices/INDEX.md",      "enabled": false }
  ]
}
```

- Add a Volume → add a line. Disable one on this machine → `"enabled": false`.
- The config is per-machine: a different file on each host loads a different set.
- Char caps bound the injected size, so a runaway INDEX can't blow up context.

## Why it's cheap

The hook fires **once per session** (SessionStart), and the injected index is
held in the model's prompt cache for the rest of the session — so the cost is a
small, capped, one-time write per session, not a per-turn tax. Keep each
`INDEX.md` terse (one line per Entry) and the whole thing stays lightweight.

## Writing a Volume

A Volume is just a directory with an `INDEX.md` and one folder per Entry:

```
capabilities/
├── INDEX.md                 # compact: one line per Entry (this is what's injected)
├── scholar-search/          # an Entry
│   └── README.md            # full detail (read on demand)
└── community-comment-apis/
    └── README.md
```

`INDEX.md` should be scannable and terse:

```markdown
# capabilities
- scholar-search — academic search over OpenAlex + arXiv, no API key
- community-comment-apis — pull comment threads from 9 platforms, no login
```

## License

MIT
