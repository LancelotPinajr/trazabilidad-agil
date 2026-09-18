"""
The HTML report: statuses read from the plans, cycle time from git history,
and a page that loads nothing from the internet.
"""
import datetime as dt
import os
import re
import subprocess

import pytest

from trazabilidad.config import Config
from trazabilidad.report import collect, cycle_days, parse_plan, percentile, render, status_of

HEAD = "| # | Task | Criterion | Status |\n|---|---|---|---|\n"


@pytest.mark.parametrize("cells, expected", [
    (["Login", "Works", "✅"], "done"),
    (["Login", "Works", "🟡 missing the test"], "in_progress"),
    (["Login", "Works", "⛔ waiting for a token"], "blocked"),
    (["Login", "Works", "⬜"], "todo"),
    (["Login", "Works", "hecha"], "done"),
    (["Login", "Works", "en curso"], "in_progress"),
    (["Login", "⬜ **deferred**", "Only table without a status column"], "todo"),
    (["Login", "Done when the user signs in", "⬜"], "todo"),        # words in the criterion don't count
    (["Login", "Done when the user signs in", "pending review"], "todo"),
])
def test_status_of(cells, expected):
    assert status_of(cells) == expected


def test_parse_plan_reads_epics_and_skips_other_tables():
    text = ("## Decisions\n| # | Decision | Status |\n|---|---|---|\n| L1 | Lock | ✅ |\n"
            "### Epic 1 — Sign in\n" + HEAD + "| 1.1 | **Form** | Works | ✅ |\n| 1.2 | `Remember` | 30 d | 🟡 |\n"
            "### Epic 2 — Protection\n" + HEAD + "| 2.3b | Unlock | Link | ⬜ |\n")
    rows = parse_plan(text, Config(root="."))
    assert rows == [("1.1", "Form", "Epic 1 — Sign in", "done"),
                    ("1.2", "Remember", "Epic 1 — Sign in", "in_progress"),
                    ("2.3b", "Unlock", "Epic 2 — Protection", "todo")]


def test_percentile():
    assert percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9) == pytest.approx(9.1)
    assert percentile([4], 0.9) == 4


def _git(repo, *args, date=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def _plan(repo, statuses):
    rows = "".join(f"| {tid} | Task {tid} | Criterion | {s} |\n" for tid, s in statuses.items())
    path = os.path.join(repo, "docs", "plans", "01-plan-login.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("### Epic 1\n" + HEAD + rows)


@pytest.fixture
def repo(tmp_path):
    repo = str(tmp_path)
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "core.autocrlf", "false")
    _plan(repo, {"1.1": "⬜", "1.2": "⬜", "2.1": "⬜"})
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs(plan): plan 01", date="2026-09-01T10:00:00+00:00")

    (tmp_path / "app.py").write_text("a\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: form (01/1.1)", date="2026-09-02T10:00:00+00:00")
    (tmp_path / "app.py").write_text("b\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feat: remember (01/1.2)", date="2026-09-03T10:00:00+00:00")
    (tmp_path / "app.py").write_text("c\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "chore: no id", date="2026-09-03T12:00:00+00:00")

    _plan(repo, {"1.1": "✅", "1.2": "🟡", "2.1": "⬜"})
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs(plan): 1.1 done", date="2026-09-06T10:00:00+00:00")
    return repo


def test_collect_cycle_time_and_weeks(repo):
    data = collect(Config(root=repo), weeks=4, today=dt.date(2026, 9, 10))
    tasks = {t.task_id: t for t in data.tasks}
    assert [t.status for t in data.tasks] == ["done", "in_progress", "todo"]
    assert cycle_days(tasks["1.1"]) == pytest.approx(4.0)       # 02-sep → 06-sep
    assert cycle_days(tasks["1.2"]) is None                      # not done
    assert tasks["2.1"].first_cited is None
    assert data.commits_read == 5
    by_week = {monday.isoformat(): (w, wo) for monday, w, wo in data.weeks}
    assert by_week["2026-08-31"] == (2, 3)                       # the 3 commits without id include 2 plan docs
    assert by_week["2026-09-07"] == (0, 0)


def test_a_task_reopened_loses_its_done_date(repo):
    _plan(repo, {"1.1": "🟡", "1.2": "🟡", "2.1": "⬜"})
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "docs(plan): reopen 1.1", date="2026-09-07T10:00:00+00:00")
    tasks = {t.task_id: t for t in collect(Config(root=repo), weeks=4, today=dt.date(2026, 9, 10)).tasks}
    assert tasks["1.1"].done_at is None and cycle_days(tasks["1.1"]) is None


def test_render_is_self_contained_and_escapes(repo):
    plan = os.path.join(repo, "docs", "plans", "01-plan-login.md")
    with open(plan, "a", encoding="utf-8") as f:
        f.write("| 3.1 | <script>alert(1)</script> | x | 🟡 |\n")
    config = Config(root=repo, language="es")
    page = render(collect(config, weeks=4, today=dt.date(2026, 9, 10)), config, 4,
                  now=dt.datetime(2026, 9, 10, tzinfo=dt.timezone.utc))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    # Nothing is fetched from anywhere: no src/href to a URL, no @import.
    assert not re.search(r'(src|href)\s*=\s*["\']?(https?:)?//', page)
    assert "@import" not in page
    assert "Tareas por plan" in page and "Tiempo de ciclo por plan" in page
    assert "n=1" in page                                          # every cycle-time figure shows its n
