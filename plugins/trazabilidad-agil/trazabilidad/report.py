"""
`python -m trazabilidad report`: one self-contained HTML file with charts.

Everything is computed from the local repository, and the page loads nothing
from the internet: no scripts, fonts or images from anywhere else.

- Tasks by plan, split by status (read from the plans as they are now).
- Commits per week, with and without a task id.
- Cycle time per plan: from the first commit that cites a task to the commit
  that marks it done in its plan. Median and 90th percentile, always with `n`.
- Tasks in progress, oldest first.

Status comes from the task row: ✅ done, 🟡 in progress, ⛔ blocked, ⬜ to do
(or the words done/hecha, in progress/en curso, blocked/bloqueada, todo/por hacer).
"""
from __future__ import annotations

import datetime as dt
import html
import os
import re
import statistics
import subprocess
from dataclasses import dataclass, field

from .commits import _id_regex, load_plans
from .config import Config

STATUSES = ["done", "in_progress", "blocked", "todo"]
_STATUS_MARKS = [
    ("done", ("✅", "✔")),
    ("blocked", ("⛔", "🚫")),
    ("in_progress", ("🟡", "🔄")),
    ("todo", ("⬜",)),
]
_STATUS_WORDS = [
    ("done", ("done", "hecha", "hecho", "cerrada")),
    ("blocked", ("blocked", "bloqueada", "bloqueado")),
    ("in_progress", ("in progress", "en curso", "doing")),
    ("todo", ("todo", "to do", "por hacer", "pendiente")),
]

TEXT = {
    "title": {"en": "Traceability report", "es": "Reporte de trazabilidad"},
    "generated": {"en": "Generated {date} from {branch} · {commits} commits read",
                  "es": "Generado el {date} desde {branch} · {commits} commits leídos"},
    "tile_done": {"en": "Tasks done", "es": "Tareas hechas"},
    "tile_done_of": {"en": "of {n} in {plans} plans", "es": "de {n} en {plans} planes"},
    "tile_cited": {"en": "Commits citing a task", "es": "Commits que citan una tarea"},
    "tile_cited_of": {"en": "{n} of {total} in the last {weeks} weeks", "es": "{n} de {total} en las últimas {weeks} semanas"},
    "tile_cycle": {"en": "Median cycle time", "es": "Mediana del tiempo de ciclo"},
    "tile_cycle_of": {"en": "n = {n} tasks with a cited commit and a done mark",
                      "es": "n = {n} tareas con commit citado y marca de hecha"},
    "days": {"en": "{v} d", "es": "{v} d"},
    "no_data": {"en": "No data yet", "es": "Aún sin datos"},
    "chart_status": {"en": "Tasks by plan", "es": "Tareas por plan"},
    "chart_status_sub": {"en": "Status as the plans say today", "es": "Estado según dicen hoy los planes"},
    "chart_weekly": {"en": "Commits per week", "es": "Commits por semana"},
    "chart_weekly_sub": {"en": "Last {weeks} weeks, merges excluded", "es": "Últimas {weeks} semanas, sin fusiones"},
    "chart_cycle": {"en": "Cycle time by plan", "es": "Tiempo de ciclo por plan"},
    "chart_cycle_sub": {"en": "First commit citing the task → commit that marks it done. Bar: median; label: p90 and n",
                        "es": "Primer commit que cita la tarea → commit que la marca hecha. Barra: mediana; etiqueta: p90 y n"},
    "wip": {"en": "In progress, oldest first", "es": "En curso, de la más antigua a la más reciente"},
    "wip_none": {"en": "Nothing in progress.", "es": "Nada en curso."},
    "done": {"en": "Done", "es": "Hecha"},
    "in_progress": {"en": "In progress", "es": "En curso"},
    "blocked": {"en": "Blocked", "es": "Bloqueada"},
    "todo": {"en": "To do", "es": "Por hacer"},
    "with_id": {"en": "Cites a task", "es": "Cita una tarea"},
    "without_id": {"en": "No task id", "es": "Sin id de tarea"},
    "table": {"en": "Table", "es": "Tabla"},
    "plan": {"en": "Plan", "es": "Plan"},
    "total": {"en": "Total", "es": "Total"},
    "week": {"en": "Week of", "es": "Semana del"},
    "median": {"en": "Median", "es": "Mediana"},
    "task": {"en": "Task", "es": "Tarea"},
    "epic": {"en": "Epic", "es": "Épica"},
    "first_commit": {"en": "First commit", "es": "Primer commit"},
    "age": {"en": "Days since", "es": "Días desde"},
    "not_cited": {"en": "not cited yet", "es": "aún sin commit"},
    "insufficient": {"en": "n < 3: not enough to read a trend", "es": "n < 3: no alcanza para leer una tendencia"},
    "privacy": {"en": "Computed on this machine from the local git repository. This page loads nothing from the internet.",
                "es": "Calculado en esta máquina con el repositorio git local. Esta página no carga nada de internet."},
}


