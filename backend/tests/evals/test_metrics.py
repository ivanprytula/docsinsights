import pytest

from evals.metrics import bootstrap_interval, mean_reciprocal_rank, recall_at_k


def test_recall_at_k_counts_questions_answered_within_k() -> None:
    ranks = [1, 3, None, 5]

    assert recall_at_k(ranks, 1) == 0.25
    assert recall_at_k(ranks, 3) == 0.5
    assert recall_at_k(ranks, 5) == 0.75


def test_recall_at_k_of_no_questions_is_zero() -> None:
    assert recall_at_k([], 3) == 0.0


def test_mean_reciprocal_rank_weights_earlier_hits_higher() -> None:
    assert mean_reciprocal_rank([1, 2, None]) == pytest.approx((1 + 0.5 + 0) / 3)


def test_mean_reciprocal_rank_of_no_questions_is_zero() -> None:
    assert mean_reciprocal_rank([]) == 0.0


def test_bootstrap_interval_of_identical_outcomes_has_no_spread() -> None:
    low, high = bootstrap_interval([1] * 10, lambda r: recall_at_k(r, 1))

    assert (low, high) == (1.0, 1.0)


def test_bootstrap_interval_brackets_the_observed_score() -> None:
    ranks = [1, 1, 1, None, None, 3, 2, None, 1, 5]

    low, high = bootstrap_interval(ranks, lambda r: recall_at_k(r, 3))

    assert low <= recall_at_k(ranks, 3) <= high
    assert low < high


def test_bootstrap_interval_is_wider_for_fewer_questions() -> None:
    def width(ranks: list[int | None]) -> float:
        low, high = bootstrap_interval(ranks, lambda r: recall_at_k(r, 1))
        return high - low

    assert width([1, None] * 5) > width([1, None] * 50)


def test_bootstrap_interval_is_reproducible() -> None:
    ranks = [1, None, 2, 1, None, 4]

    assert bootstrap_interval(ranks, lambda r: recall_at_k(r, 1)) == (
        bootstrap_interval(ranks, lambda r: recall_at_k(r, 1))
    )


def test_bootstrap_interval_of_no_questions_is_zero() -> None:
    assert bootstrap_interval([], lambda r: recall_at_k(r, 1)) == (0.0, 0.0)
