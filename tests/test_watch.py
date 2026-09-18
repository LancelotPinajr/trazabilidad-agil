"""
«The main branch changed»: a bare remote and two clones, one pushing to main
while the other one works on its own branch.
"""
import json
import os
import subprocess
import sys

import pytest

from trazabilidad.config import Config
from trazabilidad.watch import STATE_FILE, main_changes

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins", "trazabilidad")
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout.strip()


def push_commit(clone, subject):
    with open(os.path.join(clone, "app.txt"), "a", encoding="utf-8") as f:
        f.write(subject + "\n")
    git(clone, "add", "-A")
    git(clone, "commit", "-q", "-m", subject)
    git(clone, "push", "-q", "origin", "main")


@pytest.fixture
def team(tmp_path):
    remote, alice, bob = (str(tmp_path / n) for n in ("remote.git", "alice", "bob"))
    git(str(tmp_path), "init", "-q", "--bare", "-b", "main", remote)
    git(str(tmp_path), "clone", "-q", remote, alice)
    git(alice, "checkout", "-q", "-b", "main")
    push_commit(alice, "feat: first (01/1.1)")
    git(str(tmp_path), "clone", "-q", remote, bob)
    git(bob, "checkout", "-q", "-b", "bob-branch")
    return alice, bob


def test_first_run_only_records(team):
    _, bob = team
    assert main_changes(Config(root=bob), now=1000) == []
    state = json.load(open(os.path.join(bob, ".git", STATE_FILE), encoding="utf-8"))
    assert state["seen_main"] == git(bob, "rev-parse", "origin/main")


def test_announces_new_commits_once(team):
    alice, bob = team
    cfg = Config(root=bob)
    main_changes(cfg, now=1000)
    push_commit(alice, "feat: login form (01/1.2)")
    push_commit(alice, "fix: typo (01/1.2)")

    lines = main_changes(cfg, now=1000 + 11 * 60)          # past the 10-minute throttle: it fetches
    assert lines[0] == "🔔 `main` changed: 2 new commit(s) since the last notice."
    assert any("feat: login form (01/1.2)" in line for line in lines)
    assert lines[-1].endswith("`git merge origin/main`.")  # bob is on his own branch
    assert main_changes(cfg, now=1000 + 30 * 60) == []     # already announced


def test_throttle_skips_the_fetch(team):
    alice, bob = team
    cfg = Config(root=bob)
    main_changes(cfg, now=1000)
    push_commit(alice, "feat: x (01/1.3)")
    assert main_changes(cfg, now=1000 + 60) == []          # 1 minute later: no fetch, nothing new locally
    git(bob, "fetch", "-q", "origin")                       # a manual fetch is noticed without waiting
    assert "1 new commit(s)" in main_changes(cfg, now=1000 + 120)[0]


def test_spanish_and_long_lists(team):
    alice, bob = team
    cfg = Config(root=bob, language="es")
    main_changes(cfg, now=0)
    for i in range(7):
        push_commit(alice, f"feat: paso {i} (01/1.{i})")
    lines = main_changes(cfg, now=10_000)
    assert lines[0] == "🔔 Cambió `main`: 7 commit(s) nuevo(s) desde el último aviso."
    assert "  · …y 2 más" in lines


def test_no_remote_stays_quiet(tmp_path):
    repo = str(tmp_path)
    git(repo, "init", "-q", "-b", "main")
    assert main_changes(Config(root=repo), now=0) == []


def test_unreachable_remote_does_not_hang(team):
    _, bob = team
    git(bob, "remote", "set-url", "origin", os.path.join(bob, "does-not-exist.git"))
    assert main_changes(Config(root=bob), now=0) == []


def test_fetch_can_be_turned_off(team):
    alice, bob = team
    cfg = Config(root=bob, watch_fetch=False)
    main_changes(cfg, now=0)
    push_commit(alice, "feat: y (01/1.4)")
    assert main_changes(cfg, now=10_000) == []


def test_prompt_hook_json(team):
    alice, bob = team
    run = [sys.executable, os.path.join(PLUGIN, "hooks", "run.py"), "watch"]
    first = subprocess.run(run, cwd=bob, capture_output=True, text=True, encoding="utf-8")
    assert first.returncode == 0 and first.stdout == ""     # nothing to say the first time
    push_commit(alice, "feat: z (01/1.5)")
    git(bob, "fetch", "-q", "origin")
    out = subprocess.run(run, cwd=bob, capture_output=True, text=True, encoding="utf-8")
    data = json.loads(out.stdout)
    assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "feat: z (01/1.5)" in data["systemMessage"]
