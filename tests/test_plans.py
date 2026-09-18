"""
`plans`: the next free ids that /trazabilidad uses to propose rows.
"""
import json
import os
import subprocess
import sys

from trazabilidad.config import Config
from trazabilidad.plans import _next_task, describe

HEAD = "| # | Task | Criterion | Status |\n|---|---|---|---|\n"
PLUGIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugins", "trazabilidad-agil")


def test_next_task():
    assert _next_task(["2.1", "2.3", "2.3b"]) == "2.4"
    assert _next_task(["1.9", "1.10"]) == "1.11"          # numeric, not alphabetical
    assert _next_task(["B-1"]) is None                    # custom ids: no guess


def _write(folder, name, text):
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        f.write(text)


def test_describe(tmp_path):
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    _write(plans, "01-plan-login.md", "# Plan 01: login\n## Epic 1\n" + HEAD + "| 1.1 | Form | x | ✅ |\n"
           "## Epic 2\n" + HEAD + "| 2.1 | Count | x | ⬜ |\n| 2.3b | Unlock | x | 🟡 |\n")
    _write(plans, "07-plan-billing.md", "# Plan 07\n## Epic 1\n" + HEAD + "| 1.1 | Invoice | x | ⬜ |\n")
    _write(plans, "07-plan-reports.md", "# Plan 07 bis\n")
    data = describe(Config(root=str(tmp_path)))

    assert data["next_plan_number"] == "08"
    login, billing, reports = data["plans"]
    assert login["cite_as"] == "01" and billing["cite_as"] == "07-billing"   # 07 is shared
    assert login["title"] == "Plan 01: login"
    assert [e["next_task_id"] for e in login["epics"]] == ["1.2", "2.4"]
    assert login["next_epic_number"] == 3
    assert login["epics"][1]["tasks"][1] == {"id": "2.3b", "title": "Unlock", "status": "in_progress"}
    assert reports["epics"] == [] and reports["next_epic_number"] == 1


def test_no_plans_yet(tmp_path):
    data = describe(Config(root=str(tmp_path)))
    assert data["plans"] == [] and data["next_plan_number"] == "01"


def test_cli_prints_json(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    _write(tmp_path / "docs" / "plans", "03-plan-api.md", "## Epic 1\n" + HEAD + "| 1.1 | Á | x | ⬜ |\n")
    out = subprocess.run([sys.executable, "-m", "trazabilidad", "plans"], cwd=tmp_path, capture_output=True,
                         text=True, encoding="utf-8", env={**os.environ, "PYTHONPATH": PLUGIN})
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout)["plans"][0]["epics"][0]["tasks"][0]["title"] == "Á"
