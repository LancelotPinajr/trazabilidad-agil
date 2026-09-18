"""
Migrations that don't clash between branches.

1. No number repeats inside a migrations folder. Two branches that each create
   a `050` collide here, in the second pull request, not in production.
2. A migration that already reached the main branch is never edited or
   renamed. Most runners track migrations by file name: an edit never runs
   where the old one already did, and a rename runs it again.
"""
from __future__ import annotations

import re

from .config import Config
from .messages import t


def is_migration(path: str, config: Config) -> bool:
    folder, _, name = path.replace("\\", "/").rpartition("/")
    return folder in config.migration_dirs and name.endswith(".sql")


def repeated_numbers(paths: list[str], config: Config) -> list[str]:
    pattern = re.compile(config.migration_pattern)
    by_folder: dict[tuple[str, int], list[str]] = {}
    for path in paths:
        folder, _, name = path.replace("\\", "/").rpartition("/")
        m = pattern.match(name)
        if m:
            by_folder.setdefault((folder, int(m.group(1))), []).append(name)
    return [t(config.language, "migration_duplicate", dir=folder, n=f"{n:03d}", names=", ".join(sorted(names)))
            for (folder, n), names in sorted(by_folder.items()) if len(names) > 1]


def touched_migrations(changes: list[tuple[str, str]], config: Config) -> list[str]:
    """`changes` are (status, path) pairs from `git diff --name-status --no-renames`."""
    problems = []
    for status, path in changes:
        if not is_migration(path, config) or status.startswith("A"):
            continue
        key = "migration_modified" if status.startswith("M") else "migration_removed"
        problems.append(t(config.language, key, path=path))
    return problems
