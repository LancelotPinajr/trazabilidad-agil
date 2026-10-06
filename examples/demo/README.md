# Demo repository

A tiny repository to try the checks without touching your own work: one plan
(`docs/plans/01-plan-login.md`), one migration and a `.trazabilidad.toml`.

Copy this folder somewhere else, then:

```bash
git init
pip install git+https://github.com/LancelotPinajr/trazabilidad-agil-cord
python -m trazabilidad init          # adds the hook; keeps the .trazabilidad.toml that is already here
git add .
git commit -m "feat(auth): sign-in form"          # ❌ rejected: it cites no task
git commit -m "feat(auth): sign-in form (01/1.1)" # ✅ passes
```

The first message is rejected because no task id follows it. The second cites
task `1.1` of plan `01`, which exists in `docs/plans/01-plan-login.md`. An id
that is not in a plan (`01/9.9`) is rejected too.

Then look around:

```bash
python -m trazabilidad plans         # plans, epics and the next free id, as JSON
python -m trazabilidad report        # writes trazabilidad-report.html
```

The migration check compares your branch against the main branch, so it needs
two branches to have something to say:

```bash
git branch -M main
git switch -c feature
cp db/migrations/001_users.sql db/migrations/001_sessions.sql
git add . && git commit -m "feat(db): sessions table (01/2.1)"
python -m trazabilidad check-migrations --base main   # ❌ 001 is taken
```

Delete the folder when you are done; nothing was installed outside it except
the Python package.