def _t(lang: str, key: str, **values) -> str:
    texts = TEXT[key]
    return texts.get(lang, texts["en"]).format(**values)


# ── Data ────────────────────────────────────────────────────────────────────

@dataclass
class Task:
    plan: str
    task_id: str
    title: str
    epic: str
    status: str
    first_cited: dt.datetime | None = None
    done_at: dt.datetime | None = None


@dataclass
class ReportData:
    tasks: list[Task] = field(default_factory=list)
    plans: list[str] = field(default_factory=list)
    weeks: list[tuple[dt.date, int, int]] = field(default_factory=list)  # (monday, with id, without id)
    commits_read: int = 0
    branch: str = ""


def status_of(cells: list[str]) -> str:
    """The status of a task row: marks or words in its last cell, else marks anywhere.

    Words count only in the last cell: a criterion that says «done when…» is
    not a status.
    """
    last = cells[-1] if cells else ""
    for status, marks in _STATUS_MARKS:
        if any(m in last for m in marks):
            return status
    lowered = last.lower()
    for status, words in _STATUS_WORDS:
        if any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in words):
            return status
    row = " ".join(cells)
    for status, marks in _STATUS_MARKS:
        if any(m in row for m in marks):
            return status
    return "todo"


def parse_plan(text: str, config: Config) -> list[tuple[str, str, str, str]]:
    """(task id, title, epic, status) for each task row, in order."""
    row_re = re.compile(rf"^\|\s*({config.task_id_pattern})\s*\|(.*)$")
    epic = ""
    rows, seen = [], set()
    for line in text.splitlines():
        heading = re.match(r"^#{2,4}\s+(.*)", line)
        if heading:
            epic = heading.group(1).strip()
            continue
        m = row_re.match(line)
        if not m or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        cells = [c.strip() for c in m.group(2).strip().strip("|").split("|")]
        title = re.sub(r"[*`]", "", cells[0]) if cells else ""
        rows.append((m.group(1), title, epic, status_of(cells)))
    return rows


