# Plan 02: make it cost one step to adopt

Today adopting takes three steps (install the package, activate the hook, install
the plugin), and the first one someone skips is the hook — then commits go in
without an id and the trail breaks. In the repository this was extracted from,
20 of 32 commits after adoption carried no id for exactly that reason.

Cite these tasks as `02/1.2`, `02/2.1`…

## Decisions

| # | Decision | Status |
|---|---|---|
| E1 | Git cannot activate a repository's hooks on its own: `core.hooksPath` is per clone, on purpose. So the goal is not to remove that step but to make it impossible to miss | ✅ |
| E2 | This repository uses its own tool: plans in `docs/plans`, the hook active, the commit check in its CI. If it is not good enough for its own history, it is not good enough to publish | ✅ |
| E3 | Whether to publish the panel and these checks as one plugin or split them | ⬜ |

## Epic 1 — The first five minutes

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 1.1 | A demo repository | `examples/demo` lets someone see a commit rejected without touching their own work | ✅ |
| 1.2 | Who it is not for | Both READMEs say plainly which teams should not adopt it | ✅ |
| 1.3 | `init` leaves nothing pending | After `init`, the output names exactly what is still missing (CI file, plugin install) as copyable commands | ⬜ |
| 1.4 | A short demo recording | A GIF in the README showing a commit rejected and then accepted; under 10 seconds | ⬜ |

## Epic 2 — Nobody commits without the hook

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 2.1 | The notice insists | When the hook is missing, the session notice gives the one command to fix it, and keeps saying so until it is active | ⬜ |
| 2.2 | CI says what to run locally | When CI rejects commits, its message names the command that would have caught it on the machine | ⬜ |
| 2.3 | `init` is safe to re-run | Running it in a configured repo reports what is already in place and changes nothing | ⬜ |
| 2.4 | `init` leaves nothing staged | It stages the files it writes, so the first `docs(plan)` commit carries them too and loses its exemption — the hook then rejects a commit that should pass. It hit twice: in the repo this came from and here. Either leave them unstaged or say so in the output | ⬜ |

## Epic 3 — This repository uses itself

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 3.1 | Plans and hook | `.trazabilidad.toml`, `.githooks` and `docs/plans` exist here, and a commit without an id is rejected in this clone | ⬜ |
| 3.2 | Its own commit check in CI | `tests.yml` (or a sibling job) runs `check-commits` over a pull request's commits, and the badge is green | ⬜ |
| 3.3 | Its own report | `python -m trazabilidad report` on this repository produces numbers that make sense, screenshot included in the README | ⬜ |
