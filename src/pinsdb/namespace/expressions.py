from typing import Literal
import polars as pl

from pinsdb.namespace.compute import construct_frames, score_game
from pinsdb.constants import TOTAL_FRAME_PINS


@pl.api.register_expr_namespace("bowling")
class Bowling:
    def __init__(self, expr: pl.Expr) -> None:
        self._expr = expr

    def is_gutter(self) -> pl.Expr:
        """Detect if frame is empty."""
        expression = (self._expr.list.sum()) == 0
        return expression.alias("is_gutter")

    def is_strike(self) -> pl.Expr:
        """Detect if frame is a strike."""
        expression = self._expr.list.first() == TOTAL_FRAME_PINS
        return expression.alias("is_strike")

    def is_spare(self) -> pl.Expr:
        """Detect if frame is a spare."""
        expression = self.is_strike().not_() & (
            self._expr.list.sum() == TOTAL_FRAME_PINS
        )
        return expression.alias("is_spare")

    def is_wombat(self) -> pl.Expr:
        """Detect if frame is a wombat."""
        expression = self.is_strike().not_() & (
            self._expr.list.last() == TOTAL_FRAME_PINS
        )
        return expression.alias("is_wombat")

    def get_throw(self, throw: Literal["first", "second", "last"] = "first") -> pl.Expr:
        match throw:
            case "first":
                throw = 0
            case "second":
                throw = 1
            case "last":
                throw = -1
        expression = self._expr.list.get(throw)
        return expression.alias(f"{throw}_throw")

    def construct_frames(self) -> pl.Expr:
        """Construct frames from sequence of throws."""
        expression = self._expr.map_elements(
            construct_frames, return_dtype=pl.List(pl.List(pl.Int8))
        )
        return expression.alias("frames")

    def compute_score(self) -> pl.Expr:
        """Calculate score given a list of throws."""
        expression = self._expr.map_elements(score_game, return_dtype=pl.Int64)
        return expression.alias("score")

    def compute_pins(self) -> pl.Expr:
        """Calculate number of pins given a list of throws."""
        expression = self._expr.list.sum()
        return expression.alias("pins")
