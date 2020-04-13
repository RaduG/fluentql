import pytest

from fluentql.dialects.generic import GenericSQLDialect
from fluentql.query import Query as Q
from fluentql.types import Table


test_table = Table("test_table")


@pytest.fixture
def dialect_cls():
    return GenericSQLDialect


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (Q.delete().from_(test_table), "delete from test_table;"),
        (
            Q.delete().from_(test_table).where(test_table["col1"] > 100),
            "delete from test_table where col1 > 100;",
        ),
    ],
)
def test_delete_query(q, expected, dialect_cls):
    assert q.compile(dialect_cls) == expected
