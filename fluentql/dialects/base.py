from ..query import Query, QueryFunction, SimpleWhereClause, GroupWhereClause
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
            where = self.compile_wheres(query._where)

        return f"{self.keywords.SELECT} {columns} {from_} {where}"

    def compile_target_columns(self, columns):
        """
        Compile a list of column targets

        Args:
            columns (list(str|QueryFunction|tuple(str, str))): 
        
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
            column (str|QueryFunction|tuple(str|QueryFunction, str)):
        
        Returns:
            str
        """
        if isinstance(column, str):
            if column == "*":
                return self.keywords.ALL

            return column

        if isinstance(column, QueryFunction):
            return self.compile_function(column)

        # Alias
        compiled_column = self.compile_target_column(column[0])
        return f"{compiled_column} {self.keywords.AS} {column[1]}"

    def compile_function(self, function):
        """
        Compile a QueryFunction

        Args:
            function (QueryFunction):
        
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

    def compile_wheres(self, wheres):
        """
        Compile a where clause made of a list of conditions

        Args:
            wheres (list): List of SimpleWhereClause and GroupWhereClause
        
        Returns:
            str
        """
        compiled_str = ""

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
            value_type = type(where._value).__name__
            method_name = f"compile_{value_type}_value"

            try:
                value = getattr(self, method_name)(where._value)
            except AttributeError:
                value = self.compile_generic_value(where._value)

        return f"{column} {op} {value}"

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
