from enum import Enum
from types import FunctionType

from .errors import QueryBuilderError
from .function import F
from .table import Column


class QueryCommands(Enum):
    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    DROP = "drop"

    # Specific types for nested queries
    WHERE = "where"
    ON = "on"


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


class BooleanClause:
    def __init__(self, boolean=None):
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


class SimpleBooleanClause(BooleanClause):
    def __init__(self, left, op=None, right=None, boolean=None):
        """
        Args:
            left (str|F|Query):
            op (str): Defaults to None
            right (object): Defaults to None
            boolean (str): Defaults to None
        """
        super().__init__(boolean)

        self._left = left
        self._op = op
        self._right = right


class GroupBooleanClause(BooleanClause):
    def __init__(self, group, boolean=None):
        """
        Args:
            group (Query):
            boolean (str): Defaults to None
        """
        super().__init__(boolean)

        self._group = group


class Query:
    def __init__(self, command):
        """
        Args:
            command (QueryCommands): Query command type
        """
        # Initialise query command
        self._command = command

        # Initialise query sections
        self._target = []
        self._create = None
        self._update = None
        self._delete = None
        self._drop = None
        self._select = None
        self._join = None
        self._on = None
        self._where = None
        self._group_by = None
        self._having = None
        self._order = None
        self._union = None
        self._union_order = None

        # Options
        self._options = {}

    @classmethod
    def select(cls, columns=None):
        """
        Initialise a select query with a list of columns.

        Args:
            columns (list(Column|F|tuple(Column, str))): Iterable of column names
                to select. Each element can either be a Column, an instance of F, 
                or a 2-tuple where the first element is a Column object and the second
                is an alias, as a str. Defaults to None, which means all columns are
                selected.

        Returns:
            Query instance
        """
        query = cls(QueryCommands.SELECT)

        if columns is None:
            columns = []
        else:
            # Validate columns argument
            assert all(
                isinstance(c, (Column, F))
                or (len(c) == 2 and isinstance(c[0], Column) and isinstance(c[1], str))
                for c in columns
            ), "Invalid argument for columns"

        query._select = tuple(columns)

        return query

    def from_(self, target):
        """
        Set main target for the query. The list of targets must
        be empty.

        Args:
            target (Table): Query target
        
        Returns:
            Query self
        """
        if len(self._target) > 0:
            raise QueryBuilderError("Query target already set")

        self._target.append(target)

        return self

    def where(self, column, op=None, value=None, boolean="and"):
        """
        Add a where clause to a query.

        Args:
            column (Column|F|callable):
                - If a Column object is given, the name and bound table
                will be used, and op and value are also required.
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
        if isinstance(column, (Column, F)):
            assert op is not None and value is not None, "Op and value cannot be None"

            where_clause = SimpleBooleanClause(column, op, value)

        elif isinstance(column, FunctionType):
            where_group = self._sub_query(QueryCommands.WHERE)
            # Inherit targets
            where_group._target = list(self._target)

            # Call user function, which may or may not return a Query
            # but that doesn't matter as we expect the given query
            # object to be mutated
            column(where_group)

            where_clause = GroupBooleanClause(where_group)

        else:
            raise QueryBuilderError(f"Unknown argument type for column: {type(column)}")

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

        column (Column|F|callable):
            - If a Column object is given, the name and bound table
            will be used, and op and value are also required.
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

        column (Column|F|callable):
            - If a Column object is given, the name and bound table
            will be used, and op and value are also required.
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

    def join(self, target, on, how="inner"):
        """
        Add a join clause to a query

        Args:
            target (Table):
            on (None|FunctionType): A callable that takes a query object
                as its first positional argument, allowing the user to use
                on, and_on and or_on methods. If None is given, the join will
                be treated as a cross join irrespective of the value of how.
            how (str): Join type

        Returns:
            Query self
        """
        # Add target to query
        self._target.append(target)

        on_query = self._sub_query(QueryCommands.ON)
        on_query._target = list(self._target)

        if on is None:
            how = "cross"
        else:
            # Call user function
            on(on_query)

        # Set type of join in on query
        on_query.set_option("join_type", how)

        if self._join is None:
            self._join = []
        self._join.append(on_query)

        return self

    def left_join(self, target, on):
        """
        Alias for join(target, on, how="left")

        Args:
            target (Table):
            on (FunctionType): A callable that takes a query object
                as its first positional argument, allowing the user to use
                on, and_on and or_on methods.

        Returns:
            Query self
        """
        return self.join(target, on, how="left")

    def right_join(self, target, on):
        """
        Alias for join(target, on, how="right")

        Args:
            target (Table):
            on (FunctionType): A callable that takes a query object
                as its first positional argument, allowing the user to use
                on, and_on and or_on methods.

        Returns:
            Query self
        """
        return self.join(target, on, how="right")

    def inner_join(self, target, on):
        """
        Alias for join(target, on, how="inner")

        Args:
            target (Table):
            on (FunctionType): A callable that takes a query object
                as its first positional argument, allowing the user to use
                on, and_on and or_on methods.

        Returns:
            Query self
        """
        return self.join(target, on, how="inner")

    def outer_join(self, target, on):
        """
        Alias for join(target, on, how="outer")

        Args:
            target (Table):
            on (FunctionType): A callable that takes a query object
                as its first positional argument, allowing the user to use
                on, and_on and or_on methods.

        Returns:
            Query self
        """
        return self.join(target, on, how="outer")

    def cross_join(self, target):
        """
        Alias for join(target, None, how="cross")

        Args:
            target (Table):
        
        Returns:
            Query self
        """
        return self.join(target, None, how="cross")

    def on(self, left, op=None, right=None, boolean="and"):
        """
        On clause for a join. Only available for ON command
        subqueries.

        Args:
            left (Column|F|callable|object): Left hand side of the boolean
                expression. Can be a Column, a Function or a constant.
            op (str): Operator to use.
            right (Column|F|object): Right hand side of the boolean expression.
                Can be a Column, a Function or a constant.
        
        Returns:
            Query self
        """
        if self._command is not QueryCommands.ON:
            raise QueryBuilderError(".on should be called only in ON subqueries")

        if isinstance(left, FunctionType):
            on_group = self._sub_query(QueryCommands.ON)

            # Inherit targets
            on_group._target = list(self._target)

            # Call the user function
            left(on_group)

            on_clause = GroupBooleanClause(on_group)

        else:
            assert op is not None and right is not None, "Op and value cannot be None"
            on_clause = SimpleBooleanClause(left, op, right)

        if self._on is None:
            self._on = []
        else:
            # Set last on clause's boolean
            self._on[-1].boolean = boolean

        self._on.append(on_clause)

        return self

    def and_on(self, left, op=None, right=None):
        """
        Alias for on(left, op, right, boolean="and")

        Args:
            left (Column|F|callable|object): Left hand side of the boolean
                expression. Can be a Column, a Function or a constant.
            op (str): Operator to use.
            right (Column|F|object): Right hand side of the boolean expression.
                Can be a Column, a Function or a constant.
        
        Returns:
            Query self
        """
        return self.on(left, op, right, boolean="and")

    def or_on(self, left, op=None, right=None):
        """
        Alias for on(left, op, right, boolean="or")

        Args:
            left (Column|F|callable|object): Left hand side of the boolean
                expression. Can be a Column, a Function or a constant.
            op (str): Operator to use.
            right (Column|F|object): Right hand side of the boolean expression.
                Can be a Column, a Function or a constant.
        
        Returns:
            Query self
        """
        return self.on(left, op, right, boolean="or")

    def set_option(self, key, value):
        """
        Set an option by key

        Args:
            key (str):
            value (object):
        """
        self._options[key] = value

    def has_option(self, key):
        """
        Checks whether a given option is configured.

        Args:
            key (str):
        
        Returns:
            bool
        """
        return key in self._options

    def get_option(self, key):
        """
        Gets the value of an option. If the option is not configured,
        a KeyError is raised.

        Args:
            key (str):
        
        Returns:
            object
        """
        return self._options[key]

    def _sub_query(self, command):
        """
        Return a new Query of a given command, to be used as a
        subquery.

        Args:
            command (QueryCommands):

        Returns:
            Query
        """
        return type(self)(command)
