"""
The whole flow on a throwaway git repository: init, commit through the hook,
check a range and check migrations. Runs the real `git`.
"""
import json
import os
import subprocess
import sys

import pytest

PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins", "trazabilidad-agil")


def run(repo, *args, check=True):
    env = {**os.environ, "PYTHONPATH": PLUGIN, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    return subprocess.run(list(args), cwd=repo, env=env, capture_output=True, text=True,
                          encoding="utf-8", check=check)


def tz(repo, *args, check=False):
    return run(repo, sys.executable, "-m", "trazabilidad", *args, check=check)


def commit(repo, message, path="src/app.py", content=None, *flags):
    full = os.path.join(repo, *path.split("/"))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "a", encoding="utf-8") as f:
        f.write(content or message + "\n")
    run(repo, "git", "add", "-A")
    return run(repo, "git", "commit", "-q", *flags, "-m", message, check=False)


@pytest.fixture
def repo(tmp_path):
    repo = str(tmp_path)
    run(repo, "git", "init", "-q", "-b", "main")
    run(repo, "git", "config", "core.autocrlf", "false")
    commit(repo, "initial commit, before the convention")
    run(repo, "git", "branch", "base")
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "01-plan-login.md").write_text(
        "| # | Task | Criterion | Status |\n|---|---|---|---|\n| 1.1 | Login | Works | todo |\n",
        encoding="utf-8")
    return repo


def test_full_flow(repo):
    out = tz(repo, "init", "--lang", "en")
    assert out.returncode == 0, out.stderr
    assert os.path.exists(os.path.join(repo, ".trazabilidad.toml"))
    assert run(repo, "git", "config", "core.hooksPath").stdout.strip() == ".githooks"

    # Adopting the convention: plans and config enter in a commit that cites a task.
    assert commit(repo, "chore: adopt traceability (01/1.1)", ".keep").returncode == 0

    rejected = commit(repo, "feat: no id")
    assert rejected.returncode != 0
    assert "does not cite any task" in rejected.stderr
    run(repo, "git", "reset", "-q", "--hard")

    # --no-verify skips the hook, not the range check.
    assert commit(repo, "feat: sneaked in", "src/app.py", None, "--no-verify").returncode == 0
    assert commit(repo, "feat: login form (01/1.1)").returncode == 0

    result = tz(repo, "check-commits", "--range", "base..HEAD")
    assert result.returncode == 1
    assert "feat: sneaked in" in result.stdout
    assert "1 of 3 commit(s)" in result.stdout


def test_commits_before_the_config_are_not_checked(repo):
    commit(repo, "feat: old work without id")
    tz(repo, "init")
    commit(repo, "chore: adopt (01/1.1)", ".keep")
    result = tz(repo, "check-commits", "--range", "base..HEAD")
    assert result.returncode == 0, result.stdout
    assert "predate the convention" in result.stdout


def test_migrations_clash(repo):
    tz(repo, "init")
    config = os.path.join(repo, ".trazabilidad.toml")
    text = open(config, encoding="utf-8").read().replace("dirs = []", 'dirs = ["db/migrations"]')
    open(config, "w", encoding="utf-8").write(text)
    commit(repo, "feat: first migration (01/1.1)", "db/migrations/001_users.sql", "create table users();\n")
    run(repo, "git", "branch", "before-edit")
    assert tz(repo, "check-migrations").returncode == 0

    commit(repo, "feat: same number (01/1.1)", "db/migrations/001_roles.sql", "create table roles();\n")
    clash = tz(repo, "check-migrations")
    assert clash.returncode == 1 and "number 001 is used by 001_roles.sql, 001_users.sql" in clash.stdout

    edited = tz(repo, "check-migrations", "--base", "before-edit")
    assert "001_roles.sql" in edited.stdout

    commit(repo, "fix: edit an applied one (01/1.1)", "db/migrations/001_users.sql", "alter table users;\n")
    edited = tz(repo, "check-migrations", "--base", "before-edit")
    assert "db/migrations/001_users.sql: edited" in edited.stdout


def test_session_notice(repo):
    out = tz(repo, "session")
    data = json.loads(out.stdout)
    assert "`main`" in data["systemMessage"]              # working on main is flagged
    assert ".trazabilidad.toml" in data["systemMessage"]  # and the missing config
    run(repo, "git", "switch", "-q", "-c", "feature")
    tz(repo, "init", "--lang", "es")
    data = json.loads(tz(repo, "session").stdout)
    assert "Rama: `feature`" in data["systemMessage"]


def test_session_hook_runs_without_install(repo):
    # The plugin hook imports the package that ships inside the plugin.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    out = subprocess.run([sys.executable, os.path.join(PLUGIN, "hooks", "run.py"), "session"],
                         cwd=repo, env=env, capture_output=True, text=True, encoding="utf-8")
    assert out.returncode == 0
    assert json.loads(out.stdout)["hookSpecificOutput"]["hookEventName"] == "SessionStart"
