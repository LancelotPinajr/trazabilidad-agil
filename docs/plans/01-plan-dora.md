# Plan 01: DORA metrics, in a panel and in the report

The repository already knows what was planned and what was committed. The four
DORA metrics are the next thing it can answer from the same history —
**computed on your machine, from your git, sent nowhere** — plus a live panel
in Claude Code so the numbers are there while you work, not in a file you
remember to open.

Cite these tasks as `01/1.2`, `01/3.1`…

## Decisions

| # | Decision | Status |
|---|---|---|
| D1 | Git is the only source. No deployment API, no tracker, no account: whatever cannot be derived from the repository is reported as missing, not guessed | ✅ |
| D2 | What counts as a deploy is configurable, because it differs per repo: a merge into the main branch, a tag, or commits touching given paths. Default: a merge into the main branch | ⬜ |
| D3 | Change failure rate and time to restore need incidents to be recorded. Until a repository records them, both say "not enough data" and name what is missing. **No proxy is shown as if it were the metric** | ⬜ |
| D4 | The panel is optional. The plugin keeps working without it, and a surface that cannot draw a panel falls back to the report | ⬜ |
| D5 | Whether the panel needs a minimum Claude Code version, and what the plugin does on older ones | ⬜ |

## Epic 1 — Delivery, from git alone

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 1.1 | What counts as a deploy | `[dora]` in `.trazabilidad.toml` picks merge, tag or paths (D2); the demo repo counts the same deploys a human counts by hand | ⬜ |
| 1.2 | Deployment frequency | Deploys per week for the last N weeks, plus the median gap between them; `--weeks` respected | ⬜ |
| 1.3 | Lead time for changes | From a change's first commit to the deploy that carried it: median and p90, always with `n`; under 3 it says there isn't enough to read | ⬜ |
| 1.4 | Works on a repo without merges | A repo that commits straight to the main branch gets numbers too, or a clear reason why not | ⬜ |

## Epic 2 — Incidents, the two metrics git can't see

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 2.1 | A way to record an incident | A documented convention (e.g. a `hotfix:` commit citing an incident id) and a pattern for it in the config; a repo that doesn't use it stays unaffected | ⬜ |
| 2.2 | Change failure rate | Share of deploys followed by a recorded incident, with the window used and `n` | ⬜ |
| 2.3 | Time to restore | From the incident's first commit to the deploy that closes it: median and p90 with `n` | ⬜ |
| 2.4 | Honest absence | With no incidents recorded, both metrics read "not enough data" and say what to start recording; never a number that looks real | ⬜ |

## Epic 3 — The panel in Claude Code

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 3.1 | Open and close it | `/trazabilidad:panel` opens a panel titled with the repository; running it again closes it | ⬜ |
| 3.2 | What it shows | Branch and how far behind the main branch; tasks in progress; the four DORA numbers, each with its `n` or its "not enough data" | ⬜ |
| 3.3 | It never slows the session | Numbers are computed off the prompt path and cached; recomputed at most every few minutes and when a commit lands | ⬜ |
| 3.4 | Degrades without drama | Where no panel can be drawn, the command says so and points to `report`; the rest of the plugin is unaffected (D4) | ⬜ |
| 3.5 | Readable in both themes | Light and dark, and at a narrow width, without truncated numbers | ⬜ |

## Epic 4 — The same numbers in the report

| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 4.1 | DORA section | The HTML report shows the four metrics with the same values as the panel, each with its `n` | ⬜ |
| 4.2 | Documented | The README says, for each metric, how it is computed, what it needs and what it cannot see | ⬜ |
| 4.3 | Tested | Tests cover a repo with merges, one without, and one with no incidents recorded | ⬜ |
