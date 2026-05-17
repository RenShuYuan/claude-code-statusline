#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code 状态栏 — 卡片式布局
数据来源：Claude Code 通过 stdin 注入的 JSON（含实时限额）+ 本地配置文件

  ╭─ ❄️  Opus ─────────────────────────────────────────╮
  │  effort:high  advisor:Opus  plan:Max×5  ⏱ 48:23    │
  │  context ██░░░░░░░░░░░░  18.4%                     │
  │  5h      ██████████░░░░  48.0%  ↺ 2h 15m           │
  │  7d      █████░░░░░░░░░  31.0%  ↺ 3d 12h           │
  ╰────────────────────────────────────────────────────╯
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import json, os, time, re, unicodedata

# ══════════════════════════════════════════════════════════
PROGRESS_WIDTH = 14     # 进度条字符宽度
MIN_BOX_INNER  = 50     # 卡片最小内宽（字符）
EMOJI_OVERRIDE = "❄️"   # 设为 None 时回退到按 companion name 关键字自动匹配
# ══════════════════════════════════════════════════════════

HOME       = os.path.expanduser("~")
CLAUDE_DIR = os.path.join(HOME, ".claude")
RL_CACHE   = os.path.join(CLAUDE_DIR, "session-env", "rate_limits_cache.json")

TIER_DISPLAY = {
    "default_claude_max_5x": "Max×5",
    "default_claude_max":    "Max",
    "default_claude_pro":    "Pro",
    "free":                  "Free",
}
MODEL_ABBR = {
    "sonnet": "Sonnet 4.6",
    "opus":   "Opus 4.7",
    "haiku":  "Haiku 4.5",
}

# ── ANSI / 工具 ───────────────────────────────────────────
def c(text, code):
    return f"\033[{code}m{text}\033[0m"

def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

# ── 跨 session 共享 rate_limits 缓存 ─────────────────────
def _rl_pct(rl):
    """取 five_hour used_percentage 作为新旧判断依据（用量只增不减）"""
    return (rl.get("five_hour") or {}).get("used_percentage") or 0

def _rl_reset(rl):
    """取 five_hour resets_at，用于判断是否跨了重置窗口"""
    return (rl.get("five_hour") or {}).get("resets_at") or 0

def load_rl_cache():
    cache = read_json(RL_CACHE)
    return cache.get("rate_limits", {}) if cache else {}

def save_rl_cache(rl):
    try:
        os.makedirs(os.path.dirname(RL_CACHE), exist_ok=True)
        with open(RL_CACHE, "w", encoding="utf-8") as f:
            json.dump({"rate_limits": rl, "saved_at": time.time()}, f)
    except Exception:
        pass

def best_rate_limits(stdin_rl):
    """返回最新的 rate_limits：优先用使用率更高的那份，并将其写回缓存。"""
    cached = load_rl_cache()
    if not stdin_rl and not cached:
        return {}
    if not stdin_rl:
        return cached
    if not cached:
        save_rl_cache(stdin_rl)
        return stdin_rl
    # 若 resets_at 不同，说明已跨重置窗口，用更晚的那个
    if _rl_reset(stdin_rl) != _rl_reset(cached):
        winner = stdin_rl if _rl_reset(stdin_rl) > _rl_reset(cached) else cached
    else:
        winner = stdin_rl if _rl_pct(stdin_rl) >= _rl_pct(cached) else cached
    save_rl_cache(winner)
    return winner

# ── 终端显示宽度（emoji / 中文双字宽）────────────────────
_WIDE_RANGES = [
    (0x1100,0x115F),(0x2E80,0x303E),(0x3041,0xA4CF),(0xA960,0xA97C),
    (0xAC00,0xD7A3),(0xF900,0xFAFF),(0xFE10,0xFE1F),(0xFE30,0xFE6F),
    (0xFF01,0xFF60),(0xFFE0,0xFFE6),(0x1B000,0x1B0FF),(0x1F004,0x1F0CF),
    (0x1F200,0x1F2FF),(0x1F300,0x1FAFF),(0x20000,0x2FFFD),(0x30000,0x3FFFD),
]

def _char_width(ch):
    if unicodedata.east_asian_width(ch) in ('W','F'):
        return 2
    cp = ord(ch)
    for lo, hi in _WIDE_RANGES:
        if lo <= cp <= hi:
            return 2
    return 1

def vlen(s):
    clean = re.sub(r'\033\[[0-9;]*m', '', s)
    return sum(_char_width(ch) for ch in clean)

# ── 卡片绘制 ──────────────────────────────────────────────
def make_box(title, rows):
    title_w = vlen(title)
    inner   = max(title_w + 4, max((vlen(r) for r in rows), default=0) + 4, MIN_BOX_INNER)
    fill    = inner - title_w - 3
    top     = f"╭─ {title} " + "─" * max(1, fill) + "╮"
    lines   = [f"│  {row}" + " " * max(0, inner - 4 - vlen(row)) + "  │" for row in rows]
    bottom  = "╰" + "─" * inner + "╯"
    return "\n".join([top] + lines + [bottom])

# ── 进度条 ────────────────────────────────────────────────
def progress_bar(pct, ctx=False):
    """pct: 0–100 的浮点数；ctx=True 用于上下文窗口（不同风格）"""
    pct    = max(0.0, min(100.0, pct or 0.0))
    filled = round(pct / 100 * PROGRESS_WIDTH)
    if ctx:
        bar  = "▓" * filled + "░" * (PROGRESS_WIDTH - filled)
        code = "36" if pct < 50 else ("33" if pct < 80 else "31")
    else:
        bar  = "█" * filled + "░" * (PROGRESS_WIDTH - filled)
        code = "32" if pct < 50 else ("33" if pct < 80 else "31")
    return f"\033[{code}m{bar}\033[0m  \033[{code}m{pct:.1f}%\033[0m"

