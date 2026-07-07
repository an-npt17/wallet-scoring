"""Narrows polars' broad aggregate return types (PythonLiteral | None) to concrete
int/float. polars types Series.mean()/sum()/max()/quantile() etc. generically
over all dtypes it supports (including date/Decimal/timedelta), so basedpyright
sees a wide union even when the column is known to be numeric. Every call site
that uses these helpers operates on a Float64/Int64 column, so the cast is safe.
"""

import typing


def as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    return float(typing.cast(float, value))


def as_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    return int(typing.cast(int, value))
