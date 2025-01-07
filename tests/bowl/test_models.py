from pinsdb.bowl.models import Game

import pytest


class TestModels:
    @pytest.mark.parametrize(
        "throws,expected_pins,expected_score",
        [
            ([], 0, 0),
            ([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 0, 0),
            ([10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10], 120, 300),
        ],
    )
    def test_game(self, throws, expected_pins, expected_score) -> None:
        """Assert game functions as expected, specifically initialization and scoring."""
        game = Game(throws=throws)
        total_pins = game.score_pins()
        total_score = game.score_game()
        assert isinstance(total_pins, int)
        assert isinstance(total_score, int)
        assert total_pins == expected_pins
        assert total_score == expected_score
        assert total_pins <= total_score
