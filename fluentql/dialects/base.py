from ..function import F
from ..query import Query, SimpleBooleanClause, GroupBooleanClause
from ..errors import CompilationError
from ..table import Column


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
    USING = "using"
    STRING_QUOTE = "'"

    LEFT_JOIN = "left join"
    RIGHT_JOIN = "right join"
    INNER_JOIN = "inner join"
    OUTER_JOIN = "outer join"
    CROSS_JOIN = "join"
    ON = "on"


class Dialect:
    keywords = Keywords
    _options = {
        "all_caps": False,
        "keywords_caps": True,
        "break_line_on_sections": True,
        "indent": False,
    }

    def __init__(self, **options):
        """
        Options:
        - all_caps: bool
        - keywords_caps: bool
        - break_line_on_sections: bool
        - indent: bool
        """
        self._options = {**self._options, **options}

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
            compiled_query = f"{compiled_query}{self._get_keyword('QUERY_END')}"

        return compiled_query

    def compile_select(self, query):
        """
        Compile a select query

        Args:
            query (Query):
        
        Returns:
            str
        """
        # If there is no target for the select query, need to raise an error
        if query._target is None or len(query._target) == 0:
            raise CompilationError("Select query must have a target")

        columns = self.compile_target_columns(query._select)
        from_ = self.compile_from(query._target[0])

        q = f"{self._get_keyword('SELECT')} {columns} {from_}"

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
            return self._get_keyword("ALL")

        return f"{self._get_keyword('LIST_SEPARATOR')} ".join(
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
            return f"{column.table.name}.{column.name}"

        if isinstance(column, F):
            return self.compile_function(column)

        # Alias
        compiled_column = self.compile_target_column(column[0])
        return f"{compiled_column} {self._get_keyword('AS')} {column[1]}"

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
        return f"{self._get_keyword('FROM')} {target.name}"

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
        # We need this later on
        is_query = isinstance(wheres, Query)
        if is_query:
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
                    boolean = self._get_keyword("AND")
                elif given_boolean == "or":
                    boolean = self._get_keyword("OR")
                else:
                    raise CompilationError(f"Boolean {given_boolean} not supported")

                compiled_where = f"{compiled_where} {boolean}"

            compiled_wheres.append(compiled_where)

        compiled_wheres_str = " ".join(compiled_wheres)

        # TODO: proper fix for this issue
        # If the original argument was a Query, then we don't need to
        # add the keyword because it means it's a sub clause in a where
        if is_query:
            return compiled_wheres_str

        return f"{self._get_keyword('WHERE')} {compiled_wheres_str}"

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
                    boolean = self._get_keyword("AND")
                elif given_boolean == "or":
                    boolean = self._get_keyword("OR")
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
            join_type_str = self._get_keyword("INNER_JOIN")
        elif join_type == "outer":
            join_type_str = self._get_keyword("OUTER_JOIN")
        elif join_type == "left":
            join_type_str = self._get_keyword("LEFT_JOIN")
        elif join_type == "right":
            join_type_str = self._get_keyword("RIGHT_JOIN")
        elif join_type == "cross":
            join_type_str = self._get_keyword("CROSS_JOIN")
        else:
            raise CompilationError(f"Join type invalid: {join_type}")

        compiled_join = f"{join_type_str} {join_target.name}"

        if join._on is not None and join._using is not None:
            raise CompilationError("Cannot have both USING and ON in a JOIN")

        if join._on is not None:
            compiled_ons = self.compile_on(join._on)
            compiled_join = f"{compiled_join} {self._get_keyword('ON')} {compiled_ons}"
        elif join._using is not None:
            compiled_using = self.compile_using(join)
            compiled_join = f"{compiled_join} {compiled_using}"

        return compiled_join

    def compile_using(self, join):
        """
        Compile a using clause
        
        Args:
            join (Query): Join sub-query
        
        Returns:
            str
        """
        return f"{self._get_keyword('USING')} ({join._using})"

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

    def compile_str_value(self, val):
        """
        Compile a string value. Generally, strings should be
        wrapped between some form of quote.

        Args:
            val (str):
        
        Returns:
            str
        """
        quote_char = self._get_keyword("STRING_QUOTE")

        return f"{quote_char}{val}{quote_char}"

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

        compiled_args = f"{self._get_keyword('LIST_SEPARATOR')} ".join(
            [
                self.compile_target_column(arg)
                if isinstance(arg, Column)
                else self.compile_value(arg)
                for arg in args
            ]
        )

        return f"{function_name}({compiled_args})"

    def _get_keyword(self, name):
        """
        Get a keyword by name. Applies any relevant options to it.

        Args:
            name (str): Keyword name
        
        Returns:
            str
        """
        keyword = getattr(self.keywords, name)

        if self._options.get("keywords_caps", False):
            keyword = keyword.upper()

        return keyword
