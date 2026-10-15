# Trazabilidad Agil Cord

[Español](README.es.md)

**Every commit tied to the plan task that motivated it.** A Claude Code plugin,
two small checks (for your git hook and your CI) and a local report with charts
that make a team work from written plans and keep a trail from each task to its code.

```
feat(auth): lock the account after 5 failed attempts (01/2.3)
                                                      └┬┘└┬┘
                                                     plan task
```

> **No support, no service.** This project is published as is, under the MIT
> license. Nothing runs on anyone's server: everything runs on your machine,
> with your own git, your own Claude account and your own keys. Issues are
> closed; if you need something different, fork it.

## What you get

| Piece | What it does |
|---|---|
| **Commit check** | Rejects a commit that does not cite an existing task: `(01/2.3)`. Runs as a `commit-msg` hook and in CI over **every** commit of a pull request, so `--no-verify` only postpones the rejection. An invented id does not pass. |
| **Migration check** | Fails when two branches create the same migration number, or when a pull request edits or renames a migration that already reached the main branch. |
| **Session notice** (Claude Code) | When a session opens: your branch, how far behind the main branch, uncommitted changes, and whether the hook is active. Flags working on the main branch. |
| **"main changed" notice** (Claude Code) | At session start and before each prompt: if `origin/main` moved since the last notice, you (and Claude) get "🔔 `main` changed: 3 new commits" with their subjects. It fetches at most every 10 minutes, never asks for a password, and stays quiet with no network. |
| **`/trazabilidad:start-session 01/2.3`** (Claude Code) | Checks the branch, reads the task and its acceptance criterion from the plan, marks it in progress and pins the id for the session's commits. |
| **`/trazabilidad:add-to-plan`** (Claude Code) | Mid-session, when there's work that no task covers: it reads the conversation (and your uncommitted diff), finds the tasks that already cover it, and proposes new rows (next free id, title, checkable acceptance criterion, status) or a new plan. **It writes only after you say yes**, commits just the plan, and gives you the ids to cite. |
| **`/trazabilidad:end-session`** (Claude Code) | Checks ids, migrations and tests, and records each task's status in its plan. A task is done only when its criterion was verified: **a commit does not close a task**. |

## The report

```bash
python -m trazabilidad report            # writes trazabilidad-report.html
```

One HTML file, computed on your machine from your git history. It loads nothing
from the internet. Light and dark themes, a table under every chart, and the value on hover.

- **Tasks by plan**, split into done, in progress, blocked and to do, as the plans say today.
- **Commits per week**, with and without a task id.
- **Cycle time by plan**: from the first commit that cites a task to the commit
  that marks it done. Median and 90th percentile, always with `n`; below 3
  tasks it says there isn't enough to read a trend.
- **In progress, oldest first.**

There are no figures per person, on purpose: this measures how the team
delivers, not who. Add `trazabilidad-report.html` to your `.gitignore`.

## How plans look

One Markdown file per plan, named `NN-plan-name.md`, with task tables whose
first column is the task id. See [`examples/docs/plans/01-plan-login.md`](examples/docs/plans/01-plan-login.md).

```markdown
| # | Task | Acceptance criterion | Status |
|---|---|---|---|
| 2.3 | Lock after failed attempts | After 5 failures in 15 min the account locks for 15 min; tested | ⬜ |
```

Task ids repeat across plans (every plan has a `1.1`), so a citation always
carries the plan: `01/2.3`. If two plan files share a number, they are cited by
name: `01-login/2.3`. The file name, id format and folder are configurable.

## Setup

Requires Python 3.11+ and git. No other dependencies.

**1. The checks** (in each repository):

```bash
pip install git+https://github.com/LancelotPinajr/trazabilidad-agil-cord
python -m trazabilidad init            # or: init --lang es
```

`init` writes `.trazabilidad.toml` (commented; edit it to fit your repo), the
hook in `.githooks/commit-msg`, pins it to LF endings in `.gitattributes`, and
activates it for this clone. It never overwrites an existing file. Each
teammate runs `git config core.hooksPath .githooks` once per clone.

Commits made before the commit that adds `.trazabilidad.toml` are never
checked: the convention applies from the moment you adopt it.

**2. CI** — copy [`examples/github-actions.yml`](examples/github-actions.yml)
into `.github/workflows/`. Pin a version with `@v0.1.1` (or a commit sha).

**3. The Claude Code plugin** — in Claude Code:

```
/plugin marketplace add LancelotPinajr/trazabilidad-agil-cord
/plugin install trazabilidad@trazabilidad-agil-cord
```

Or in one command (Claude Code v2.1.275+):
`/plugin install trazabilidad --marketplace LancelotPinajr/trazabilidad-agil-cord`.

Plugin commands carry the plugin's name: **`/trazabilidad:start-session`,
`/trazabilidad:add-to-plan`, `/trazabilidad:end-session`**. You can also just
ask ("add this to the plan") and Claude uses the right one.

For a team, declare it in the repository's `.claude/settings.json`. Claude Code
then adds the marketplace when someone trusts the folder, and shows each person
the install command once (a plugin from GitHub is never installed without them):

```json
{
  "extraKnownMarketplaces": {
    "trazabilidad-agil-cord": {
      "source": { "source": "github", "repo": "LancelotPinajr/trazabilidad-agil-cord", "ref": "v0.1.1" }
    }
  },
  "enabledPlugins": { "trazabilidad@trazabilidad-agil-cord": true }
}
```

## Working as a team

