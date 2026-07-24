<p align="center">
  <img src="./assets/readme/hero.gif" width="100%"
       alt="AutoLibrary — the library layer every coding agent installs. Skills is just one Volume of it. A session-start hook loads every Volume's compact index into every session, on Claude Code and Codex.">
</p>

<div align="center">

**The library layer every coding agent installs.**

Register anything as a **Volume** — Skills, capabilities, context, playbooks.
A session-start hook loads each Volume's compact index into every session, so the
agent starts already knowing what it has and where to find it.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
![Host: Claude Code](https://img.shields.io/badge/host-Claude%20Code-black)
![Host: Codex CLI](https://img.shields.io/badge/host-Codex%20CLI-black)
![Install: two commands](https://img.shields.io/badge/install-two%20commands-black)

</div>

---

## The idea

Programs don't re-derive the standard library — they `import` it. Your agent should too.

AutoLibrary turns anything you keep on disk — a folder of Skills, your API playbooks,
device setup, project context, whatever — into an installable **Volume**. At the start
of every session, a hook loads a **compact index** of each enabled Volume into the
agent's context. The agent sees the map up front; it opens the full material only when a
task actually needs it.

**Skills is just one Volume of it.** So is everything else you want every session to
start with. AutoLibrary doesn't care what's inside a Volume — it's the layer that loads
your Volumes into any agent, the same way every session.

## Not a plugin for one tool — a primitive for every agent

- **Every agent installs it.** Claude Code and Codex CLI ship today; the loader is
  host-agnostic, so anything with a session-start hook can load the same Library.
- **Register anything.** A Volume is just a folder with an index named after it. Skills,
  capabilities, context, references — AutoLibrary stays agnostic about the contents.
- **A Volume is a contract, not a listing.** Each index opens with a **charter**: what the
  Volume holds, where its items live, how they're named. The loader tags every Volume with
  its path straight from your config and tells the agent the charter is binding — so the
  *next* thing the agent creates lands inside the Volume, named its way, instead of
  scattered next to it. An index that only says what exists gets read and then ignored.
- **Grow without limit.** Add a Volume by adding one line; it costs nothing until enabled.
- **Shape per machine.** Your laptop and your server load different Volumes from the
  *same* Library.
- **Stay cheap.** The hook fires once per session and the index is prompt-cached; caps
  bound its size.
- **Time-aware.** A static index goes stale silently, and agents are time-blind. The
  loader stamps every injection with today's date and reminds the agent that entries are
  time-sensitive — so record `created` / `expires` / `last-verified`, and a machine past
  its expiry or an aged "LIVE" date gets caught instead of trusted.

## Install

### Claude Code

This repo is a plugin **and** its own marketplace:

```
/plugin marketplace add nmhjklnm/auto-library
/plugin install auto-library@auto-library
```

The bundled `SessionStart` hook self-registers — you never touch `settings.json`.
Try it first, no install: `claude --plugin-dir /path/to/auto-library`.

### Codex CLI

Add a `SessionStart` hook to `~/.codex/config.toml` — see
[`codex/README.md`](codex/README.md). Same loader, same config, same behavior.

## Configure

Point AutoLibrary at your Volumes with a JSON config, at any of (first found wins):
`$AUTOLIBRARY_CONFIG`, `$CLAUDE_CONFIG_DIR/autolibrary.json`,
`$CODEX_HOME/autolibrary.json`, or `~/.claude/autolibrary.json`. See
[`autolibrary.example.json`](autolibrary.example.json):

```json
{
  "per_volume_char_cap": 1500,
  "total_char_cap": 8000,
  "volumes": [
    { "name": "capabilities", "path": "/absolute/path/to/capabilities", "enabled": true },
    { "name": "skills",       "path": "/absolute/path/to/skills",       "enabled": true },
    { "name": "devices",      "path": "/absolute/path/to/devices",      "enabled": false }
  ]
}
```

- Register a Volume by `name` + `path`. Its index file is `<path>/<name>.md` —
  named after the Volume (`skills` → `skills.md`), not a generic `INDEX.md`.
- Flip `enabled` to load/unload per machine. Char caps keep the injection small.

## The model: Library ⊃ Volume ⊃ Entry

| Term | What it is | On disk |
|---|---|---|
| **Library** | every Volume an agent loads | — |
| **Volume** | one module you register | a folder, e.g. `capabilities/` |
| **Entry** | one item in a Volume | a folder, e.g. `capabilities/scholar-search/` |
| **`<name>.md`** | the Volume's compact index, named after it | injected at session start |
| **charter** | the index's opening lines — scope, where items live, naming | binding on the agent |

Only each Volume's `<name>.md` (one terse line per Entry) enters the context; the
Entries — full material, assets — stay on disk and are read on demand.

Each injected Volume is prefixed with `[Volume · <name> · <path>]`, generated from your
config — so the location is always present even if the charter forgets to state it.

## For agents (self-configuration)

> AutoLibrary is the library layer for coding agents: a session-start hook injects each
> enabled Volume's `<name>.md` index into context. To configure it, edit the JSON at
> `$AUTOLIBRARY_CONFIG`, `$CLAUDE_CONFIG_DIR/autolibrary.json`, or
> `~/.claude/autolibrary.json` — `volumes` is a list of `{name, path, enabled}`, and each
> Volume's index is `<path>/<name>.md`. Add a Volume → add an entry; toggle `enabled` per
> machine. The change takes effect on the next session; no restart needed. Open each index
> with a charter — what the Volume holds, where its items live, how they're named — and
> obey it: create new items inside that Volume's path, named its way, then add them to its
> index. Entries are time-sensitive: record when each was created/added and when it expires
> or was last verified, so stale or expired entries are caught rather than trusted.

An agent can read that one paragraph and configure AutoLibrary with no other docs.

## License

MIT — see [LICENSE](LICENSE).
