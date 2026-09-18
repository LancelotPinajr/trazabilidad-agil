from trazabilidad.config import Config
from trazabilidad.migrations import repeated_numbers, touched_migrations

DB = "db/migrations"
OTHER = "services/billing/migrations"
CFG = Config(root=".", migration_dirs=[DB, OTHER])


def test_no_repeats():
    assert repeated_numbers([f"{DB}/048_a.sql", f"{DB}/049_b.sql"], CFG) == []


def test_two_branches_creating_the_same_number():
    assert repeated_numbers([f"{DB}/042_x.sql", f"{DB}/042_y.sql"], CFG) == [
        f"{DB}: number 042 is used by 042_x.sql, 042_y.sql"]


def test_each_folder_numbers_on_its_own():
    assert repeated_numbers([f"{DB}/001_init.sql", f"{OTHER}/001_init.sql"], CFG) == []


def test_new_migration_is_allowed():
    assert touched_migrations([("A", f"{DB}/050_new.sql")], CFG) == []


def test_editing_or_removing_an_existing_one_is_not():
    problems = touched_migrations([("M", f"{DB}/048_a.sql"), ("D", f"{DB}/042_x.sql")], CFG)
    assert problems == [f"{DB}/048_a.sql: edited; write a new migration instead",
                        f"{DB}/042_x.sql: deleted or renamed; write a new migration instead"]


def test_files_outside_the_configured_folders_do_not_matter():
    assert touched_migrations([("M", "src/app.py"), ("D", "other/migrations/001_x.sql")], CFG) == []
