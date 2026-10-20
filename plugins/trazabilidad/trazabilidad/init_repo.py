"""
`python -m trazabilidad init`: prepares a repository in one step.

Writes a commented `.trazabilidad.toml`, the `commit-msg` hook in `.githooks/`,
pins that hook to LF endings in `.gitattributes`, and activates it for this
clone. Never overwrites a file that already exists.
"""
from __future__ import annotations

import os
import subprocess

from .config import CONFIG_FILE
from .messages import t

CONFIG_TEMPLATE = {
    "en": '''# Trazabilidad Agil Cord — https://github.com/LancelotPinajr/trazabilidad-agil-cord
language = "en"            # "en" or "es"
main_branch = "main"

[plans]
# Plan documents: one Markdown file per plan, with task tables whose first
# column is the task id:  | 2.3 | Task | Acceptance criterion | Status |
dir = "docs/plans"
file_pattern = '^(\\d+)-plan-([a-z0-9-]+)\\.md$'   # group 1: number, group 2: short name
task_id_pattern = '\\d+\\.\\d+[a-z]?'

[commits]
exempt_prefixes = ["Merge ", 'Revert "', "fixup! ", "squash! ", "amend! "]
docs_only_plans_exempt = true   # a docs: commit that only edits plans needs no id

[migrations]
dirs = []                        # e.g. ["db/migrations"]; empty turns the check off
pattern = '^(\\d+)_.+\\.sql$'

[dora]
# What counts as a deploy, for deployment frequency and lead time:
#   "merge" into the main branch (the default), "tag", or commits touching "paths"
release = "merge"
tag_pattern = '^v'
paths = []                       # e.g. ["backend"], with release = "paths"

[watch]
# "main changed" notice in Claude Code: a quick fetch at most this often
fetch = true
every_minutes = 10
''',
    "es": '''# Trazabilidad Agil Cord — https://github.com/LancelotPinajr/trazabilidad-agil-cord
language = "es"            # "en" o "es"
main_branch = "main"

[plans]
# Documentos de plan: un Markdown por plan, con tablas de tareas cuya primera
# columna es el id:  | 2.3 | Tarea | Criterio de aceptación | Estado |
dir = "docs/plans"
file_pattern = '^(\\d+)-plan-([a-z0-9-]+)\\.md$'   # grupo 1: número, grupo 2: nombre corto
task_id_pattern = '\\d+\\.\\d+[a-z]?'

[commits]
exempt_prefixes = ["Merge ", 'Revert "', "fixup! ", "squash! ", "amend! "]
docs_only_plans_exempt = true   # un commit docs: que solo edita planes no necesita id

[migrations]
dirs = []                        # p. ej. ["db/migrations"]; vacío apaga el chequeo
pattern = '^(\\d+)_.+\\.sql$'

[dora]
# Qué cuenta como un despliegue, para frecuencia de despliegue y tiempo de entrega:
#   "merge" a la rama principal (el valor por omisión), "tag", o commits que tocan "paths"
release = "merge"
tag_pattern = '^v'
paths = []                       # p. ej. ["backend"], con release = "paths"

[watch]
# aviso «cambió main» en Claude Code: un fetch rápido como mucho con esta frecuencia
fetch = true
every_minutes = 10
''',
}

HOOK = '''#!/bin/sh
# Rejects a commit that does not cite a plan task (trazabilidad-agil-cord).
# CI checks the same thing, so --no-verify only postpones the rejection.
for py in python python3; do
    if "$py" -c "import trazabilidad" >/dev/null 2>&1; then
        exec "$py" -m trazabilidad check-commits --message "$1"
    fi
done
echo "commit-msg: trazabilidad is not installed (pip install git+https://github.com/LancelotPinajr/trazabilidad-agil-cord); CI will check the task id." >&2
exit 0
'''

GITATTRIBUTES_LINE = ".githooks/* text eol=lf"


def _write_new(root: str, relative: str, content: str, lang: str, executable: bool = False) -> None:
    path = os.path.join(root, *relative.split("/"))
    if os.path.exists(path):
        print(t(lang, "init_exists", path=relative))
        return
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    if executable:
        os.chmod(path, 0o755)
    print(t(lang, "init_created", path=relative))


def init(root: str, lang: str) -> int:
    _write_new(root, CONFIG_FILE, CONFIG_TEMPLATE.get(lang, CONFIG_TEMPLATE["en"]), lang)
    _write_new(root, ".githooks/commit-msg", HOOK, lang, executable=True)

    attributes = os.path.join(root, ".gitattributes")
    existing = open(attributes, encoding="utf-8").read() if os.path.exists(attributes) else ""
    if GITATTRIBUTES_LINE not in existing:
        with open(attributes, "a", encoding="utf-8", newline="\n") as f:
            f.write(("" if not existing or existing.endswith("\n") else "\n") + GITATTRIBUTES_LINE + "\n")

    # git ignores a hook without the executable bit on Linux and macOS.
    subprocess.run(["git", "add", "--chmod=+x", ".githooks/commit-msg"], cwd=root, capture_output=True)

    current = subprocess.run(["git", "config", "core.hooksPath"], cwd=root,
                             capture_output=True, text=True).stdout.strip()
    if current and current != ".githooks":
        print(t(lang, "init_hooks_path_other", path=current))
    else:
        subprocess.run(["git", "config", "core.hooksPath", ".githooks"], cwd=root, check=True)
        print(t(lang, "init_hooks_path"))
    return 0
