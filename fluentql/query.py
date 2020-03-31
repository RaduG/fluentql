from enum import Enum
from types import FunctionType

from .errors import QueryBuilderError
from .function import F


class QueryTypes(Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    DROP = "drop"

    # Specific types for nested queries
    WHERE = "where"


class Operators:
    EQ = "="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="
    NE = "<>"
    NSEQ = "<=>"
    LIKE = "like"
    LIKE_BIN = "like binary"
    NOT_LIKE = "not like"
    ILIKE = "ilike"
    BIN_AND = "&"
    BIN_OR = "|"
    BIN_XOR = "^"
    RLIKE = "rlike"
    NOT_RLIKE = "not rlike"
    REGEXP = "regexp"
    NOT_REGEXP = "not regexp"


class WhereClause:
    def __init__(self, column, op=None, value=None, boolean=None):
        """
        Args:
            boolean (str): Defaults to None
        """
        self._boolean = boolean

    @property
    def boolean(self):
        """
        Returns:
            str
        """
        return self._boolean

    @boolean.setter
    def boolean(self, value):
        """
        Args:
            value (str):
        """
        self._boolean = value


class SimpleWhereClause(WhereClause):
    def __init__(self, column, op=None, value=None, boolean=None):
        """
        Args:
            column (str|F|Query):
            op (str): Defaults to None
            value (object): Defaults to None
            boolean (str): Defaults to None
        """
        super().__init__(boolean)

        self._column = column
        self._op = op
        self._value = value


class GroupWhereClause(WhereClause):
    def __init__(self, group, boolean=None):
        """
        Args:
            group (Query):
            boolean (str): Defaults to None
        """
        super().__init__(boolean)

        self._group = group


class InheritedTarget:
    pass


class Query:
    def __init__(self, target):
        """
        Args:
            target (object): Main target of the query
        """
        self._target = target

        # Initialise query type
        self._type = None

        # Initialise query sections
        self._create = None
        self._update = None
        self._delete = None
        self._drop = None
        self._select = None
        # self._from = None -- this should be target
        self._join = None
        self._where = None
        self._group_by = None
        self._having = None
        self._order = None
        self._union = None
        self._union_order = None

        # Options
        self._options = {}

    def select(self, columns=("*",)):
        """
        Initialise a select query with a list of columns.

        Args:
            columns (list(str|F|tuple(str, str))): Iterable of column names
                to select. Each element can either be a string, a F, or a 2-tuple
                where the first element is the original column name and the second
                is an alias. Defaults to ('*'), which means all columns will be
                selected.

        Returns:
            Query self
        """
        if self._type is not None:
            raise QueryBuilderError(
                "Select columns already defined or select clause not compatible with statement."
            )
        if self._select is not None:
            raise QueryBuilderError("Select columns already defined")

        # Validate columns argument
        assert all(
            isinstance(c, (str, F))
            or (len(c) == 2 and isinstance(c[0], str) and isinstance(c[1], str))
            for c in columns
        ), "Invalid argument for columns"

        self._type = QueryTypes.SELECT
        self._select = tuple(columns)

        return self

    def where(self, column, op=None, value=None, boolean="and"):
        """
        Add a where clause to a query.

        Args:
            column (str|F|callable):
                - If a str is given, it should contain the name of the column
                to compare and op and value are also required.
                - If a F is given, the transformation is to be applied
                as defined in the F itself, and op and value are
                also required.
                - If a callable is given, it should take a query object as its
                first positional argument, and it assumes that the user wants to
                build a nested where clause group.
            op (str): Operator to use. Required if column is a str or a F.
                Defaults to None.
            value (object): Value to compare against. If a Query object is given,
                that query will be treated as a sub-query. Otherwise, it can be
                any object that can be formatted to a string. The dialect used to
                construct the query may contain specific implementations of string
                formatting for specific types, such as datetime objects.
            boolean (str): Boolean operator between the previous where clause and
                this where clause. Defaults to "and".
        Returns:
            Query self
        """
        if isinstance(column, (str, F)):
            assert op is not None and value is not None, "Op and value cannot be None"

            where_clause = SimpleWhereClause(column, op, value)

        elif isinstance(column, FunctionType):
            where_group = self._sub_query(InheritedTarget)
            where_group._type = QueryTypes.WHERE

            # Call user function, which may or may not return a Query
            # but that doesn't matter as we expect the given query
            # object to be mutated
            column(where_group)

            where_clause = GroupWhereClause(where_group)

        if self._where is None:
            self._where = []
        else:
            # Set last where clause's boolean
            self._where[-1].boolean = boolean

        self._where.append(where_clause)

        return self

    def and_where(self, column, op=None, value=None):
        """
        Alias for where(column, op, value, boolean="and").

        column (str|F|callable):
            - If a str is given, it should contain the name of the column
            to compare and op and value are also required.
            - If a F is given, the transformation is to be applied
            as defined in the F itself, and op and value are
            also required.
            - If a callable is given, it should take a query object as its
            first positional argument, and it assumes that the user wants to
            build a nested where clause group.
        op (str): Operator to use. Required if column is a str or a F.
            Defaults to None.
        value (object): Value to compare against. Can be any object that can be
            formatted to a string. The dialect used to construct the query
            may contain specific implementations of string formatting for
            specific types, such as datetime objects.
        """
        return self.where(column, op, value, "and")

    def or_where(self, column, op=None, value=None):
        """
        Alias for where(column, op, value, boolean="or")

        column (str|F|callable):
            - If a str is given, it should contain the name of the column
            to compare and op and value are also required.
            - If a F is given, the transformation is to be applied
            as defined in the F itself, and op and value are
            also required.
            - If a callable is given, it should take a query object as its
            first positional argument, and it assumes that the user wants to
            build a nested where clause group.
        op (str): Operator to use. Required if column is a str or a F.
            Defaults to None.
        value (object): Value to compare against. Can be any object that can be
            formatted to a string. The dialect used to construct the query
            may contain specific implementations of string formatting for
            specific types, such as datetime objects.
        """
        return self.where(column, op, value, boolean="or")

    def _sub_query(self, target):
        """
        Return a new Query object bound to a given target.

        Args:
            target (object):

        Returns:
            Query
        """
        return type(self)(target)
