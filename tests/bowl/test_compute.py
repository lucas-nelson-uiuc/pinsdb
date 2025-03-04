import pytest
from pinsdb.namespace.compute import score_game


class TestCompute:
    @pytest.mark.parametrize(
        "throws,total_score",
        [
            ([0] * 10, 0),
            ([10] * 12, 300),
            ([0] * 18 + [10] * 3, 30),
            ([9, 1, 10, 10, 10, 10, 10, 10, 7, 0, 9, 0, 10, 10, 9], 229),
        ],
    )
    def test_compute(self, throws: list[int], total_score: int):
        """Validate scoring mechanism is accurate."""
        assert score_game(throws) == total_score
