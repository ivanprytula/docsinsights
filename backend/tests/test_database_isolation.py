from app.core.db import engine


def test_suite_runs_against_the_throwaway_test_database() -> None:
    assert engine.url.database == "test"
    assert engine.url.username == "test"
