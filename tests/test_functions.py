from typing import Any

import pytest

from fluentql import GenericSQLDialect, Table
from fluentql.function import (
    F,
    Add,
    Subtract,
    Multiply,
    Divide,
    Modulo,
    BitwiseAnd,
    BitwiseOr,
    BitwiseXor,
    Equals,
    NotEqual,
    LessThan,
    LessThanOrEqual,
    GreaterThan,
    GreaterThanOrEqual,
    Not,
    As,
    TableStar,
    Star,
    Like,
    In,
    Max,
    Min,
    Sum,
    Asc,
    Desc,
)
from fluentql.types import AnyColumn


col1 = AnyColumn("col1")
col2 = AnyColumn("col2")
table = Table("table")


class FakeFunction(F):
    a: Any
    b: Any
    c: Any
    returns: Any


@pytest.fixture
def dialect():
    return GenericSQLDialect()


@pytest.mark.parametrize(
    ["f", "expected"],
    [
        (Add(col1, 10), "col1 + 10"),
        (Subtract(col1, 100), "col1 - 100"),
        (Multiply(col1, 200), "col1 * 200"),
        (Divide(10, 100), "10 / 100"),
        (Modulo(col1, 2), "col1 % 2"),
        (BitwiseAnd(True, False), "true and false"),
        (BitwiseOr(False, True), "false or true"),
        (BitwiseXor(False, False), "false xor false"),
        (Equals(col1, col2), "col1 = col2"),
        (NotEqual(col1, col2), "col1 <> col2"),
        (LessThan(col1, col2), "col1 < col2"),
        (LessThanOrEqual(col1, col2), "col1 <= col2"),
        (GreaterThan(col1, 200), "col1 > 200"),
        (GreaterThanOrEqual(col1, col2 * 100), "col1 >= col2 * 100"),
        (Not(col1 > 10), "not (col1 > 10)"),
        (As(col1, "alias"), "col1 as alias"),
        (TableStar(table), "table.*"),
        (Star(), "*"),
        (Like(col1, "%abc%"), "col1 like '%abc%'"),
        (In(col1, col2), "col1 in (col2)"),
        (Max(col1), "max(col1)"),
        (Min(col1), "min(col1)"),
        (Sum(col1), "sum(col1)"),
        (Asc(col1), "col1 asc"),
        (Desc(col1), "col1 desc"),
        (FakeFunction(1, 2, 3), "fakefunction(1, 2, 3)"),
    ],
)
def test_function_compiles_correctly(f, expected, dialect):
    assert dialect.dispatch(f) == expected
