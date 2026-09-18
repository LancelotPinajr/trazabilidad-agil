"""
«The main branch changed»: tells you when `origin/<main>` moved since the last notice.

Runs at session start and before each prompt (Claude Code `UserPromptSubmit`).
To stay cheap it fetches at most every `watch.every_minutes`; in between it
only compares refs, which is instant. The fetch never prompts for a password
and gives up after a few seconds: with no network or no key it stays quiet
instead of hanging the session.

What was already announced is kept in `.git/trazabilidad-watch.json`, per
clone: it never enters the repository.
"""
from __future__ import annotations

import json
import os
import subprocess
import time

from .config import Config
from .messages import t

STATE_FILE = "trazabilidad-watch.json"
FETCH_TIMEOUT = 8
SHOWN_COMMITS = 5


def _git(root: str, *args: str, timeout: float = 5) -> str | None:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # never ask for a password
    try:
        r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _state_path(root: str) -> str | None:
    git_dir = _git(root, "rev-parse", "--absolute-git-dir")
    return os.path.join(git_dir, STATE_FILE) if git_dir else None


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(path: str, state: dict) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        pass


def main_changes(config: Config, now: float | None = None) -> list[str]:
    """Lines to show if the main branch moved since the last notice; [] otherwise."""
    root, lang, main = config.root, config.language, config.main_branch
    path = _state_path(root)
    if path is None:
        return []
    now = time.time() if now is None else now
    state = _load(path)

    if config.watch_fetch and now - state.get("last_fetch", 0) >= config.watch_every_minutes * 60:
        state["last_fetch"] = now  # also on failure: don't retry on every prompt
        _git(root, "fetch", "--quiet", "origin", main, timeout=FETCH_TIMEOUT)

    current = _git(root, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{main}")
    if not current:
        _save(path, state)
        return []
    seen = state.get("seen_main")
    state["seen_main"] = current
    _save(path, state)
    if not seen or seen == current:
        return []  # the first run only records where main is

    log = _git(root, "log", "--no-merges", "--format=%h %s", f"{seen}..{current}") or ""
    commits = log.splitlines()
    if not commits:  # main was rewritten or only merges arrived
        return [t(lang, "watch_moved", main=main)]
    lines = [t(lang, "watch_changed", main=main, n=len(commits))]
    lines += [f"  · {c}" for c in commits[:SHOWN_COMMITS]]
    if len(commits) > SHOWN_COMMITS:
        lines.append(t(lang, "watch_more", n=len(commits) - SHOWN_COMMITS))
    branch = _git(root, "branch", "--show-current")
    if branch and branch != main:
        lines.append(t(lang, "watch_merge", main=main))
    return lines


def prompt_hook_output(config: Config) -> str | None:
    lines = main_changes(config)
    if not lines:
        return None
    text = "Trazabilidad · " + "\n".join(lines)
    return json.dumps({
        "systemMessage": text,
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text},
    }, ensure_ascii=False)
