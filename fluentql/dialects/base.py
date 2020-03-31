from ..function import F
from ..query import Query, SimpleWhereClause, GroupWhereClause
from ..errors import CompilationError


class Keywords:
    SELECT = "select"
    FROM = "from"
    AS = "as"
    WHERE = "where"
    ALL = "*"
    LIST_SEPARATOR = ","
    AND = "and"
    OR = "or"
    QUERY_END = ";"


class Dialect:
    keywords = Keywords

    def compile(self, query, terminal_query=True):
        """
        Compile a given query

        Args:
            query (Query):
            terminal_query (bool): Specified whether this is a top-level
                query, which means it has to end with the QUERY_END char.
                Defaults to True.
        
        Returns:
            str
        """
        query_type = query._type.value
        compiled_query = getattr(self, f"compile_{query_type}")(query)

        if terminal_query:
            compiled_query = f"{compiled_query}{self.keywords.QUERY_END}"

        return compiled_query

    def compile_select(self, query):
        """
        Compile a select query

        Args:
            query (Query):
        
        Returns:
            str
        """
        columns = self.compile_target_columns(query._select)
        where = None
        from_ = self.compile_from(query._target)

        # Compile Where if it exists
        if query._where is not None:
            where = self.compile_where(query._where)

        return f"{self.keywords.SELECT} {columns} {from_} {where}"

    def compile_target_columns(self, columns):
        """
        Compile a list of column targets

        Args:
            columns (list(str|F|tuple(str, str))): 
        
        Returns:
            str
        """
        return self.keywords.LIST_SEPARATOR.join(
            self.compile_target_column(column) for column in columns
        )

    def compile_target_column(self, column):
        """
        Compile a target column

        Args:
            column (str|F|tuple(str|F, str)):
        
        Returns:
            str
        """
        if isinstance(column, str):
            if column == "*":
                return self.keywords.ALL

            return column

        if isinstance(column, F):
            return self.compile_function(column)

        # Alias
        compiled_column = self.compile_target_column(column[0])
        return f"{compiled_column} {self.keywords.AS} {column[1]}"

    def compile_function(self, function):
        """
        Compile a F

        Args:
            function (F):
        
        Returns:
            str
        """
        function_name = function.name.lower()

        method_name = f"compile_func_{function_name}"

        try:
            return getattr(self, method_name)(function)
        except AttributeError:
            return self.compile_generic_func(function)

    def compile_from(self, target):
        """
        Compiles a from clause

        Args:
            target (object): Object with a 'name' attribute
        
        Returns:
            str
        """
        return f"{self.keywords.FROM} {target.name}"

    def compile_where(self, wheres):
        """
        Compile a where query or a where clause made of a
        list of conditions

        Args:
            wheres (Query|list): Query or list of SimpleWhereClause
                and GroupWhereClause
        
        Returns:
            str
        """
        compiled_str = ""

        if isinstance(wheres, Query):
            wheres = wheres._where

        for where in wheres:
            if isinstance(where, SimpleWhereClause):
                compiled_where = self.compile_simple_where(where)
            elif isinstance(where, GroupWhereClause):
                compiled_where = self.compile_group_where(where)

            compiled_str = f"{compiled_str} {compiled_where}"

            if where.boolean is not None:
                given_boolean = where.boolean

                if given_boolean == "and":
                    boolean = self.keywords.AND
                elif given_boolean == "or":
                    boolean = self.keywords.OR
                else:
                    raise CompilationError(f"Boolean {given_boolean} not supported")

                compiled_str = f"{compiled_str} {boolean} "

        return f"{self.keywords.WHERE} {compiled_str}"

    def compile_simple_where(self, where):
        """
        Compile a SimpleWhereClause

        Args:
            where (SimpleWhereClause):
        
        Returns:
            str
        """
        column = self.compile_target_column(where._column)

        op = self.compile_operator(where._op)

        # Value can be a Query object or a value
        if isinstance(where._value, Query):
            sub_query = self.compile(where._value, False)

            value = f"({sub_query})"
        else:
            value = self.compile_value(where._value)

        return f"{column} {op} {value}"

    def compile_value(self, value):
        """
        Compiles a constant value to a string

        Args:
            value (object):
        
        Returns:
            str
        """
        value_type = type(value).__name__
        method_name = f"compile_{value_type}_value"

        try:
            return getattr(self, method_name)(value)
        except AttributeError:
            return self.compile_generic_value(value)

    def compile_group_where(self, where):
        """
        Compiles a GroupWhereClause

        Args:
            where (GroupWhereClause):
        
        Returns:
            str
        """
        group_query = self.compile(where._group, False)

        return f"({group_query})"

    def compile_operator(self, op):
        """
        Compile operator. Currently returns the given argument.

        TODO: map operator from generic list to dialect specifics

        Args:
            op (str):
        
        Returns:
            str
        """
        return op

    def compile_generic_value(self, val):
        """
        Calls str() on given value object

        Args:
            val (object):
        
        Returns:
            str
        """
        return str(val)

    def compile_generic_func(self, function):
        """
        Last resort compile method for functions

        Args:
            function (F):
        
        Returns:
            str
        """
        function_name = function.name
        args = function.args

        compiled_args = self.keywords.LIST_SEPARATOR.join(
            [self.compile_value(arg) for arg in args]
        )

        return f"{function_name}({compiled_args})"