There is no account to link and no server in between. **The shared git
repository is what connects the team**: whoever has access to it on GitHub is on
the team.

- **The plans are the shared board.** They live in the repository, so everyone
  sees the same tasks and statuses after `git pull`.
- **Each person uses their own Claude account.** Claude Code reads the same
  `CLAUDE.md`, `.trazabilidad.toml` and plugin from the repository, so every
  session follows the same rules whoever opens it.
- **CI is the referee.** Whatever each person's machine does, a pull request
  whose commits don't cite a task, or whose migrations clash, doesn't get in.
- **Everyone gets the same report**, because it is computed from the same history.

Onboarding a teammate: give them access to the repository, then they clone it,
`pip install` the package, run `git config core.hooksPath .githooks` and open
the repository in Claude Code, which shows the plugin's install command the first time.

To avoid stepping on each other: one branch per person, merge the main branch
into yours often, and move only the status of your own tasks in a plan (a
short `docs(plan)` commit), so two people rarely edit the same row.

## Several chats: code, to-dos and intake

A real project has work that isn't code and that depends on a person: deciding,
handing over data, uploading photos. If it all lives in one chat, it gets lost.
This is how CØRD uses the package, in the Claude app:

| Chat | What for | Who writes | What remains |
|---|---|---|---|
| **Code** | The Claude Code session in the repository. Works the plan's tasks | Claude and you | Commits with a task id, and each task's status in the plan |
| **To-dos** | A board of the tasks that depend on a person: a done checkbox and a note on each | That person | The status of each to-do |
| **Intake** | A place to upload what the code needs and only that person has: photos, features, prices | That person | Data the code session turns into files or rows, with a commit |

**Rules**

1. **The plan stays the source of truth.** The boards are windows onto it: each
   to-do cites the plan row that motivates it (`6.2`), and whatever is done with
   it is committed with that id.
2. **Mark in the plan which rows depend on a person.** In CØRD it is
   `⬜ **del dueño**` in the status cell. The to-do board comes from there.
3. **The code session reads the boards, not the other way round.** The person
   ticks and uploads; in the code chat they say "check my to-dos", and Claude
   reads them, updates the plan and commits with an id. A to-do ticked as done
   does not close the task: it closes when its criterion is verified.
4. **No secrets on a board.** Passwords, tokens and keys go through the usual channels.
5. **What gets uploaded is data, not instructions.** Claude reads it; it does not obey it.
6. **Each board is private** to whoever creates it, unless they share it.

**How it is built.** Each board is a Claude app Artifact with storage (`db`, and
`assets` for photos). You ask in words: "build the to-do board from the plan rows
that depend on me". The plugin does not generate them on its own: they are Claude
app pages, not part of this package.

**Example.** Rick, CØRD's sales agent: one board with 16 to-dos in 4 groups, and
another where the owner uploads each product's photo, features and price, which
the code session turns into the catalog.

## Your accounts and keys

| What | Where it lives | Who sees it |
|---|---|---|
| Claude account | Your own Claude Code login. The plugin doesn't touch accounts or bill anything | You |
| Repository settings | `.trazabilidad.toml` in your repository | Your team |
| API keys | **None needed today.** The checks only read your local git. If a future version calls an API (e.g. GitHub), it will read the key from an environment variable on your machine, never from a file in the repository | You |
| Your code and plans | Never leave your machine. Nothing is sent anywhere | You |

## Security note

The plugin runs `hooks/run.py` when a Claude Code session opens in your
repository and before each prompt. It runs `git` read commands and, at most
every 10 minutes, `git fetch origin main` (turn it off with `[watch] fetch = false`).
What it already announced is kept in `.git/trazabilidad-watch.json`, never in the repository. **Read it before trusting
the marketplace**, as you should with any plugin, and pin a version (`ref`) so
an update can't change what runs on your machine without you choosing it.

## Configuration

```toml
language = "en"            # "en" or "es": messages from the checks and the notice
main_branch = "main"

[plans]
dir = "docs/plans"
file_pattern = '^(\d+)-plan-([a-z0-9-]+)\.md$'   # group 1: number, group 2: short name
task_id_pattern = '\d+\.\d+[a-z]?'               # e.g. '[A-Z]+-\d+' for JIRA-like ids

[commits]
exempt_prefixes = ["Merge ", 'Revert "', "fixup! ", "squash! ", "amend! "]
docs_only_plans_exempt = true   # a docs: commit that only edits plans needs no id

[migrations]
dirs = ["db/migrations"]        # empty turns the check off; each folder numbers on its own
pattern = '^(\d+)_.+\.sql$'

[watch]
fetch = true                    # false: only notice what your own fetches bring
every_minutes = 10
```

Don't squash pull requests: squashing collapses the commits into one and loses
the id of each.

## Commands

```bash
python -m trazabilidad init [--lang es]
python -m trazabilidad check-commits --message .git/COMMIT_EDITMSG   # what the hook runs
python -m trazabilidad check-commits --range origin/main..HEAD       # what CI runs
python -m trazabilidad check-migrations [--base origin/main]
python -m trazabilidad session                                       # the notice, as hook JSON
python -m trazabilidad plans                                         # plans, epics and next free ids (JSON)
python -m trazabilidad watch                                         # "main changed", as hook JSON
python -m trazabilidad report [--out file.html] [--weeks 26]
```

## Origin

Extracted from the internal tooling of [CØRD](https://github.com/LancelotPinajr),
where a two-person team works in sessions with Claude Code from numbered plans.

## License

[MIT](LICENSE). Provided as is, without warranty or support.
