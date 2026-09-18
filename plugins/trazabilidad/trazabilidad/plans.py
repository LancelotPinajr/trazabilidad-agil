"""
`python -m trazabilidad plans`: the plans, their epics and the next free ids, as JSON.

It is what `/trazabilidad:add-to-plan` reads before proposing new rows, so the ids come
from the files and are never guessed: the next task of an epic, the next epic
of a plan, and the next plan number.
"""
from __future__ import annotations

import json
import os
import re

from .config import Config
from .report import parse_plan

_NUMERIC_ID = re.compile(r"^(\d+)\.(\d+)[a-z]?$")


def _next_task(ids: list[str]) -> str | None:
    """`2.4` after `2.1, 2.3, 2.3b`; None when the ids are not `major.minor`."""
    pairs = [(int(m.group(1)), int(m.group(2))) for i in ids if (m := _NUMERIC_ID.match(i))]
    if not pairs:
        return None
    major = max(p[0] for p in pairs)  # a table can mix epics; the last one leads
    return f"{major}.{max(p[1] for p in pairs if p[0] == major) + 1}"


def describe(config: Config) -> dict:
    folder = config.path(config.plans_dir)
    file_re = re.compile(config.plan_file_pattern)
    plans, numbers = [], []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        fm = file_re.match(name)
        if not fm:
            continue
        number, short = fm.group(1), fm.group(2)
        numbers.append(number)
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            text = f.read()
        title = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), "")
        epics: dict[str, list] = {}
        for task_id, task_title, epic, status in parse_plan(text, config):
            epics.setdefault(epic, []).append({"id": task_id, "title": task_title, "status": status})
        majors = [int(im.group(1)) for e in epics.values() for t in e if (im := _NUMERIC_ID.match(t["id"]))]
        plans.append({
            "key": f"{number}-{short}",
            "file": f"{config.plans_dir}/{name}",
            "title": title,
            "epics": [{"heading": h, "tasks": ts, "next_task_id": _next_task([t["id"] for t in ts])}
                      for h, ts in epics.items()],
            "next_epic_number": (max(majors) + 1) if majors else 1,
        })
    # Numbers shared by two plans are cited by name, which needs every plan read first.
    for plan in plans:
        number = plan["key"].split("-", 1)[0]
        plan["cite_as"] = number if numbers.count(number) == 1 else plan["key"]
    width = max((len(n) for n in numbers), default=2)
    next_number = (max((int(n) for n in numbers), default=0) + 1)
    return {
        "plans_dir": config.plans_dir,
        "language": config.language,
        "next_plan_number": str(next_number).zfill(width),
        "plans": plans,
    }


def plans_json(config: Config) -> str:
    return json.dumps(describe(config), ensure_ascii=False, indent=2)
