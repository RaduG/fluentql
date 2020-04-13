import pytest

from fluentql.dialects.generic import GenericSQLDialect
from fluentql.errors import CompilationError, QueryBuilderError
from fluentql.query import Query as Q
from fluentql.types import Table


@pytest.fixture
def dialect_cls():
    return GenericSQLDialect


@pytest.fixture
def table_a():
    return Table("table_a")


@pytest.fixture
def table_b():
    return Table("table_b")


# Table for parametrized tests
test_table = Table("test_table")


def test_empty_select_query_raises_compile_error(table_a, dialect_cls):
    with pytest.raises(CompilationError):
        # This should raise a CompilationError
        Q.select().compile(dialect_cls)


def test_select_star(table_a, dialect_cls):
    q = Q.select().from_(table_a).compile(dialect_cls)

    assert q == "select * from table_a;"


def test_select_table_star(table_a, dialect_cls):
    q = Q.select(table_a.all()).from_(table_a).compile(dialect_cls)

    assert q == "select table_a.* from table_a;"


def test_column_selection(table_a, dialect_cls):
    q = Q.select(table_a["col1"], table_a["col2"]).from_(table_a).compile(dialect_cls)

    assert q == "select col1, col2 from table_a;"


def test_column_selection_alias(table_a, dialect_cls):
    q = (
        Q.select(table_a["col1"].alias("col1_alias"))
        .from_(table_a)
        .compile(dialect_cls)
    )

    assert q == "select col1 as col1_alias from table_a;"


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (
            Q.select().from_(test_table).where(test_table["col1"] == 120),
            "select * from test_table where col1 = 120;",
        ),
        (
            Q.select().from_(test_table).where(120 == test_table["col1"]),
            "select * from test_table where col1 = 120;",
        ),
        (
            Q.select().from_(test_table).where(test_table["col1"].like("%abc")),
            "select * from test_table where col1 like '%abc';",
        ),
        (
            Q.select().from_(test_table).where(test_table["col1"] < test_table["col2"]),
            "select * from test_table where col1 < col2;",
        ),
        (
            Q.select().from_(test_table).where(1 == 1),
            "select * from test_table where true;",
        ),
    ],
)
def test_simple_where_query(q, expected, dialect_cls):
    assert q.compile(dialect_cls) == expected


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"] < 20)
            .and_where(test_table["col2"] == True),
            "select * from test_table where col1 < 20 and col2 = true;",
        ),
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"] < 20)
            .or_where(test_table["col2"] == False),
            "select * from test_table where col1 < 20 or col2 = false;",
        ),
        (
            Q.select()
            .from_(test_table)
            .where(test_table["col1"] == "v")
            .and_where(test_table["col2"] < test_table["col3"])
            .or_where(20 > test_table["col5"]),
            "select * from test_table where col1 = 'v' and col2 < col3 or col5 < 20;",
        ),
    ],
)
def test_compound_where_query(q, expected, dialect_cls):
    assert q.compile(dialect_cls) == expected


@pytest.mark.parametrize(
    ["q", "expected"],
    [
        (
            Q.select()
            .from_(test_table)
            .where(1 == 1)
            .and_where(
                lambda q: q.where(test_table["col1"] == 7).or_where(
                    test_table["col3"] == test_table["col4"]
                )
            ),
            "select * from test_table where true and (col1 = 7 or col3 = col4);",
        )
    ],
)
def test_complex_where_query(q, expected, dialect_cls):
    assert q.compile(dialect_cls) == expected
