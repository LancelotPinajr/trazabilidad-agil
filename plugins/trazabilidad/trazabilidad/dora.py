"""
Delivery metrics from git alone: deployment frequency and lead time for change.

What counts as a deploy differs per repository, so `[dora] release` picks it:

    "merge"  every merge into the main branch (the default)
    "tag"    every tag matching `tag_pattern`
    "paths"  every commit on the main branch touching one of `paths`

The other two DORA metrics — change failure rate and time to restore — need
incidents to be recorded, which git does not know about. They are not computed
here and never guessed.

Everything is read from the local repository; nothing is sent anywhere.
"""
from __future__ import annotations

import datetime as dt
import fnmatch
import re
import statistics
import subprocess
from dataclasses import dataclass, field

from .config import Config

UNIT = "\x1f"
RECORD = "\x1e"


@dataclass
class Deploy:
    """One deploy: when it landed, and when each change it carried was committed."""
    sha: str
    when: dt.datetime
    changes: list[dt.datetime] = field(default_factory=list)


@dataclass
class Delivery:
    release_kind: str
    main_ref: str
    weeks: int
    deploys: list[Deploy] = field(default_factory=list)
    reason: str | None = None          # why there is nothing to report
    now: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.timezone.utc))

    def per_week(self) -> list[tuple[dt.date, int]]:
        """Deploys per week, oldest first, including the weeks with none."""
        last = _monday(self.now.date())
        weeks = [last - dt.timedelta(weeks=i) for i in range(self.weeks - 1, -1, -1)]
        counts = dict.fromkeys(weeks, 0)
        for deploy in self.deploys:
            week = _monday(deploy.when.date())
            if week in counts:
                counts[week] += 1
        return [(w, counts[w]) for w in weeks]

    def median_gap_days(self) -> float | None:
        """Median days from one deploy to the next."""
        times = sorted(d.when for d in self.deploys)
        gaps = [(b - a).total_seconds() / 86400 for a, b in zip(times, times[1:])]
        return round(statistics.median(gaps), 2) if gaps else None

    def lead_times_days(self) -> list[float]:
        """One number per change: from its commit to the deploy that carried it."""
        return sorted(
            (deploy.when - when).total_seconds() / 86400
            for deploy in self.deploys for when in deploy.changes
            if deploy.when >= when
        )


def _monday(day: dt.date) -> dt.date:
    return day - dt.timedelta(days=day.weekday())


def _git(root: str, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                       encoding="utf-8")
    return r.stdout if r.returncode == 0 else ""


def _when(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.strip())


def main_ref(config: Config) -> str | None:
    """`origin/main` when it exists, else the local branch, else nothing."""
    for ref in (f"origin/{config.main_branch}", config.main_branch):
        if _git(config.root, "rev-parse", "--verify", "--quiet", ref).strip():
            return ref
    return None


def _commits_in(root: str, *revs: str) -> list[dt.datetime]:
    log = _git(root, "log", "--no-merges", "--format=%cI", *revs)
    return sorted(_when(line) for line in log.splitlines() if line.strip())


def _merge_deploys(config: Config, ref: str) -> list[Deploy]:
    """Each merge into the main branch, carrying what its side brought in."""
    deploys = []
    log = _git(config.root, "log", "--first-parent", ref, "--merges",
               f"--format=%H{UNIT}%cI{UNIT}%P")
    for line in log.splitlines():
        if not line.strip():
            continue
        sha, when, parents = line.split(UNIT)
        sides = parents.split()
        changes = _commits_in(config.root, sides[1], f"^{sides[0]}") if len(sides) > 1 else []
        deploys.append(Deploy(sha, _when(when), changes))
    return deploys


def _tag_marks(config: Config) -> list[tuple[str, dt.datetime]]:
    marks = []
    log = _git(config.root, "for-each-ref", "refs/tags",
               f"--format=%(refname:short){UNIT}%(creatordate:iso-strict){UNIT}%(objectname)")
    for line in log.splitlines():
        if not line.strip():
            continue
        name, when, sha = line.split(UNIT)
        if re.search(config.dora_tag_pattern, name):
            marks.append((sha, _when(when)))
    return sorted(marks, key=lambda m: m[1])


