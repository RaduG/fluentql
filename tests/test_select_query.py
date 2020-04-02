import pytest

from fluentql.dialects.base import Dialect
from fluentql.errors import CompilationError, QueryBuilderError
from fluentql.query import Query as Q
from fluentql.table import Table


@pytest.fixture
def dialect():
    return Dialect(keywords_caps=False)


@pytest.fixture
def table_a():
    return Table("table_a")


@pytest.fixture
def table_b():
    return Table("table_b")


# Table for parametrized tests
test_table = Table("test_table")


def test_empty_select_query_raises_compile_error(table_a, dialect):
    with pytest.raises(CompilationError):
        q = Q.select()

        # This should raise a CompilationError
        dialect.compile(q)


def test_select_star(table_a, dialect):
    q = Q.select().from_(table_a)

    assert dialect.compile(q) == "select * from table_a;"


def test_select_table_star(table_a, dialect):
    q = Q.select(table_a.all()).from_(table_a)

    assert dialect.compile(q) == "select table_a.* from table_a;"


def test_column_selection(table_a, dialect):
    q = Q.select(table_a["col1"], table_a["col2"]).from_(table_a)

    assert dialect.compile(q) == "select table_a.col1, table_a.col2 from table_a;"


def test_column_selection_alias(table_a, dialect):
    q = Q.select((table_a["col1"], "col1_alias")).from_(table_a)

    assert dialect.compile(q) == "select table_a.col1 as col1_alias from table_a;"


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (
            Q.select().from_(test_table).where(test_table["col1"], "=", 120),
            "select * from test_table where test_table.col1 = 120;",
        ),
        (
            Q.select().from_(test_table).where(120, "=", test_table["col1"]),
            "select * from test_table where 120 = test_table.col1;",
        ),
        (
            Q.select().from_(test_table).where(test_table["col1"], "like", "%abc"),
            "select * from test_table where test_table.col1 like '%abc';",
        ),
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"], "<", test_table["col2"]),
            "select * from test_table where test_table.col1 < test_table.col2;",
        ),
        (
            Q.select().from_(test_table).where(1, "=", 1),
            "select * from test_table where 1 = 1;",
        ),
    ],
)
def test_simple_where_query(q, expected, dialect):
    assert dialect.compile(q) == expected


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"], "<", 20)
            .and_where(test_table["col2"], "is", True),
            "select * from test_table where test_table.col1 < 20 and test_table.col2 is True;",
        ),
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"], "<", 20)
            .or_where(test_table["col2"], "is", False),
            "select * from test_table where test_table.col1 < 20 or test_table.col2 is False;",
        ),
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"], "=", "v")
            .and_where(test_table["col2"], "<", test_table["col3"])
            .or_where(20, ">", test_table["col5"]),
            "select * from test_table where test_table.col1 = 'v' and test_table.col2 < test_table.col3 or 20 > test_table.col5;",
        ),
    ],
)
def test_compound_where_query(q, expected, dialect):
    assert dialect.compile(q) == expected


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (
            Q.select()
            .from_(test_table)
            .where(1, "=", 1)
            .and_where(
                lambda q: q.where(test_table["col1"], "=", 7).or_where(
                    test_table["col3"], "=", test_table["col4"]
                )
            ),
            "select * from test_table where 1 = 1 and (test_table.col1 = 7 or test_table.col3 = test_table.col4);",
        )
    ],
)
def test_complex_where_query(q, expected, dialect):
    assert dialect.compile(q) == expected
