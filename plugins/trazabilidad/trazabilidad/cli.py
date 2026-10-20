"""
Command line:

    python -m trazabilidad init [--lang es]
    python -m trazabilidad check-commits --message .git/COMMIT_EDITMSG   # commit-msg hook
    python -m trazabilidad check-commits --range origin/main..HEAD       # CI
    python -m trazabilidad check-migrations [--base origin/main]
    python -m trazabilidad session                                       # Claude Code SessionStart hook
    python -m trazabilidad report [--out trazabilidad-report.html] [--weeks 26]
    python -m trazabilidad plans                                         # plans, epics and next free ids (JSON)
    python -m trazabilidad watch                                         # Claude Code UserPromptSubmit hook
    python -m trazabilidad dora [--weeks 12]                             # delivery metrics (JSON)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

from . import config as config_module
from .config import CONFIG_FILE
from .commits import check_message, load_plans
from .init_repo import init
from .messages import t
from .dora import summary as dora_summary
from .plans import plans_json
from .report import write_report
from .migrations import is_migration, repeated_numbers, touched_migrations
from .session import hook_output
from .watch import prompt_hook_output


def _git(root: str, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                          text=True, encoding="utf-8").stdout


def _repo_root() -> str:
    try:
        return _git(os.getcwd(), "rev-parse", "--show-toplevel").strip()
    except (OSError, subprocess.CalledProcessError):
        return os.getcwd()


def _load_plans_or_exit(cfg):
    if not os.path.isdir(cfg.path(cfg.plans_dir)):
        print(t(cfg.language, "no_plans_dir", dir=cfg.plans_dir), file=sys.stderr)
        sys.exit(2)
    return load_plans(cfg)


def cmd_check_message(cfg, message_file: str) -> int:
    plans = _load_plans_or_exit(cfg)
    with open(message_file, encoding="utf-8") as f:
        message = f.read()
    files = _git(cfg.root, "diff", "--cached", "--name-only").split()
    problems = check_message(message, files, plans, cfg)
    if not problems:
        return 0
    print(t(cfg.language, "commit_rejected"), file=sys.stderr)
    for p in problems:
        print(f"  - {p}", file=sys.stderr)
    print(t(cfg.language, "format_help", dir=cfg.plans_dir), file=sys.stderr)
    return 1


def cmd_check_range(cfg, rng: str) -> int:
    plans = _load_plans_or_exit(cfg)
    lang = cfg.language
    bad, before, checked = [], 0, 0
    for sha in _git(cfg.root, "rev-list", "--no-merges", "--reverse", rng).split():
        # The convention applies from the commit that adopted it: the first one
        # whose tree has the config file. Dates can be set by hand; trees can't.
        exists = subprocess.run(["git", "cat-file", "-e", f"{sha}:{CONFIG_FILE}"],
                                cwd=cfg.root, capture_output=True).returncode == 0
        if not exists:
            before += 1
            continue
        checked += 1
        message = _git(cfg.root, "log", "-1", "--format=%B", sha)
        files = _git(cfg.root, "diff-tree", "--no-commit-id", "--name-only", "-r", sha).split()
        problems = check_message(message, files, plans, cfg)
        if problems:
            bad.append((sha[:7], message.splitlines()[0] if message else "", problems))
    if before:
        print(t(lang, "range_before", n=before, range=rng))
    if not bad:
        print(t(lang, "range_ok", n=checked, range=rng))
        return 0
    print(t(lang, "range_bad", bad=len(bad), n=checked, range=rng))
    for sha, subject, problems in bad:
        print(f"  {sha} {subject}")
        for p in problems:
            print(f"          - {p}")
    print(t(lang, "format_help", dir=cfg.plans_dir))
    return 1


def cmd_check_migrations(cfg, base: str | None) -> int:
    lang = cfg.language
    paths = [p for p in _git(cfg.root, "ls-files").splitlines() if is_migration(p, cfg)]
    problems = repeated_numbers(paths, cfg)
    if base:
        changes = []
        for line in _git(cfg.root, "diff", "--name-status", "--no-renames", f"{base}...HEAD").splitlines():
            status, _, path = line.partition("\t")
            changes.append((status, path))
        problems += touched_migrations(changes, cfg)
    if not problems:
        suffix = t(lang, "migrations_ok_base", base=base) if base else ""
        print(t(lang, "migrations_ok", n=len(paths), base=suffix))
        return 0
    print(t(lang, "migrations_clash"))
    for p in problems:
        print(f"  - {p}")
    return 1


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # accents stay readable on Windows too
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="trazabilidad", description="Trazabilidad Agil Cord")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init", help="prepare this repository")
    p_init.add_argument("--lang", choices=["en", "es"], default="en")
    p_commits = sub.add_parser("check-commits", help="every commit cites a plan task")
    mode = p_commits.add_mutually_exclusive_group(required=True)
    mode.add_argument("--message", help="commit message file (commit-msg hook)")
    mode.add_argument("--range", help="git range, e.g. origin/main..HEAD (CI)")
    p_migr = sub.add_parser("check-migrations", help="migrations don't clash between branches")
    p_migr.add_argument("--base", help="branch to compare with, e.g. origin/main")
    sub.add_parser("session", help="Claude Code SessionStart notice (JSON)")
    sub.add_parser("plans", help="plans, epics and next free ids, as JSON")
    sub.add_parser("watch", help="notice when the main branch changed (hook JSON)")
    p_dora = sub.add_parser("dora", help="deployment frequency and lead time, as JSON")
    p_dora.add_argument("--weeks", type=int, default=12)
    p_report = sub.add_parser("report", help="HTML report with charts, computed locally")
    p_report.add_argument("--out", default="trazabilidad-report.html")
    p_report.add_argument("--weeks", type=int, default=26)
    args = parser.parse_args(argv)

    root = _repo_root()
    if args.command == "init":
        return init(root, args.lang)
    cfg = config_module.load(root)
    if args.command == "check-commits":
        return cmd_check_message(cfg, args.message) if args.message else cmd_check_range(cfg, args.range)
    if args.command == "check-migrations":
        return cmd_check_migrations(cfg, args.base)
    if args.command == "dora":
        print(json.dumps(dora_summary(cfg, args.weeks), indent=2))
        return 0
    if args.command == "plans":
        print(plans_json(cfg))
        return 0
    if args.command == "report":
        _load_plans_or_exit(cfg)
        path, data = write_report(cfg, args.out, args.weeks)
        print(f"{path} ({len(data.tasks)} tasks, {data.commits_read} commits)")
        return 0
    try:
        output = prompt_hook_output(cfg) if args.command == "watch" else hook_output(cfg)
    except Exception:  # a notice must never keep a session from opening
        return 0
    if output:
        print(output)
    return 0
