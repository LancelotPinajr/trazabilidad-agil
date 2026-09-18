---
name: trazabilidad
description: Turn what was decided or built in this conversation into tasks of a plan, so the work can be committed with a task id. Use when the person types /trazabilidad, asks to "add this to a plan", or has work to commit that no task covers. / Convierte lo decidido o programado en la conversación en tareas de un plan, para poder hacer commit con su id.
argument-hint: "[plan, e.g. 01 or 01-login] [what to add; defaults to the conversation]"
---

# Add the conversation to a plan

Answer in the language the person writes in.

The goal: work that happened in this conversation ends up as rows in a plan,
with an acceptance criterion, so every commit can cite `plan/task`. **The
plans are shared with the team: propose first, write only after a clear yes.**

`$ARGUMENTS` may name a plan and/or say what to add. Without it, take the
work from this conversation.

## 1. Read the plans

Run `python -m trazabilidad plans` (JSON: plans, epics, tasks, `next_task_id`
per epic, `next_epic_number`, `next_plan_number`, and `cite_as`). If the
package is not installed, read the files in `plans.dir` of `.trazabilidad.toml`
directly and work the ids out by hand, carefully.

## 2. Work out what the conversation produced

List the concrete units of work: what was built or changed (look at
`git status` and `git diff` too), what was decided, and what was left
pending. One task = one thing someone can verify. Leave out chatter,
dead ends and anything the person discarded.

## 3. Don't duplicate

For each unit, look for an existing task that already covers it (same
intent, even if worded differently). If there is one, **don't add a row**:
report its id (`cite_as/id`) for the commits, and whether its status should
move (that's the person's call; see `/end-session`).

## 4. Propose

For the rest, propose rows in the plan and epic where they belong:

- **id**: the epic's `next_task_id`, then the following ones. A new epic takes
  `next_epic_number` and starts at `.1`. Never reuse or renumber an existing id.
- **title**: short, what the task is.
- **acceptance criterion**: observable and checkable ("an invalid RFC returns
  400 with the field name; tested"), not "works well". If the conversation
  doesn't say how it will be verified, write the best criterion you can and
  flag it for the person to confirm.
- **status**: in progress if it is being worked on now; done **only** if the
  criterion was verified in this conversation, with the evidence; otherwise to do.

If nothing fits an existing plan, propose a new file
`<plans.dir>/<next_plan_number>-plan-<short-name>.md` with a title, a one-line
purpose and an epic table in the same format as the other plans.

Show the proposal as a table (plan · epic · id · title · criterion · status)
plus the ids to cite for work already covered. **Stop and wait for the person.**

## 5. Write, after a yes

- Add the rows to the plan's epic table, keeping its columns and style. Touch
  nothing else in the file.
- Commit only the plan file(s): `docs(plan): <plan> <ids> from the session`.
  That commit needs no id.
- Tell the person the ids to cite, e.g. `feat(auth): … (01/2.4)`. If the work
  is still uncommitted, offer to commit it now with those ids.

Don't push unless the person asks.
