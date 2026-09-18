---
name: start-session
description: Start a work session on a task from the repo's plans (e.g. "/start-session 12/2.3"). Use when the person says which plan task they will work on. / Abre una sesión sobre una tarea del plan («/start-session 12/2.3»); úsala cuando la persona diga qué tarea va a trabajar.
argument-hint: "<plan>/<task>, e.g. 12/2.3"
---

# Start a session on a plan task

Answer in the language the person writes in (the repo's `.trazabilidad.toml`
also has a `language` setting).

The task is `$ARGUMENTS`: `plan/task`, e.g. plan 12, task 2.3. When two plan
files share a number they are cited by name: `12-login/2.3`.

1. **Check the branch.** `git branch --show-current`. If it is the main branch
   (`main_branch` in `.trazabilidad.toml`, `main` by default) or clearly not
   this person's branch, stop and say so before touching anything.
2. **Find the task.** Plans live in `plans.dir` of `.trazabilidad.toml`. Find
   the table row whose first column is the task id. If it does not exist, say
   so: work starts from a task in the plan. Add the row first (a `docs:` commit
   that only edits the plan needs no id).
3. **Read around it:** its epic, the decisions it cites and the tasks it depends
   on. If it is blocked or depends on something unfinished, say so first.
4. **Summarize** in a few lines: what the task is, its acceptance criterion
   exactly as written, and how you propose to verify it.
5. **Mark it in progress** in the plan (the plan's own in-progress marker) and
   commit that change with a `docs(plan): …` commit that only touches the plan.

From here on, **every commit of the session cites the id**:
`type(scope): subject ($ARGUMENTS)`. The `commit-msg` hook and CI enforce it.
