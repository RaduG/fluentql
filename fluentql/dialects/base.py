from ..function import F
from ..query import Query, SimpleBooleanClause, GroupBooleanClause
from ..errors import CompilationError
from ..table import Column, Table


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

    LEFT_JOIN = "left join"
    RIGHT_JOIN = "right join"
    INNER_JOIN = "inner join"
    OUTER_JOIN = "outer join"
    CROSS_JOIN = "join"
    ON = "on"


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
        command = query._command.value
        compiled_query = getattr(self, f"compile_{command}")(query)

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
        from_ = self.compile_from(query._target[0])

        q = f"{self.keywords.SELECT} {columns} {from_}"

        # Compile join if it exists
        if query._join is not None:
            for join in query._join:
                join_type = join.get_option("join_type")
                method_name = f"compile_{join_type}_join"

                # First try specific join method, otherwise use fallback
                try:
                    compiled_join = getattr(self, method_name)(join)
                except AttributeError:
                    compiled_join = self.compile_join(join)

                q = f"{q} {compiled_join}"

        # Compile Where if it exists
        if query._where is not None:
            where = self.compile_where(query._where)
            q = f"{q} {where}"

        return q

    def compile_target_columns(self, columns):
        """
        Compile a list of column targets

        Args:
            columns (list(str|F|tuple(str, str))): 
        
        Returns:
            str
        """
        # Select all
        if len(columns) == 0:
            return self.keywords.ALL

        return self.keywords.LIST_SEPARATOR.join(
            self.compile_target_column(column) for column in columns
        )

    def compile_target_column(self, column):
        """
        Compile a target column

        Args:
            column (Column|F|tuple(Column|F, str)):
        
        Returns:
            str
        """
        if isinstance(column, Column):
            return column.name

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
            wheres (Query|list): Query or list of SimpleBooleanClause
                and GroupBooleanClause
        
        Returns:
            str
        """
        if isinstance(wheres, Query):
            wheres = wheres._where

        compiled_wheres = []

        for where in wheres:
            if isinstance(where, SimpleBooleanClause):
                compiled_where = self.compile_simple_boolean_clause(where)
            elif isinstance(where, GroupBooleanClause):
                compiled_where = self.compile_group_boolean_clause(where)

            if where.boolean is not None:
                given_boolean = where.boolean

                if given_boolean == "and":
                    boolean = self.keywords.AND
                elif given_boolean == "or":
                    boolean = self.keywords.OR
                else:
                    raise CompilationError(f"Boolean {given_boolean} not supported")

                compiled_where = f"{compiled_where} {boolean}"

            compiled_wheres.append(compiled_where)

        compiled_wheres_str = " ".join(compiled_wheres)
        return f"{self.keywords.WHERE} {compiled_wheres_str}"

    def compile_on(self, ons):
        """
        Compiles an on query or a list on on clauses

        Args:
            ons (Query|list(BooleanClause)):
        
        Returns:
            str
        """
        if isinstance(ons, Query):
            ons = ons._on

        compiled_ons = []

        for on in ons:
            if isinstance(on, SimpleBooleanClause):
                compiled_on = self.compile_simple_boolean_clause(on)
            elif isinstance(on, GroupBooleanClause):
                compiled_on = self.compile_group_boolean_clause(on)

            if on.boolean is not None:
                given_boolean = on.boolean

                if given_boolean == "and":
                    boolean = self.keywords.AND
                elif given_boolean == "or":
                    boolean = self.keywords.OR
                else:
                    raise CompilationError(f"Boolean {given_boolean} not supported")

                compiled_on = f"{compiled_on} {boolean}"

            compiled_ons.append(compiled_on)

        return " ".join(compiled_ons)

    def compile_simple_boolean_clause(self, clause):
        """
        Compile a SimpleBooleanClause

        Args:
            clause (SimpleBooleanClause):
        
        Returns:
            str
        """
        left = self.compile_term(clause._left)
        op = self.compile_operator(clause._op)

        # Value can be a Query object or a value
        if isinstance(clause._right, Query):
            right = f"({self.compile(clause._right, False)})"
        else:
            right = self.compile_term(clause._right)

        return f"{left} {op} {right}"

    def compile_term(self, term):
        """
        Compile a term. Can be a Column, F or value.

        Args:
            term (Column|F|object):
        
        Returns:
            str
        """
        if isinstance(term, Column):
            return self.compile_target_column(term)
        elif isinstance(term, F):
            return self.compile_function(term)
        else:
            return self.compile_value(term)

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

    def compile_group_boolean_clause(self, clause):
        """
        Compiles a GroupBooleanClause

        Args:
            clause (GroupBooleanClause):
        
        Returns:
            str
        """
        clause_query = self.compile(clause._group, False)

        return f"({clause_query})"

    def compile_join(self, join):
        """
        Compile a join query

        Args:
            join (Query): join Query
        
        Returns:
            str
        """
        join_target = join._target[-1]
        join_type = join.get_option("join_type")

        if join_type == "inner":
            join_type_str = self.keywords.INNER_JOIN
        elif join_type == "outer":
            join_type_str = self.keywords.OUTER_JOIN
        elif join_type == "left":
            join_type_str = self.keywords.LEFT_JOIN
        elif join_type == "right":
            join_type_str = self.keywords.RIGHT_JOIN
        elif join_type == "cross":
            join_type_str = self.keywords.CROSS_JOIN
        else:
            raise ValueError(f"Join type invalid: {join_type}")

        compiled_join = f"{join_type_str} {join_target.name}"

        if len(join._on) > 0:
            compiled_ons = self.compile_on(join._on)
            compiled_join = f"{compiled_join} {self.keywords.ON} {compiled_ons}"

        return compiled_join

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

        compiled_args = f"{self.keywords.LIST_SEPARATOR} ".join(
            [
                self.compile_target_column(arg)
                if isinstance(arg, Column)
                else self.compile_value(arg)
                for arg in args
            ]
        )

        return f"{function_name}({compiled_args})"
