"""
Every commit cites the plan task that motivated it: `type(scope): subject (12/2.3)`.

The id carries the plan because task numbers repeat across plans (`1.1` is in
every plan). When two plan files share a number, they are cited by their short
name: `12-login/2.3`. Any plan also accepts the long form. The task has to
exist in the plan's task tables: an invented id does not pass.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from .config import Config
from .messages import t


@dataclass
class Plans:
    tasks: dict[str, set[str]] = field(default_factory=dict)      # "12-login" -> {"1.1", …}
    alias: dict[str, str] = field(default_factory=dict)           # "12" -> "12-login"
    ambiguous: dict[str, list[str]] = field(default_factory=dict)  # "16" -> ["16-a", "16-b"]

    def resolve(self, key: str) -> str | None:
        return key if key in self.tasks else self.alias.get(key)


def load_plans(config: Config) -> Plans:
    plans = Plans()
    folder = config.path(config.plans_dir)
    file_re = re.compile(config.plan_file_pattern)
    row_re = re.compile(rf"^\|\s*({config.task_id_pattern})\s*\|", re.MULTILINE)
    by_number: dict[str, list[str]] = {}
    for name in sorted(os.listdir(folder)):
        m = file_re.match(name)
        if not m:
            continue
        number, short = m.group(1), m.group(2)
        key = f"{number}-{short}"
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            plans.tasks[key] = set(row_re.findall(f.read()))
        by_number.setdefault(number, []).append(key)
    for number, keys in by_number.items():
        if len(keys) == 1:
            plans.alias[number] = keys[0]
        else:
            plans.ambiguous[number] = keys
    return plans


def _id_regex(config: Config) -> re.Pattern:
    return re.compile(rf"(?<![\w/.-])(\d+(?:-[a-z0-9-]+)?)/({config.task_id_pattern})(?!\w|\.\d)")


def is_plan(path: str, config: Config) -> bool:
    folder, _, name = path.replace("\\", "/").rpartition("/")
    return folder == config.plans_dir and bool(re.match(config.plan_file_pattern, name))


def check_message(message: str, files: list[str], plans: Plans, config: Config) -> list[str]:
    """The problems with a commit message; an empty list if it complies."""
    lang = config.language
    lines = [line for line in message.splitlines() if not line.startswith("#")]
    subject = next((line for line in lines if line.strip()), "")
    if not subject:
        return []  # git itself aborts an empty message
    if any(subject.startswith(p) for p in config.exempt_prefixes):
        return []
    if (config.docs_only_plans_exempt and re.match(r"^docs(\([^)]*\))?!?:", subject)
            and files and all(is_plan(f, config) for f in files)):
        return []

    citations = _id_regex(config).findall("\n".join(lines))
    if not citations:
        return [t(lang, "no_citation")]

    problems = []
    for key, task in citations:
        if key in plans.ambiguous:
            options = ", ".join(f"{k}/{task}" for k in plans.ambiguous[key])
            problems.append(t(lang, "ambiguous_plan", key=key, task=task, options=options))
            continue
        plan = plans.resolve(key)
        if plan is None:
            problems.append(t(lang, "unknown_plan", key=key, task=task, dir=config.plans_dir))
        elif task not in plans.tasks[plan]:
            problems.append(t(lang, "unknown_task", key=key, task=task, plan=plan))
    return problems
