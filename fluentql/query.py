from enum import Enum
from types import FunctionType

from .errors import QueryBuilderError
from .function import F, OrderF, Asc, BitwiseAnd, BitwiseOr, Star
from .types import Column


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
    JOIN = "join"
    HAVING = "having"


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
        self._using = None
        self._where = None
        self._group_by = None
        self._having = None
        self._order = None
        self._union = None
        self._union_order = None

        # Options
        self._options = {}

    def compile(self, dialect_cls, **user_options):
        """
        Compiles the query using a given dialect type.

        Args:
            dialect_cls (type): Implementation of BaseDialect
            **user_options: Options to be passed to the dialect constructor

        Returns:
            str
        """
        # If we have more than one target, we should use absolute names for
        # column references
        options = {"use_absolute_names_for_columns": len(self._target) > 1}

        # User options should override the settings defined here
        dialect_options = {**options, **user_options}

        dialect = dialect_cls(**dialect_options)

        return dialect.compile(self)

    @classmethod
    def select(cls, *columns):
        """
        Initialise a select query with a list of columns.

        Args:
            *columns (Column|F): Columns
                to select. Each element can either be a Column or an instance of F.
                Defaults to None, which means all columns are selected.

        Returns:
            Query instance
        """
        query = cls(QueryCommands.SELECT)

        # Validate columns argument
        assert all(
            isinstance(c, (Column, F)) for c in columns
        ), "Invalid argument for columns"

        if len(columns):
            query._select = columns
        else:
            query._select = [Star()]

        return query

    def from_(self, target):
        """
        Set main target for the query. The list of targets must be empty.

        Args:
            target (Table): Query target

        Returns:
            Query self
        """
        if len(self._target) > 0:
            raise QueryBuilderError("Query target already set")

        self._target.append(target)

        return self

    def set_from(self, target):
        """
        Alias for from_(target).

        Args:
            target (Table): Query target

        Returns:
            Query self
        """
        return self.from_(target)

    def where(self, condition, boolean=BitwiseAnd):
        """
        Add a where clause to a query.

        Args:
            condition (F|callable):
                - The default implementation is when an F is given, for
                operations using built in functions.
                - If a callable is given, it should take a query object as its
                first positional argument, and it assumes that the user wants to
                build a nested where clause group.
            boolean (And|Or): Boolean operator between the previous where clause and
                this where clause. Defaults to And.
        Returns:
            Query self
        """
        if isinstance(condition, FunctionType):
            where_subquery = self._sub_query(QueryCommands.WHERE)
            # Inherit targets
            where_subquery._target = list(self._target)

            # Call user function, which may or may not return a Query
            # but that doesn't matter as we expect the given query
            # object to be mutated
            condition(where_subquery)

            condition = where_subquery._where

        if self._where is None:
            self._where = condition
        else:
            # Set last where clause's boolean
            self._where = boolean(self._where, condition)

        return self

    def and_where(self, condition):
        """
        Alias for where(condition, boolean=And). Equivalent to a generic where
        call, but more explicit.

        condition (F|callable):
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
        return self.where(condition, BitwiseAnd)

    def or_where(self, condition):
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
        return self.where(condition, BitwiseOr)

    def join(self, target, on, how="inner"):
        """
        Add a join clause to a query.

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

        join_query = self._sub_query(QueryCommands.JOIN)
        join_query._target = list(self._target)

        if on is None:
            how = "cross"
        else:
            # Call user function
            on(join_query)

        # Set type of join in on query
        join_query.set_option("join_type", how)

        if self._join is None:
            self._join = []

        self._join.append(join_query)

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

    def on(self, condition, boolean=BitwiseAnd):
        """
        On clause for a join. Only available for ON command subqueries.

        Args:
            left (Column|F|callable|object): Left hand side of the boolean
                expression. Can be a Column, a Function or a constant.
            op (str): Operator to use.
            right (Column|F|object): Right hand side of the boolean expression.
                Can be a Column, a Function or a constant.

        Returns:
            Query self
        """
        if self._command not in (QueryCommands.JOIN, QueryCommands.ON):
            raise QueryBuilderError(
                ".on should be called only in JOIN or OR subqueries"
            )

        if isinstance(condition, FunctionType):
            on_subquery = self._sub_query(QueryCommands.ON)

            # Inherit targets
            on_subquery._target = list(self._target)

            # Call the user function
            condition(on_subquery)

            condition = on_subquery._on

        if self._on is None:
            self._on = condition
        else:
            self._on = boolean(self._on, condition)

        return self

    def and_on(self, condition):
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
        return self.on(condition, boolean=BitwiseAnd)

    def or_on(self, condition):
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
        return self.on(condition, boolean=BitwiseOr)

    def using(self, column_name):
        """
        Using clause for a join. Can only be used in a Join sub-query if.

        .on has not been used

        Args:
            column_name (str): Column name to use for the join

        Returns:
            Query self
        """
        if self._command is not QueryCommands.JOIN:
            raise QueryBuilderError(".using can only be used on a JOIN query")

        if self._using is not None:
            raise QueryBuilderError(".using can only be used once for a join")

        if self._on is not None:
            raise QueryBuilderError(
                ".using can only be used if an on clause was not defined for the join"
            )

        # TODO: Validate that the column actually exists
        self._using = column_name

        return self

    def group_by(self, *columns):
        """
        Issue a Group By on a Select statement.

        Args:
            *columns (Column): Columns to group by, in that order

        Returns:
            Query self
        """
        if self._command is not QueryCommands.SELECT:
            raise QueryBuilderError("group_by can only be used with select statements")

        if len(columns) == 0:
            raise QueryBuilderError(
                "group_by requires at least a target column, none provided"
            )

        if not all(isinstance(column, Column) for column in columns):
            raise QueryBuilderError("group_by can only be used on Columns")

        # TODO: If a group by clause is set, then the selected columns must either be
        # in the group by list, or aggregated. We must check the select list for
        # target columns, as well as the list of target tables.
        # Star() and TableStar() make it a bit more complicated, as for untyped
        # tables we don't really know what's in them. Therefore, for untyped tables,
        # if there is potential for the validation to fail, we raise a warning, whereas
        # for types tables we raise an Error

        self._group_by = columns

        return self

    def having(self, condition, boolean=BitwiseAnd):
        """
        Having clause for a select query.

        Args:
            condition (F|Callable): 
            boolean (F):

        Returns:
            Query self
        """
        if isinstance(condition, FunctionType):
            having_subquery = self._sub_query(QueryCommands.HAVING)
            # Inherit targets
            having_subquery._target = list(self._target)

            # Call user function, which may or may not return a Query
            # but that doesn't matter as we expect the given query
            # object to be mutated
            condition(having_subquery)

            condition = having_subquery._having

        if self._having is None:
            self._having = condition
        else:
            # Set last where clause's boolean
            self._having = boolean(self._having, condition)

        return self

    def and_having(self, condition):
        """
        Shorthand for having(condition, boolean=BitwiseAnd)

        Args:
            condition (F|Callable):
        
        Returns:
            Query self
        """
        return self.having(condition, BitwiseAnd)

    def or_having(self, condition):
        """
        Shorthand for having(condition, boolean=BitwiseOr)

        Args:
            condition (F|Callable):
        
        Returns:
            Query self
        """
        return self.having(condition, BitwiseOr)

    def order_by(self, *criteria):
        """
        Adds an order by clause to a select statement

        Args:
            criteria (tuple(Column|OrderF)): Criteria to apply. If
                a Column is passed, ascending order is assumed.
        
        Returns:
            Query self
        """
        if self._command is not QueryCommands.SELECT:
            raise QueryBuilderError("order_by can only be used with select statements")

        if any(not isinstance(c, (Column, OrderF)) for c in criteria):
            raise QueryBuilderError(
                "Only Column or OrderF objects should be passed to sort()"
            )

        self._order = [Asc(c) if isinstance(c, Column) else c for c in criteria]

        return self

    def fetch(self, n_rows):
        """
        Limit the number of results to n_rows. The actual clause
        depends on dialect.

        Args:
            n_rows (int): Number of rows
        
        Returns:
            Query self
        """
        self.set_option("fetch", n_rows)

        return self

    def skip(self, n_rows):
        """
        Skip n_rows rows from the result and return the rest. The actual
        clause depends on dialect and not all SQL implementations support
        this.

        Args:
            n_rows (int): Number of rows
        
        Returns:
            Query self
        """
        self.set_option("skip", n_rows)

        return self

    def distinct(self):
        """
        Distinct clause for select statement.

        Returns:
            Query self
        """
        self.set_option("distinct", True)

        return self

    def set_option(self, key, value):
        """
        Set an option by key.

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
        Gets the value of an option. If the option is not configured, a
        KeyError is raised.

        Args:
            key (str):

        Returns:
            object
        """
        return self._options[key]

    def _sub_query(self, command):
        """
        Return a new Query of a given command, to be used as a subquery.

        Args:
            command (QueryCommands):

        Returns:
            Query
        """
        return type(self)(command)
