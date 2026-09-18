---
name: end-session
description: Close a work session on plan tasks - check commits, migrations and tests, and record each task's status in its plan. Use when the person says they are finishing. / Cierra la sesión - revisa commits, migraciones y pruebas, y deja el estado en el plan.
argument-hint: "[plan/task …] (optional; defaults to the tasks cited by the branch's commits)"
---

# End a work session

Answer in the language the person writes in.

1. **No loose changes.** `git status`: what belongs to the session goes in a
   commit with its id; point out anything else. Don't commit files you didn't
   touch in this session.
2. **Commits cite their task.** Run
   `python -m trazabilidad check-commits --range origin/<main>..HEAD` and, if
   the repo configures migrations, `python -m trazabilidad check-migrations --base origin/<main>`
   (`<main>` is `main_branch` in `.trazabilidad.toml`). If the package is not
   installed: `pip install git+https://github.com/LancelotPinajr/trazabilidad-agil-cord`.
   Fix anything that fails before going on.
3. **Tests pass.** Run the tests for what you touched and the project's suite.
   Report the result as it is.
4. **Status in the plan.** For each task worked (`$ARGUMENTS`, or the ones the
   branch's commits cite): done **only if its acceptance criterion was verified
   in this session**, with the evidence; otherwise in progress, with what is
   missing. **A commit does not close a task**: code existing is not the
   criterion being met. Commit it as `docs(plan): …`, touching only the plan.
5. **Summary for the person:** what is done and verified, what is half done and
   why, and what is left for them (push, pull request, decisions).

Don't push or open the pull request unless the person asks.
