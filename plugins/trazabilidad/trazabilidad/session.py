"""
The notice shown when a Claude Code session opens in the repo.

Branch, how far behind the main branch, uncommitted changes, and whether the
commit hook is active; plus «the main branch changed» (see `watch.py`), whose
quick, throttled fetch is the only network call. When the fetch can't run, the
counts come from the last successful fetch and say when that was, taken from
the remote branch's reflog — git touches FETCH_HEAD even when a fetch fails.

Output is Claude Code hook JSON: `systemMessage` is shown to the person,
`additionalContext` goes to Claude. It never fails: what can't be known is left out.
"""
from __future__ import annotations

import json
import subprocess
import time

from .config import Config
from .messages import t
from .watch import main_changes


def _git(root: str, *args: str) -> str | None:
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                           encoding="utf-8", timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _ago(lang: str, seconds: float) -> str:
    hours = seconds / 3600
    if hours < 1:
        return t(lang, "ago_hour")
    if hours < 48:
        return t(lang, "ago_hours", n=int(hours))
    return t(lang, "ago_days", n=int(hours / 24))


def notices(config: Config) -> list[str]:
    root, lang, main = config.root, config.language, config.main_branch
    branch = _git(root, "branch", "--show-current")
    if branch is None:
        return []  # not a git repository
    changes = main_changes(config)
    lines = []
    if branch == main:
        lines.append(t(lang, "session_on_main", main=main))
    elif not branch:
        lines.append(t(lang, "session_detached"))
    else:
        lines.append(t(lang, "session_branch", branch=branch))

    counts = _git(root, "rev-list", "--left-right", "--count", f"HEAD...origin/{main}")
    if counts:
        ahead, behind = (int(x) for x in counts.split())
        last = _git(root, "log", "-g", "-1", "--format=%ct", f"refs/remotes/origin/{main}")
        when = t(lang, "session_when", ago=_ago(lang, time.time() - int(last))) if last else ""
        if behind:
            lines.append(t(lang, "session_behind", n=behind, main=main, when=when))
        else:
            lines.append(t(lang, "session_up_to_date", n=ahead, main=main, when=when))

    dirty = _git(root, "status", "--porcelain", "--untracked-files=no")
    if dirty:
        lines.append(t(lang, "session_dirty", n=len(dirty.splitlines())))
    if not config.found:
        lines.append(t(lang, "session_no_config"))
    elif _git(root, "config", "core.hooksPath") != ".githooks":
        lines.append(t(lang, "session_no_hook"))
    return lines + changes


def hook_output(config: Config) -> str | None:
    lines = notices(config)
    if not lines:
        return None
    text = "Trazabilidad · " + " ".join(lines)
    return json.dumps({
        "systemMessage": text,
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text},
    }, ensure_ascii=False)
