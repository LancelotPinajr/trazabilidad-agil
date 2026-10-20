"""
Delivery metrics: what counts as a deploy, how often they land, and how long a
change waits for one. Read from a real git repository built in a temp folder.
"""
import datetime as dt
import os
import subprocess

import pytest

from trazabilidad.config import Config
from trazabilidad.dora import collect, percentile, summary

NOW = dt.datetime(2026, 10, 20, 12, 0, tzinfo=dt.timezone.utc)


def _git(repo, *args, date=None):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def _commit(repo, name, date, content="x"):
    with open(os.path.join(repo, name), "w", encoding="utf-8") as f:
        f.write(content)
    _git(repo, "add", "-A", date=date)
    _git(repo, "commit", "-q", "-m", f"work on {name}", date=date)


def _day(n: int) -> str:
    """ISO time n days before NOW."""
    return (NOW - dt.timedelta(days=n)).isoformat()


@pytest.fixture
def repo(tmp_path):
    """main with two merged branches: one change merged the same day, one after 5 days."""
    repo = str(tmp_path)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "core.autocrlf", "false")
    _commit(repo, "readme.md", _day(40))

    _git(repo, "switch", "-q", "-c", "one", date=_day(30))
    _commit(repo, "a.txt", _day(30))
    _git(repo, "switch", "-q", "main", date=_day(30))
    _git(repo, "merge", "-q", "--no-ff", "one", "-m", "Merge branch 'one'", date=_day(30))

    _git(repo, "switch", "-q", "-c", "two", date=_day(15))
    _commit(repo, "b.txt", _day(15))
    _commit(repo, "c.txt", _day(12))
    _git(repo, "switch", "-q", "main", date=_day(10))
    _git(repo, "merge", "-q", "--no-ff", "two", "-m", "Merge branch 'two'", date=_day(10))
    return repo


def cfg(repo, **kw):
    return Config(root=repo, found=True, **kw)


def test_merges_are_the_deploys(repo):
    delivery = collect(cfg(repo), weeks=8, now=NOW)
    assert delivery.reason is None
    assert len(delivery.deploys) == 2
    # The second merge carried two commits; the first, one.
    assert sorted(len(d.changes) for d in delivery.deploys) == [1, 2]


def test_deployment_frequency_counts_each_week(repo):
    freq = summary(cfg(repo), weeks=8, now=NOW)["deployment_frequency"]
    assert freq["total"] == 2
    weeks = {w["week"]: w["deploys"] for w in freq["per_week"]}
    assert len(weeks) == 8                       # empty weeks are listed too
    assert sum(weeks.values()) == 2
    assert weeks["2026-09-14"] == 1              # the merge 30 days before NOW
    assert weeks["2026-10-05"] == 1              # the merge 10 days before NOW
    assert freq["median_gap_days"] == pytest.approx(20, abs=0.1)


def test_weeks_window_is_respected(repo):
    assert summary(cfg(repo), weeks=2, now=NOW)["deployment_frequency"]["total"] == 1


def test_lead_time_is_first_commit_to_its_deploy(repo):
    lead = summary(cfg(repo), weeks=8, now=NOW)["lead_time_days"]
    assert lead["n"] == 3                        # three changes across two deploys
    assert lead["median"] == pytest.approx(2, abs=0.1)     # c.txt waited 2 days
    assert lead["enough"] is True


def test_under_three_changes_says_so(repo):
    lead = summary(cfg(repo), weeks=3, now=NOW)["lead_time_days"]
    assert lead["n"] == 2 and lead["enough"] is False and lead["p90"] is None


def test_a_repo_without_merges_says_what_to_configure(tmp_path):
    repo = str(tmp_path)
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "a.txt", _day(3))
    delivery = collect(cfg(repo), weeks=8, now=NOW)
    assert delivery.deploys == []
    assert "commits straight to the main branch" in delivery.reason


def test_tags_as_deploys(tmp_path):
    repo = str(tmp_path)
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "a.txt", _day(20))
    _git(repo, "tag", "-a", "v1.0", "-m", "v1.0", date=_day(18))
    _commit(repo, "b.txt", _day(9))
    _git(repo, "tag", "-a", "v1.1", "-m", "v1.1", date=_day(8))
    _commit(repo, "c.txt", _day(2))              # after the last tag: not deployed yet
    data = summary(cfg(repo, dora_release="tag"), weeks=8, now=NOW)
    assert data["deployment_frequency"]["total"] == 2
    assert data["lead_time_days"]["n"] == 2      # c.txt has no deploy to wait for
    assert data["reason"] is None


def test_paths_as_deploys(tmp_path):
    repo = str(tmp_path)
    _git(repo, "init", "-q", "-b", "main")
    os.makedirs(os.path.join(repo, "backend"))
    _commit(repo, "docs.md", _day(12))                       # no deploy: wrong path
    _commit(repo, os.path.join("backend", "main.py"), _day(6))
    data = summary(cfg(repo, dora_release="paths", dora_paths=["backend"]), weeks=8, now=NOW)
    assert data["deployment_frequency"]["total"] == 1
    assert data["lead_time_days"]["n"] == 2                  # both commits rode that deploy


def test_paths_without_paths_configured_is_said(tmp_path):
    repo = str(tmp_path)
    _git(repo, "init", "-q", "-b", "main")
    _commit(repo, "a.txt", _day(2))
    assert "needs [dora] paths" in collect(cfg(repo, dora_release="paths"), now=NOW).reason


def test_percentile_matches_the_report():
    assert percentile([1.0, 2.0, 3.0], 0.9) == pytest.approx(2.8)
    assert percentile([], 0.9) == 0.0
