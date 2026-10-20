"""
Per-repository configuration: `.trazabilidad.toml` at the repo root.

Everything has a default, so a repo without the file still gets the branch
warning. The commit check needs the plans directory to exist.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field

CONFIG_FILE = ".trazabilidad.toml"


@dataclass
class Config:
    root: str
    found: bool = False
    language: str = "en"
    main_branch: str = "main"
    plans_dir: str = "docs/plans"
    # Group 1: plan number. Group 2: short name. «07-plan-login.md» -> ("07", "login").
    plan_file_pattern: str = r"^(\d+)-plan-([a-z0-9-]+)\.md$"
    # A task id as it appears in the first column of a plan's task tables.
    task_id_pattern: str = r"\d+\.\d+[a-z]?"
    exempt_prefixes: list[str] = field(default_factory=lambda: [
        "Merge ", 'Revert "', "fixup! ", "squash! ", "amend! "])
    # A `docs:` commit that only touches plan files needs no id: writing a plan
    # is not a task of that plan.
    docs_only_plans_exempt: bool = True
    migration_dirs: list[str] = field(default_factory=list)
    migration_pattern: str = r"^(\d+)_.+\.sql$"
    # What counts as a deploy: "merge" into the main branch, "tag", or commits
    # touching "paths". Deployment frequency and lead time are read from it.
    dora_release: str = "merge"
    dora_tag_pattern: str = r"^v"
    dora_paths: list[str] = field(default_factory=list)
    # «The main branch changed» notice: fetch at most this often, never on every prompt.
    watch_fetch: bool = True
    watch_every_minutes: int = 10

    def path(self, relative: str) -> str:
        return os.path.join(self.root, *relative.split("/"))


def load(root: str) -> Config:
    config = Config(root=root)
    path = os.path.join(root, CONFIG_FILE)
    if not os.path.exists(path):
        return config
    with open(path, "rb") as f:
        data = tomllib.load(f)
    config.found = True
    config.language = data.get("language", config.language)
    config.main_branch = data.get("main_branch", config.main_branch)
    plans = data.get("plans", {})
    config.plans_dir = plans.get("dir", config.plans_dir).rstrip("/")
    config.plan_file_pattern = plans.get("file_pattern", config.plan_file_pattern)
    config.task_id_pattern = plans.get("task_id_pattern", config.task_id_pattern)
    commits = data.get("commits", {})
    config.exempt_prefixes = commits.get("exempt_prefixes", config.exempt_prefixes)
    config.docs_only_plans_exempt = commits.get("docs_only_plans_exempt", config.docs_only_plans_exempt)
    migrations = data.get("migrations", {})
    config.migration_dirs = [d.rstrip("/") for d in migrations.get("dirs", config.migration_dirs)]
    config.migration_pattern = migrations.get("pattern", config.migration_pattern)
    dora = data.get("dora", {})
    config.dora_release = dora.get("release", config.dora_release)
    config.dora_tag_pattern = dora.get("tag_pattern", config.dora_tag_pattern)
    config.dora_paths = [p.rstrip("/") for p in dora.get("paths", config.dora_paths)]
    watch = data.get("watch", {})
    config.watch_fetch = watch.get("fetch", config.watch_fetch)
    config.watch_every_minutes = watch.get("every_minutes", config.watch_every_minutes)
    return config
