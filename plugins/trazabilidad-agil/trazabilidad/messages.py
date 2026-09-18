"""Every message the tool prints, in English and Spanish (`language` in the config)."""
from __future__ import annotations

MESSAGES = {
    "no_citation": {
        "en": "does not cite any task",
        "es": "no cita ninguna tarea",
    },
    "ambiguous_plan": {
        "en": "{key}/{task}: there are several plans {key}; use {options}",
        "es": "{key}/{task}: hay varios planes {key}; usa {options}",
    },
    "unknown_plan": {
        "en": "{key}/{task}: there is no plan {key} in {dir}",
        "es": "{key}/{task}: no hay un plan {key} en {dir}",
    },
    "unknown_task": {
        "en": "{key}/{task}: plan {plan} has no task {task}",
        "es": "{key}/{task}: el plan {plan} no tiene la tarea {task}",
    },
    "commit_rejected": {
        "en": "Commit rejected: the message does not cite a valid task.",
        "es": "Commit rechazado: el mensaje no cita una tarea válida.",
    },
    "format_help": {
        "en": ("  Format:    type(scope): subject (12/2.3)\n"
               "  Several:   type(scope): subject (12/2.3, 12/2.4)\n"
               "  Plan ids come from the task tables in {dir}.\n"
               "  Plans that share a number are cited by name: 12-login/2.3"),
        "es": ("  Formato:   tipo(ámbito): asunto (12/2.3)\n"
               "  Varios:    tipo(ámbito): asunto (12/2.3, 12/2.4)\n"
               "  Los ids salen de las tablas de tareas de {dir}.\n"
               "  Los planes que comparten número se citan por nombre: 12-login/2.3"),
    },
    "range_before": {
        "en": "{n} commit(s) in {range} predate the convention and are not checked.",
        "es": "{n} commit(s) de {range} son anteriores a la convención y no se revisan.",
    },
    "range_ok": {
        "en": "OK: the {n} checked commit(s) in {range} cite a valid task.",
        "es": "OK: los {n} commit(s) revisados de {range} citan una tarea válida.",
    },
    "range_bad": {
        "en": "{bad} of {n} commit(s) in {range} do not cite a valid task:",
        "es": "{bad} de {n} commit(s) de {range} no citan una tarea válida:",
    },
    "no_plans_dir": {
        "en": "There is no plans directory {dir}. Set plans.dir in .trazabilidad.toml.",
        "es": "No existe la carpeta de planes {dir}. Ajusta plans.dir en .trazabilidad.toml.",
    },
    "migration_duplicate": {
        "en": "{dir}: number {n} is used by {names}",
        "es": "{dir}: el número {n} lo usan {names}",
    },
    "migration_modified": {
        "en": "{path}: edited; write a new migration instead",
        "es": "{path}: se editó; lo que haga falta va en una migración nueva",
    },
    "migration_removed": {
        "en": "{path}: deleted or renamed; write a new migration instead",
        "es": "{path}: se borró o se renombró; lo que haga falta va en una migración nueva",
    },
    "migrations_ok": {
        "en": "OK: {n} migrations, no repeated numbers{base}.",
        "es": "OK: {n} migraciones, sin números repetidos{base}.",
    },
    "migrations_ok_base": {
        "en": " and none from {base} touched",
        "es": " ni migraciones de {base} tocadas",
    },
    "migrations_clash": {
        "en": "Migrations clash:",
        "es": "Las migraciones chocan:",
    },
    "session_on_main": {
        "en": "⚠️ This folder is on `{main}`. Don't work here: switch to your own branch.",
        "es": "⚠️ La carpeta está en `{main}`. Aquí no se trabaja: cambia a tu rama.",
    },
    "session_detached": {
        "en": "⚠️ This folder is not on any branch (detached HEAD).",
        "es": "⚠️ La carpeta no está en ninguna rama (HEAD suelto).",
    },
    "session_branch": {
        "en": "Branch: `{branch}`.",
        "es": "Rama: `{branch}`.",
    },
    "session_behind": {
        "en": "⚠️ {n} commit(s) behind `origin/{main}`{when}. Before opening a PR: "
              "`git fetch origin && git merge origin/{main}`.",
        "es": "⚠️ Va {n} commit(s) detrás de `origin/{main}`{when}. Antes de abrir un PR: "
              "`git fetch origin && git merge origin/{main}`.",
    },
    "session_up_to_date": {
        "en": "Up to date with `origin/{main}`{when}; {n} commit(s) of your own.",
        "es": "Al día con `origin/{main}`{when}; {n} commit(s) propios.",
    },
    "session_when": {
        "en": ", as of the last fetch ({ago})",
        "es": ", según lo último que se trajo ({ago})",
    },
    "session_dirty": {
        "en": "{n} file(s) with uncommitted changes.",
        "es": "Hay {n} archivo(s) con cambios sin commit.",
    },
    "session_no_hook": {
        "en": "⚠️ The commit-id hook is not active in this clone: `git config core.hooksPath .githooks`.",
        "es": "⚠️ El hook que exige el id de tarea no está activo en este clon: "
              "`git config core.hooksPath .githooks`.",
    },
    "session_no_config": {
        "en": "No .trazabilidad.toml yet: `python -m trazabilidad init` sets the repo up.",
        "es": "Aún no hay .trazabilidad.toml: `python -m trazabilidad init` prepara el repo.",
    },
    "watch_changed": {
        "en": "🔔 `{main}` changed: {n} new commit(s) since the last notice.",
        "es": "🔔 Cambió `{main}`: {n} commit(s) nuevo(s) desde el último aviso.",
    },
    "watch_moved": {
        "en": "🔔 `{main}` changed since the last notice.",
        "es": "🔔 Cambió `{main}` desde el último aviso.",
    },
    "watch_more": {"en": "  · …and {n} more", "es": "  · …y {n} más"},
    "watch_merge": {
        "en": "Bring it into your branch when it suits you: `git merge origin/{main}`.",
        "es": "Tráelo a tu rama cuando te convenga: `git merge origin/{main}`.",
    },
    "ago_hour": {"en": "less than an hour ago", "es": "hace menos de una hora"},
    "ago_hours": {"en": "{n} h ago", "es": "hace {n} h"},
    "ago_days": {"en": "{n} days ago", "es": "hace {n} días"},
    "init_created": {"en": "Created {path}", "es": "Creado {path}"},
    "init_exists": {"en": "Already exists, left as is: {path}", "es": "Ya existe, sin tocar: {path}"},
    "init_hooks_path": {
        "en": "core.hooksPath = .githooks (commit-id hook active in this clone)",
        "es": "core.hooksPath = .githooks (hook de ids activo en este clon)",
    },
    "init_hooks_path_other": {
        "en": "core.hooksPath already points to {path}; left as is. Call the commit-msg hook from there.",
        "es": "core.hooksPath ya apunta a {path}; sin tocar. Llama al hook commit-msg desde ahí.",
    },
}


def t(language: str, message_id: str, /, **values) -> str:
    texts = MESSAGES[message_id]
    return texts.get(language, texts["en"]).format(**values)
