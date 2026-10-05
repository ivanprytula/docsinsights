import random
from collections.abc import Callable

Metric = Callable[[list[int | None]], float]


def recall_at_k(ranks: list[int | None], k: int) -> float:
    """Fraction of questions whose first relevant hit ranks within the top k."""
    if not ranks:
        return 0.0
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks)


def mean_reciprocal_rank(ranks: list[int | None]) -> float:
    """Average of 1/rank of the first relevant hit; 0 for questions with none."""
    if not ranks:
        return 0.0
    return sum(1 / r for r in ranks if r is not None) / len(ranks)


def bootstrap_interval(
    ranks: list[int | None],
    metric: Metric,
    *,
    resamples: int = 1000,
    confidence: float = 0.95,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap interval: resample questions with replacement, re-score.

    Seeded so the same ranks always give the same interval.
    """
    if not ranks:
        return (0.0, 0.0)
    rng = random.Random(seed)
    scores = sorted(metric(rng.choices(ranks, k=len(ranks))) for _ in range(resamples))
    tail = (1 - confidence) / 2
    return (scores[int(tail * resamples)], scores[int((1 - tail) * resamples) - 1])
