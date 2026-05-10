# claude-code-statusline

A card-style status line for [Claude Code](https://claude.ai/code) that displays real-time model info, rate limit usage, and context window usage.

```
╭─ 🐉  Opus 4.7 ─────────────────────────────────────────╮
│  effort:max  advisor:Opus 4.7  plan:Max×5  ⏱ 48:23     │
│  上下文  ▓▓▓░░░░░░░░░░░░  18.4%                         │
│  5h      ████████░░░░░░  48.0%  ↺ 2h 15m                │
│  7d      █████░░░░░░░░░  31.0%  ↺ 3d 12h                │
╰─────────────────────────────────────────────────────────╯
```

## What it shows

| Row | Content |
|-----|---------|
| Title | Companion emoji · Model name · Session name |
| Row 1 | `effortLevel` · `advisorModel` · Subscription tier · Session duration |
| Row 2 | Context window usage (current conversation) |
| Row 3 | 5-hour rate limit usage + time until reset |
| Row 4 | 7-day rate limit usage + time until reset |

Progress bar colors: green < 50% · yellow < 80% · red ≥ 80%

## Requirements

- Python 3.8+
- Claude Code (CLI, desktop app, or VS Code extension)
- A Claude subscription (Pro / Max / Max×5)

> Rate limit rows show `── 等待首次响应 ──` until the first API response in a session arrives.

## Installation

### 1. Copy the script

```bash
mkdir -p ~/.claude/scripts
cp status_line.py ~/.claude/scripts/status_line.py
```

### 2. Add to `~/.claude/settings.json`

```json
{
  "statusLine": {
    "type": "command",
    "command": "python ~/.claude/scripts/status_line.py",
    "refreshInterval": 30
  }
}
```

**Windows users** — use the full path with forward slashes:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python C:/Users/<YourName>/.claude/scripts/status_line.py",
    "refreshInterval": 30
  }
}
```

### 3. Restart Claude Code

The status line appears at the bottom of the interface after restart.

## Rate limit caching

The script caches rate limit data in `~/.claude/session-env/rate_limits_cache.json`.
Usage percentages persist across sessions — the cached value from the previous session is shown
until a fresher reading arrives from the current session's first API call.

## Companion emoji

If you have a companion configured in `~/.claude.json`, the script maps companion name keywords
to an emoji:

| Keywords | Emoji |
|----------|-------|
| scale, fang, ember, cinder, flame, ash, brine, dragon | 🐉 |
| spark, volt, thunder, storm | ⚡ |
| frost, ice, snow, crystal | ❄️ |
| shadow, night, dark, void | 🌑 |
| (anything else) | 🐾 |

Set `"companionMuted": true` in `~/.claude.json` to hide the emoji.

## Customization

Edit the constants at the top of `status_line.py`:

| Constant | Default | Effect |
|----------|---------|--------|
| `PROGRESS_WIDTH` | `14` | Width of progress bars (characters) |
| `MIN_BOX_INNER` | `50` | Minimum card inner width |

The `refreshInterval` (seconds) is set in `settings.json`.

## How it works

Claude Code calls the script on each refresh, piping a JSON payload via stdin.
The script reads:
- `model.display_name` — current model
- `rate_limits` — 5h/7d usage percentages and reset timestamps
- `context_window.used_percentage` — context usage
- `cost.total_duration_ms` — session duration
- `session_name` — named session (if set)

It also reads local files:
- `~/.claude/settings.json` — `effortLevel`, `advisorModel`
- `~/.claude/.credentials.json` — subscription tier
- `~/.claude.json` — companion name

## License

MIT