def _path_marks(config: Config, ref: str) -> list[tuple[str, dt.datetime]]:
    """Commits on the main branch that touch one of the configured paths."""
    marks = []
    log = _git(config.root, "log", "--first-parent", ref, "--name-only",
               f"--format={RECORD}%H{UNIT}%cI")
    for block in log.split(RECORD):
        head, _, body = block.partition("\n")
        if UNIT not in head:
            continue
        sha, _, when = head.partition(UNIT)
        files = [f for f in body.splitlines() if f.strip()]
        if any(_matches(f, p) for f in files for p in config.dora_paths):
            marks.append((sha, _when(when)))
    marks.reverse()  # git log is newest first
    return marks


def _matches(path: str, pattern: str) -> bool:
    """`backend/**` and `backend/` both cover `backend/app/main.py`."""
    prefix = pattern.rstrip("*").rstrip("/")
    return fnmatch.fnmatch(path, pattern) or (bool(prefix) and path.startswith(prefix + "/"))


def _linear_deploys(marks: list[tuple[str, dt.datetime]], config: Config) -> list[Deploy]:
    """Tags or path commits: each deploy carries what landed since the previous one."""
    deploys = []
    previous = None
    for sha, when in marks:
        revs = (sha,) if previous is None else (sha, f"^{previous}")
        deploys.append(Deploy(sha, when, _commits_in(config.root, *revs)))
        previous = sha
    return deploys


def collect(config: Config, weeks: int = 12, now: dt.datetime | None = None) -> Delivery:
    """Deploys of the last `weeks` weeks, each with the changes it carried."""
    now = now or dt.datetime.now(dt.timezone.utc)
    kind = config.dora_release
    ref = main_ref(config)
    delivery = Delivery(kind, ref or config.main_branch, weeks, now=now)
    if ref is None:
        delivery.reason = f"this repository has no branch {config.main_branch}"
        return delivery

    if kind == "merge":
        found = _merge_deploys(config, ref)
        empty = (f"no merges into {ref}: this repository commits straight to the main "
                 f'branch, so set [dora] release to "tag" or "paths"')
    elif kind == "tag":
        found = _linear_deploys(_tag_marks(config), config)
        empty = f"no tags matching {config.dora_tag_pattern}"
    elif kind == "paths":
        if not config.dora_paths:
            delivery.reason = '[dora] release = "paths" needs [dora] paths'
            return delivery
        found = _linear_deploys(_path_marks(config, ref), config)
        empty = f"no commits on {ref} touching {', '.join(config.dora_paths)}"
    else:
        delivery.reason = f'[dora] release = "{kind}" is not merge, tag or paths'
        return delivery

    if not found:
        delivery.reason = empty
        return delivery

    cutoff = now - dt.timedelta(weeks=weeks)
    delivery.deploys = sorted((d for d in found if d.when >= cutoff), key=lambda d: d.when)
    if not delivery.deploys:
        delivery.reason = f"no deploys in the last {weeks} weeks"
    return delivery


def summary(config: Config, weeks: int = 12, now: dt.datetime | None = None) -> dict:
    """What the report and the panel show. A value is None when there isn't enough."""
    delivery = collect(config, weeks, now)
    lead = delivery.lead_times_days()
    enough = len(lead) >= 3            # same floor as the cycle time chart
    return {
        "release_kind": delivery.release_kind,
        "main_ref": delivery.main_ref,
        "weeks": weeks,
        "reason": delivery.reason,
        "deployment_frequency": {
            "total": len(delivery.deploys),
            "per_week": [{"week": w.isoformat(), "deploys": n} for w, n in delivery.per_week()],
            "median_gap_days": delivery.median_gap_days(),
        },
        "lead_time_days": {
            "n": len(lead),
            "median": round(statistics.median(lead), 2) if lead else None,
            "p90": round(percentile(lead, 0.9), 2) if enough else None,
            "enough": enough,
        },
    }


def percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p
    low = int(k)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (k - low)
