# AutoLibrary on Codex CLI

The same loader powers both Claude Code and [Codex CLI](https://developers.openai.com/codex/hooks).
Codex's `SessionStart` hook supports the same context injection — it accepts
plain text on stdout as additional session context — so AutoLibrary works there
with the identical `library-load.py` and the identical config file.

## Install

Codex has no plugin marketplace; you register the hook in `config.toml`. Append
`config.snippet.toml` to `~/.codex/config.toml` (or `$CODEX_HOME/config.toml`),
replacing the path with where you cloned this repo:

```toml
[features]
hooks = true

[[hooks.SessionStart]]
[[hooks.SessionStart.hooks]]
command = "python3 /ABSOLUTE/PATH/TO/auto-library/hooks/library-load.py codex"
```

The `codex` argument switches the loader to plain-text output (Codex's format);
without it the loader emits the Claude Code JSON envelope.

## Configure

Same config file as the Claude Code version — the loader also looks in
`$CODEX_HOME/autolibrary.json` and `~/.codex/autolibrary.json`. See the top-level
[`autolibrary.example.json`](../autolibrary.example.json) and README.

## Notes

- Put the hook in the **global** `~/.codex/config.toml`. Repo-local
  `.codex/config.toml` hooks are known not to fire in interactive sessions
  ([openai/codex#17532](https://github.com/openai/codex/issues/17532)).
- Everything else — Volumes, `<name>.md` indexes, per-machine toggling, char
  caps, fail-safe — behaves exactly as in the Claude Code version.
