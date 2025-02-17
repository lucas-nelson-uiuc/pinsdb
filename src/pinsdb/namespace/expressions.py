import polars as pl

from pinsdb.namespace.compute import construct_frames, score_game
from pinsdb.constants import TOTAL_FRAME_PINS


@pl.api.register_expr_namespace("bowling")
class Bowling:
    def __init__(self, expr: pl.Expr) -> None:
        self._expr = expr

    def is_strike(self) -> pl.Expr:
        """Detect if frame is a strike."""
        return (self._expr.list.first() == TOTAL_FRAME_PINS).alias("is_strike")
    
    def is_spare(self) -> pl.Expr:
        """Detect if frame is a spare."""
        return (self.is_strike().not_() & (self._expr.list.sum() == TOTAL_FRAME_PINS)).alias("is_spare")
    
    def is_wombat(self) -> pl.Expr:
        """Detect if frame is a wombat."""
        return (self.is_strike().not_() & (self._expr.list.last() == TOTAL_FRAME_PINS)).alias("is_wombat")

    def construct_frames(self) -> pl.Expr:
        """Construct frames from sequence of throws."""
        return self._expr.map_elements(construct_frames, return_dtype=pl.List(pl.List(pl.Int8))).alias("frames")

    def compute_score(self) -> pl.Expr:
        """Calculate score given a list of throws."""
        return self._expr.map_elements(score_game, return_dtype=pl.Int64).alias("score")
    
    def compute_pins(self) -> pl.Expr:
        """Calculate number of pins given a list of throws."""
        return self._expr.list.sum().alias("pins")