# ── 重置倒计时 ────────────────────────────────────────────
def format_reset(resets_at):
    if not resets_at:
        return ""
    remaining = int(resets_at - time.time())
    if remaining <= 0:
        return c(" ↺ 即将重置", "33")
    d, rem = divmod(remaining, 86400)
    h, rem = divmod(rem, 3600)
    m      = rem // 60
    if d > 0:
        txt = f" ↺ {d}d {h}h"
    elif h > 0:
        txt = f" ↺ {h}h {m}m"
    else:
        txt = f" ↺ {m}m"
    return c(txt, "90")

# ── 时长格式化 ────────────────────────────────────────────
def format_ms(ms):
    s = int((ms or 0) / 1000)
    h, rem = divmod(s, 3600)
    m, s   = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# ── 伴侣 emoji ────────────────────────────────────────────
def companion_emoji(name):
    n = name.lower()
    if any(w in n for w in ("scale","fang","ember","cinder","flame","ash","brine","dragon")):
        return "🐉"
    if any(w in n for w in ("spark","volt","thunder","storm")):
        return "⚡"
    if any(w in n for w in ("frost","ice","snow","crystal")):
        return "❄️"
    if any(w in n for w in ("shadow","night","dark","void")):
        return "🌑"
    return "🐾"

# ── 主逻辑 ────────────────────────────────────────────────
def main():
    # ── 读取 stdin JSON（Claude Code 注入的会话数据）──────
    data = json.load(sys.stdin)

    model_name  = data.get("model", {}).get("display_name", "?")
    duration_ms = data.get("cost", {}).get("total_duration_ms") or 0

    rl       = best_rate_limits(data.get("rate_limits") or {})
    five_h   = rl.get("five_hour") or {}
    seven_d  = rl.get("seven_day") or {}
    pct_5h   = five_h.get("used_percentage")   # None 表示尚无数据
    pct_7d   = seven_d.get("used_percentage")
    reset_5h = five_h.get("resets_at")
    reset_7d = seven_d.get("resets_at")

    ctx_win      = data.get("context_window") or {}
    pct_ctx      = ctx_win.get("used_percentage")   # None 表示首次响应前
    session_name = data.get("session_name", "")

    # ── 读取本地配置（settings / credentials / state）─────
    settings = read_json(os.path.join(CLAUDE_DIR, "settings.json"))
    creds    = read_json(os.path.join(CLAUDE_DIR, ".credentials.json"))
    state    = read_json(os.path.join(HOME, ".claude.json"))

    effort   = settings.get("effortLevel", "")
    adv_raw  = settings.get("advisorModel", "")
    advisor  = MODEL_ABBR.get(adv_raw, adv_raw)

    oauth    = creds.get("claudeAiOauth", {})
    plan     = TIER_DISPLAY.get(oauth.get("rateLimitTier",""), oauth.get("subscriptionType","?"))

    comp        = state.get("companion", {})
    comp_name   = comp.get("name", "")
    comp_muted  = state.get("companionMuted", False)
    if comp_muted:
        emoji = ""
    elif EMOJI_OVERRIDE is not None:
        emoji = EMOJI_OVERRIDE
    else:
        emoji = companion_emoji(comp_name) if comp_name else ""

    # ── 标题：伴侣图标 + 模型名 + 会话名 ──────────────────
    title_parts = []
    if emoji:
        title_parts.append(emoji)
    title_parts.append(c(model_name, "36"))
    if session_name:
        title_parts.append(c(f"[{session_name}]", "90"))
    title = "  ".join(title_parts)

    # ── 第一行：参数信息 ───────────────────────────────────
    row1 = []
    if effort:
        ec = {"low":"32","medium":"33","high":"33","max":"31"}.get(effort,"33")
        row1.append(f"effort:{c(effort, ec)}")
    if advisor:
        row1.append(f"advisor:{c(advisor, '35')}")
    row1.append(f"plan:{c(plan, '32')}")
    # ── 第二行：上下文窗口（当前对话）+ 会话时长 ──────────
    duration_str = f"  ⏱ {c(format_ms(duration_ms), '90')}" if duration_ms else ""
    if pct_ctx is not None:
        row2 = f"{c('context', '90')} {progress_bar(pct_ctx, ctx=True)}{duration_str}"
    else:
        row2 = f"{c('context', '90')} {c('── 等待首次响应 ──', '90')}{duration_str}"

    # ── 第三行：5 小时订阅用量 ────────────────────────────
    if pct_5h is not None:
        row3 = f"{c('5h', '90')}      {progress_bar(pct_5h)}{format_reset(reset_5h)}"
    else:
        row3 = f"{c('5h', '90')}      {c('── 等待首次响应 ──', '90')}"

    # ── 第四行：7 天订阅用量 ──────────────────────────────
    if pct_7d is not None:
        row4 = f"{c('7d', '90')}      {progress_bar(pct_7d)}{format_reset(reset_7d)}"
    else:
        row4 = f"{c('7d', '90')}      {c('── 等待首次响应 ──', '90')}"

    print(make_box(title, ["  ".join(row1), row2, row3, row4]))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(f"╭─ claude ─╮\n│  status unavailable  │\n╰──────────╯")
