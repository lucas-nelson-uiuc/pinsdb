from enum import Enum
from pathlib import Path


DATABASE_SOURCE = Path(".data")


class DATABASE_ENGINE(Enum):
    POLARS = "polars"
    PANDAS = "pandas"
    DUCKDB = "duckdb"