def _git(root: str, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else ""


def _when(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.strip())


def collect(config: Config, weeks: int = 26, today: dt.date | None = None) -> ReportData:
    data = ReportData(branch=_git(config.root, "branch", "--show-current").strip() or "HEAD")
    plans = load_plans(config)
    file_re = re.compile(config.plan_file_pattern)
    folder = config.path(config.plans_dir)
    by_key: dict[tuple[str, str], Task] = {}

    for name in sorted(os.listdir(folder)):
        m = file_re.match(name)
        if not m:
            continue
        plan = f"{m.group(1)}-{m.group(2)}"
        data.plans.append(plan)
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            for task_id, title, epic, status in parse_plan(f.read(), config):
                task = Task(plan, task_id, title, epic, status)
                data.tasks.append(task)
                by_key[(plan, task_id)] = task

        # When each task was marked done: walk the plan's history in order.
        relative = f"{config.plans_dir}/{name}"
        log = _git(config.root, "log", "--reverse", "--format=%H %cI", "--", relative)
        was_done: dict[str, bool] = {}
        for line in log.splitlines():
            sha, iso = line.split(" ", 1)
            for task_id, _, _, status in parse_plan(_git(config.root, "show", f"{sha}:{relative}"), config):
                task = by_key.get((plan, task_id))
                done = status == "done"
                if task and done and not was_done.get(task_id):
                    task.done_at = _when(iso)
                elif task and not done:
                    task.done_at = None
                was_done[task_id] = done

    # Citations and weekly counts, from every non-merge commit reachable from HEAD.
    id_re = _id_regex(config)
    today = today or dt.date.today()
    start = today - dt.timedelta(days=today.weekday()) - dt.timedelta(weeks=weeks - 1)
    counts = {start + dt.timedelta(weeks=i): [0, 0] for i in range(weeks)}
    log = _git(config.root, "log", "--no-merges", "--format=%cI%x1f%B%x1e")
    for record in log.split("\x1e"):
        if "\x1f" not in record:
            continue
        iso, message = record.split("\x1f", 1)
        when = _when(iso)
        data.commits_read += 1
        cited = False
        for key, task_id in id_re.findall(message):
            plan = plans.resolve(key)
            task = by_key.get((plan, task_id)) if plan else None
            if task:
                cited = True
                if task.first_cited is None or when < task.first_cited:
                    task.first_cited = when
        monday = when.date() - dt.timedelta(days=when.weekday())
        if monday in counts:
            counts[monday][0 if cited else 1] += 1
    data.weeks = [(monday, c[0], c[1]) for monday, c in sorted(counts.items())]
    return data


def cycle_days(task: Task) -> float | None:
    if task.status != "done" or not task.first_cited or not task.done_at or task.done_at < task.first_cited:
        return None
    return (task.done_at - task.first_cited).total_seconds() / 86400


def percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    low, high = int(k), min(int(k) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (k - low)


# ── Rendering ───────────────────────────────────────────────────────────────

def _e(value) -> str:
    return html.escape(str(value), quote=True)


def _fmt_days(value: float) -> str:
    return f"{value:.1f}" if value < 10 else f"{value:.0f}"


def _bar_path(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    """A horizontal bar: square at the baseline, rounded data end."""
    r = min(r, w / 2, h / 2)
    return (f"M{x:.1f},{y:.1f}H{x + w - r:.1f}Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}"
            f"V{y + h - r:.1f}Q{x + w:.1f},{y + h:.1f} {x + w - r:.1f},{y + h:.1f}H{x:.1f}Z")


def _col_path(x: float, y: float, w: float, h: float, r: float = 4) -> str:
    """A column: square at the baseline, rounded top."""
    r = min(r, w / 2, h / 2)
    return (f"M{x:.1f},{y + h:.1f}V{y + r:.1f}Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f}"
            f"H{x + w - r:.1f}Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f}V{y + h:.1f}Z")


def _nice_max(value: int) -> int:
    if value <= 5:
        return 5
    magnitude = 10 ** (len(str(value)) - 1)
    for step in (1, 2, 5, 10):
        top = step * magnitude
        if top >= value:
            return top
    return value


def _status_chart(data: ReportData, lang: str) -> str:
    rows = []
    for plan in data.plans:
        counts = {s: 0 for s in STATUSES}
        for task in data.tasks:
            if task.plan == plan:
                counts[task.status] += 1
        if sum(counts.values()):
            rows.append((plan, counts))
    if not rows:
        return f'<p class="empty">{_e(_t(lang, "no_data"))}</p>'

    label_w, bar_h, row_h, right = 150, 20, 34, 110
    width = 760
    plot_w = width - label_w - right
    most = max(sum(c.values()) for _, c in rows)
    height = row_h * len(rows) + 8
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_e(_t(lang, "chart_status"))}">']
    for i, (plan, counts) in enumerate(rows):
        y = 4 + i * row_h + (row_h - bar_h) / 2
        total = sum(counts.values())
        parts.append(f'<text class="axis-label" x="{label_w - 10}" y="{y + bar_h / 2}" text-anchor="end" '
                     f'dominant-baseline="middle">{_e(plan)}</text>')
        x = label_w
        present = [s for s in STATUSES if counts[s]]
        for j, status in enumerate(present):
            w = plot_w * counts[status] / most
            gap = 2 if j < len(present) - 1 else 0
            tip = f"{_t(lang, status)}: {counts[status]} / {total}"
            shape = (_bar_path(x, y, w - gap, bar_h) if j == len(present) - 1
                     else f"M{x:.1f},{y:.1f}h{max(w - gap, 0.5):.1f}v{bar_h}h-{max(w - gap, 0.5):.1f}Z")
            parts.append(f'<path class="mark s-{status}" d="{shape}" tabindex="0" '
                         f'data-tip="{_e(plan)}" data-value="{_e(tip)}"/>')
            x += w
        done = counts["done"]
        parts.append(f'<text class="value-label" x="{x + 8:.1f}" y="{y + bar_h / 2}" dominant-baseline="middle">'
                     f'{done}/{total}</text>')
    parts.append("</svg>")

    legend = "".join(f'<span class="key"><span class="swatch s-{s}"></span>{_icon(s)} {_e(_t(lang, s))}</span>'
                     for s in STATUSES)
    head = "".join(f"<th>{_e(_t(lang, s))}</th>" for s in STATUSES)
    body = "".join(f"<tr><td>{_e(p)}</td>" + "".join(f"<td>{c[s]}</td>" for s in STATUSES)
                   + f"<td>{sum(c.values())}</td></tr>" for p, c in rows)
    table = (f'<details><summary>{_e(_t(lang, "table"))}</summary><table><thead><tr><th>{_e(_t(lang, "plan"))}</th>'
             f'{head}<th>{_e(_t(lang, "total"))}</th></tr></thead><tbody>{body}</tbody></table></details>')
    return f'<div class="legend">{legend}</div>{"".join(parts)}{table}'


def _icon(status: str) -> str:
    return {"done": "✓", "in_progress": "◐", "blocked": "⊘", "todo": "○"}[status]


def _weekly_chart(data: ReportData, lang: str) -> str:
    if not data.weeks:
        return f'<p class="empty">{_e(_t(lang, "no_data"))}</p>'
    width, height, left, bottom, top = 760, 240, 40, 28, 12
    plot_w, plot_h = width - left - 10, height - bottom - top
    top_value = _nice_max(max(w + wo for _, w, wo in data.weeks) or 1)
    band = plot_w / len(data.weeks)
    col_w = min(24, band * 0.7)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_e(_t(lang, "chart_weekly"))}">']
    for k in range(5):
        value = top_value * k / 4
        y = top + plot_h - plot_h * k / 4
        parts.append(f'<line class="{"baseline" if k == 0 else "grid"}" x1="{left}" x2="{width - 10}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{left - 6}" y="{y:.1f}" text-anchor="end" dominant-baseline="middle">{value:g}</text>')
    for i, (monday, with_id, without_id) in enumerate(data.weeks):
        x = left + i * band + (band - col_w) / 2
        base = top + plot_h
        tip = f"{_t(lang, 'with_id')}: {with_id} · {_t(lang, 'without_id')}: {without_id}"
        segments = [(with_id, "c-1"), (without_id, "c-2")]
        segments = [(v, c) for v, c in segments if v]
        for j, (value, css) in enumerate(segments):
            h = plot_h * value / top_value
            is_top = j == len(segments) - 1
            gap = 0 if is_top else 2
            y = base - h
            shape = (_col_path(x, y, col_w, h) if is_top
                     else f"M{x:.1f},{y + gap:.1f}h{col_w:.1f}V{base:.1f}h-{col_w:.1f}Z")
            parts.append(f'<path class="mark {css}" d="{shape}" tabindex="0" '
                         f'data-tip="{_e(_t(lang, "week"))} {monday.isoformat()}" data-value="{_e(tip)}"/>')
            base = y
        if i % max(1, len(data.weeks) // 6) == 0:
            parts.append(f'<text class="tick" x="{x + col_w / 2:.1f}" y="{height - 8}" text-anchor="middle">'
                         f'{monday.strftime("%d/%m")}</text>')
    parts.append("</svg>")
    legend = (f'<span class="key"><span class="swatch c-1"></span>{_e(_t(lang, "with_id"))}</span>'
              f'<span class="key"><span class="swatch c-2"></span>{_e(_t(lang, "without_id"))}</span>')
    body = "".join(f"<tr><td>{m.isoformat()}</td><td>{w}</td><td>{wo}</td></tr>" for m, w, wo in data.weeks)
    table = (f'<details><summary>{_e(_t(lang, "table"))}</summary><table><thead><tr><th>{_e(_t(lang, "week"))}</th>'
             f'<th>{_e(_t(lang, "with_id"))}</th><th>{_e(_t(lang, "without_id"))}</th></tr></thead>'
             f'<tbody>{body}</tbody></table></details>')
    return f'<div class="legend">{legend}</div>{"".join(parts)}{table}'


def _cycle_chart(data: ReportData, lang: str) -> str:
    rows = []
    for plan in data.plans:
        values = [d for t in data.tasks if t.plan == plan and (d := cycle_days(t)) is not None]
        if values:
            rows.append((plan, statistics.median(values), percentile(values, 0.9), len(values)))
    if not rows:
        return f'<p class="empty">{_e(_t(lang, "no_data"))}</p>'
    label_w, bar_h, row_h, right, width = 150, 20, 34, 170, 760
    plot_w = width - label_w - right
    most = max(r[1] for r in rows) or 1
    height = row_h * len(rows) + 8
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_e(_t(lang, "chart_cycle"))}">']
    for i, (plan, median, p90, n) in enumerate(rows):
        y = 4 + i * row_h + (row_h - bar_h) / 2
        w = max(plot_w * median / most, 2)
        label = f"{_t(lang, 'days', v=_fmt_days(median))} · p90 {_fmt_days(p90)} · n={n}"
        parts.append(f'<text class="axis-label" x="{label_w - 10}" y="{y + bar_h / 2}" text-anchor="end" '
                     f'dominant-baseline="middle">{_e(plan)}</text>')
        parts.append(f'<path class="mark c-1" d="{_bar_path(label_w, y, w, bar_h)}" tabindex="0" '
                     f'data-tip="{_e(plan)}" data-value="{_e(label)}"/>')
        parts.append(f'<text class="value-label" x="{label_w + w + 8:.1f}" y="{y + bar_h / 2}" '
                     f'dominant-baseline="middle">{_e(label)}</text>')
    parts.append("</svg>")
    few = [r[0] for r in rows if r[3] < 3]
    note = f'<p class="note">{_e(_t(lang, "insufficient"))}: {_e(", ".join(few))}</p>' if few else ""
    body = "".join(f"<tr><td>{_e(p)}</td><td>{_fmt_days(m)}</td><td>{_fmt_days(q)}</td><td>{n}</td></tr>"
                   for p, m, q, n in rows)
    table = (f'<details><summary>{_e(_t(lang, "table"))}</summary><table><thead><tr><th>{_e(_t(lang, "plan"))}</th>'
             f'<th>{_e(_t(lang, "median"))} (d)</th><th>p90 (d)</th><th>n</th></tr></thead>'
             f'<tbody>{body}</tbody></table></details>')
    return "".join(parts) + note + table


def _wip_table(data: ReportData, lang: str, now: dt.datetime) -> str:
    wip = [t for t in data.tasks if t.status == "in_progress"]
    if not wip:
        return f'<p class="empty">{_e(_t(lang, "wip_none"))}</p>'
    wip.sort(key=lambda t: t.first_cited or now)
    rows = []
    for t in wip:
        if t.first_cited:
            since, age = t.first_cited.date().isoformat(), str((now - t.first_cited).days)
        else:
            since, age = _t(lang, "not_cited"), "—"
        rows.append(f"<tr><td>{_e(t.plan)}/{_e(t.task_id)}</td><td>{_e(t.title)}</td><td>{_e(t.epic)}</td>"
                    f"<td>{_e(since)}</td><td class='num'>{_e(age)}</td></tr>")
    return (f'<table class="wip"><thead><tr><th>{_e(_t(lang, "task"))}</th><th></th><th>{_e(_t(lang, "epic"))}</th>'
            f'<th>{_e(_t(lang, "first_commit"))}</th><th class="num">{_e(_t(lang, "age"))}</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


STYLE = """
.viz-root{color-scheme:light;--surface-1:#fcfcfb;--page:#f9f9f7;--text-primary:#0b0b0b;--text-secondary:#52514e;
--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--border:rgba(11,11,11,.10);--c-1:#2a78d6;--c-2:#eb6834;
--s-done:#0ca30c;--s-in_progress:#fab219;--s-blocked:#d03b3b;--s-todo:#c3c2b7}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])) .viz-root{color-scheme:dark;
--surface-1:#1a1a19;--page:#0d0d0d;--text-primary:#fff;--text-secondary:#c3c2b7;--grid:#2c2c2a;--axis:#383835;
--border:rgba(255,255,255,.10);--c-1:#3987e5;--c-2:#d95926;--s-todo:#52514e}}
:root[data-theme="dark"] .viz-root{color-scheme:dark;--surface-1:#1a1a19;--page:#0d0d0d;--text-primary:#fff;
--text-secondary:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--border:rgba(255,255,255,.10);--c-1:#3987e5;--c-2:#d95926;
--s-todo:#52514e}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--text-primary);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
.viz-root{background:var(--page);min-height:100vh;padding:32px 16px}
main{max-width:820px;margin:0 auto}
h1{font-size:24px;font-weight:600;margin:0 0 4px}
h2{font-size:16px;font-weight:600;margin:0}
.sub,.meta,.note,.empty{color:var(--text-secondary);margin:2px 0 12px;font-size:13px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:24px 0}
.tile,.card{background:var(--surface-1);border:1px solid var(--border);border-radius:12px;padding:16px}
.card{margin:0 0 16px}
.tile .label{color:var(--text-secondary);font-size:13px}
.tile .value{font-size:32px;font-weight:600;margin:4px 0}
.tile .of{color:var(--muted);font-size:12px}
svg{width:100%;min-width:600px;height:auto;display:block;overflow:visible}
.grid{stroke:var(--grid);stroke-width:1}.baseline{stroke:var(--axis);stroke-width:1}
.tick{fill:var(--muted);font-size:12px;font-variant-numeric:tabular-nums}
.axis-label{fill:var(--text-secondary);font-size:13px}
.value-label{fill:var(--text-primary);font-size:13px;font-variant-numeric:tabular-nums}
.mark{cursor:default;outline:none;transition:opacity .1s}
.mark:hover,.mark:focus{opacity:.8}
.c-1{fill:var(--c-1);background:var(--c-1)}.c-2{fill:var(--c-2);background:var(--c-2)}
.s-done{fill:var(--s-done);background:var(--s-done)}.s-in_progress{fill:var(--s-in_progress);background:var(--s-in_progress)}
.s-blocked{fill:var(--s-blocked);background:var(--s-blocked)}.s-todo{fill:var(--s-todo);background:var(--s-todo)}
.legend{display:flex;flex-wrap:wrap;gap:16px;margin:0 0 8px;color:var(--text-secondary);font-size:12px}
.key{display:inline-flex;align-items:center;gap:6px}
.swatch{width:10px;height:10px;border-radius:2px;display:inline-block}
details{margin-top:8px}summary{color:var(--text-secondary);font-size:12px;cursor:pointer}
table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px;font-variant-numeric:tabular-nums}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid)}th{color:var(--text-secondary);font-weight:500}
.num{text-align:right}
.table-wrap{overflow-x:auto}
#tip{position:fixed;pointer-events:none;background:var(--surface-1);border:1px solid var(--border);border-radius:8px;
padding:6px 10px;font-size:12px;box-shadow:0 4px 12px rgba(0,0,0,.12);display:none;max-width:280px}
#tip strong{display:block;color:var(--text-primary)}#tip span{color:var(--text-secondary)}
footer{color:var(--muted);font-size:12px;margin-top:24px}
"""

SCRIPT = """
const tip=document.getElementById('tip');
function show(el,x,y){tip.replaceChildren();const v=document.createElement('strong');v.textContent=el.dataset.value;
const l=document.createElement('span');l.textContent=el.dataset.tip;tip.append(v,l);tip.style.display='block';
const r=tip.getBoundingClientRect();tip.style.left=Math.min(x+12,innerWidth-r.width-8)+'px';
tip.style.top=Math.max(8,y-r.height-12)+'px'}
document.querySelectorAll('.mark').forEach(el=>{
el.addEventListener('pointermove',e=>show(el,e.clientX,e.clientY));
el.addEventListener('pointerleave',()=>tip.style.display='none');
el.addEventListener('focus',()=>{const b=el.getBoundingClientRect();show(el,b.right,b.top)});
el.addEventListener('blur',()=>tip.style.display='none')});
"""


def render(data: ReportData, config: Config, weeks: int, now: dt.datetime | None = None) -> str:
    lang = config.language
    now = now or dt.datetime.now(dt.timezone.utc)
    total, done = len(data.tasks), sum(t.status == "done" for t in data.tasks)
    with_id = sum(w for _, w, _ in data.weeks)
    all_commits = with_id + sum(wo for _, _, wo in data.weeks)
    cycles = [d for t in data.tasks if (d := cycle_days(t)) is not None]

    def tile(label, value, of):
        return (f'<div class="tile"><div class="label">{_e(label)}</div><div class="value">{_e(value)}</div>'
                f'<div class="of">{_e(of)}</div></div>')

    tiles = "".join([
        tile(_t(lang, "tile_done"), f"{done}", _t(lang, "tile_done_of", n=total, plans=len(data.plans))),
        tile(_t(lang, "tile_cited"), f"{round(100 * with_id / all_commits)} %" if all_commits else "—",
             _t(lang, "tile_cited_of", n=with_id, total=all_commits, weeks=weeks)),
        tile(_t(lang, "tile_cycle"), _t(lang, "days", v=_fmt_days(statistics.median(cycles))) if cycles else "—",
             _t(lang, "tile_cycle_of", n=len(cycles))),
    ])

    def card(title, sub, body):
        subtitle = f'<p class="sub">{_e(sub)}</p>' if sub else ""
        return f'<section class="card"><h2>{_e(title)}</h2>{subtitle}<div class="table-wrap">{body}</div></section>'

    meta = _t(lang, "generated", date=now.date().isoformat(), branch=data.branch, commits=data.commits_read)
    return f"""<!doctype html>
<html lang="{_e(lang)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(_t(lang, "title"))}</title>
<style>{STYLE}</style></head>
<body><div class="viz-root"><main>
<h1>{_e(_t(lang, "title"))}</h1><p class="meta">{_e(meta)}</p>
<div class="tiles">{tiles}</div>
{card(_t(lang, "chart_status"), _t(lang, "chart_status_sub"), _status_chart(data, lang))}
{card(_t(lang, "chart_weekly"), _t(lang, "chart_weekly_sub", weeks=weeks), _weekly_chart(data, lang))}
{card(_t(lang, "chart_cycle"), _t(lang, "chart_cycle_sub"), _cycle_chart(data, lang))}
{card(_t(lang, "wip"), "", _wip_table(data, lang, now))}
<footer>{_e(_t(lang, "privacy"))}</footer>
</main><div id="tip" role="status"></div></div>
<script>{SCRIPT}</script>
</body></html>
"""


def write_report(config: Config, out: str, weeks: int = 26) -> tuple[str, ReportData]:
    data = collect(config, weeks=weeks)
    path = out if os.path.isabs(out) else os.path.join(config.root, out)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(data, config, weeks))
    return path, data

