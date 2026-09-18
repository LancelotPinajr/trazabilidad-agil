import pytest

from trazabilidad.commits import check_message, load_plans
from trazabilidad.config import Config

CODE = ["src/app.py"]
TABLE = "| # | Task | Criterion | Status |\n|---|---|---|---|\n"


@pytest.fixture
def cfg(tmp_path):
    plans = tmp_path / "docs" / "plans"
    plans.mkdir(parents=True)
    (plans / "21-plan-traceability.md").write_text(
        TABLE + "| 1.1 | a | b | todo |\n| 2.3 | a | b | todo |\n| 2.3b | a | b | todo |\n", encoding="utf-8")
    (plans / "16-plan-agents.md").write_text(TABLE + "| 0.1 | a | b | done |\n", encoding="utf-8")
    (plans / "16-plan-starter.md").write_text(TABLE + "| 0.1 | a | b | done |\n", encoding="utf-8")
    (plans / "notes.md").write_text(TABLE + "| 9.9 | a | b | todo |\n", encoding="utf-8")
    return Config(root=str(tmp_path), found=True)


@pytest.fixture
def plans(cfg):
    return load_plans(cfg)


def check(message, cfg, plans, files=CODE):
    return check_message(message, files, plans, cfg)


def test_valid_id(cfg, plans):
    assert check("feat(agile): transitions in one transaction (21/2.3)", cfg, plans) == []


def test_several_ids_and_letter_suffix(cfg, plans):
    assert check("fix: x (21/1.1, 21/2.3b)", cfg, plans) == []


def test_long_plan_form(cfg, plans):
    assert check("fix: x (21-traceability/1.1)", cfg, plans) == []


def test_id_in_body_followed_by_period(cfg, plans):
    assert check("feat: x\n\nPart of 21/2.3.\n", cfg, plans) == []


def test_missing_id(cfg, plans):
    assert check("feat: x", cfg, plans) == ["does not cite any task"]


def test_id_without_plan(cfg, plans):
    assert check("feat: x (2.3)", cfg, plans) == ["does not cite any task"]


def test_invented_task(cfg, plans):
    assert check("feat: x (21/9.9)", cfg, plans) == ["21/9.9: plan 21-traceability has no task 9.9"]


def test_unknown_plan(cfg, plans):
    assert check("feat: x (99/1.1)", cfg, plans) == ["99/1.1: there is no plan 99 in docs/plans"]


def test_shared_plan_number_asks_for_the_name(cfg, plans):
    problems = check("feat: x (16/0.1)", cfg, plans)
    assert len(problems) == 1 and "16-agents/0.1, 16-starter/0.1" in problems[0]
    assert check("feat: x (16-starter/0.1)", cfg, plans) == []


def test_a_good_id_does_not_hide_a_bad_one(cfg, plans):
    assert check("feat: x (21/1.1, 21/7.7)", cfg, plans) == ["21/7.7: plan 21-traceability has no task 7.7"]


def test_only_plan_files_count(plans):
    assert set(plans.tasks) == {"21-traceability", "16-agents", "16-starter"}


def test_docs_only_touching_a_plan_is_exempt(cfg, plans):
    assert check("docs(plan): plan 22", cfg, plans, ["docs/plans/21-plan-traceability.md"]) == []


def test_docs_touching_code_needs_an_id(cfg, plans):
    files = ["docs/plans/21-plan-traceability.md", "src/app.py"]
    assert check("docs: x", cfg, plans, files) == ["does not cite any task"]


def test_feat_touching_only_a_plan_needs_an_id(cfg, plans):
    assert check("feat: x", cfg, plans, ["docs/plans/21-plan-traceability.md"]) == ["does not cite any task"]


@pytest.mark.parametrize("subject", [
    "Merge pull request #18 from someone/branch",
    "Merge remote-tracking branch 'origin/main' into feature",
    'Revert "feat: x (21/1.1)"',
    "fixup! feat: x",
])
def test_merges_and_reverts_are_exempt(cfg, plans, subject):
    assert check(subject, cfg, plans) == []


def test_comment_lines_do_not_count(cfg, plans):
    assert check("feat: x\n# (21/1.1) written by git\n", cfg, plans) == ["does not cite any task"]


def test_spanish_messages(cfg, plans):
    cfg.language = "es"
    assert check("feat: x", cfg, plans) == ["no cita ninguna tarea"]


def test_custom_task_id_pattern(tmp_path):
    plans_dir = tmp_path / "plans"
    plans_dir.mkdir()
    (plans_dir / "3-plan-billing.md").write_text(TABLE + "| B-12 | a | b | todo |\n", encoding="utf-8")
    cfg = Config(root=str(tmp_path), plans_dir="plans", task_id_pattern=r"[A-Z]-\d+")
    plans = load_plans(cfg)
    assert check_message("feat: x (3/B-12)", CODE, plans, cfg) == []
    assert check_message("feat: x (3/B-13)", CODE, plans, cfg) == ["3/B-13: plan 3-billing has no task B-13"]
