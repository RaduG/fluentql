from .base import BaseDialect
from ..function import Star
from ..errors import CompilationError


class _GenericNames:
    MAX = "max"
    MIN = "min"
    LIKE = "like"


class _GenericKeywords:
    SELECT = "select"
    FROM = "from"
    AS = "as"
    WHERE = "where"
    STAR = "*"

    GROUP_BY = "group by"
    HAVING = "having"
    LIMIT = "limit"

    JOIN = "join"
    LEFT_JOIN = "left join"
    RIGHT_JOIN = "right join"
    INNER_JOIN = "inner join"
    OUTER_JOIN = "outer join"
    CROSS_JOIN = "join"
    USING = "using"
    ON = "on"


class _GenericOperators:
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    EQUAL = "="
    NOT_EQUAL = "<>"
    AND = "and"
    OR = "or"
    XOR = "xor"
    IN = "in"


class _GenericSymbols:
    LIST_SEPARATOR = ","
    QUERY_END = ";"
    STRING_QUOTE = "'"


class GenericSQLDialect(BaseDialect):
    _names = _GenericNames
    _keywords = _GenericKeywords
    _operators = _GenericOperators
    _symbols = _GenericSymbols

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

    def compile(self, query):
        """
        Add QUERY END at the end

        Args:
            query (Query):
        
        Returns:
            str
        """
        query_end_symbol = self._get_symbol("QUERY_END")

        compiled_query = self.dispatch(query)

        return f"{compiled_query}{query_end_symbol}"

    def compile_select_query(self, query):
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

        q_template_components = ["{select}", "{targets}", "{from_}"]

        query_components = {}
        query_components["select"] = self._get_keyword("SELECT")

        if type(query._select) is Star:
            query_components["targets"] = self.dispatch(query._select)
        else:
            query_components["targets"] = ", ".join(
                self.dispatch(t) for t in query._select
            )

        query_components[
            "from_"
        ] = f"{self._get_keyword('FROM')} {self.dispatch(query._target[0])}"

        # Compile join if it exists
        if query._join is not None:
            joins = [self.dispatch(join) for join in query._join]
            query_components["joins"] = " ".join(joins)

        if query._join is not None:
            q_template_components.append("{joins}")
            joins = [self.dispatch(join) for join in query._join]
            query_components["joins"] = " ".join(joins)

        if query._where is not None:
            q_template_components.append("{where_keyword}")
            q_template_components.append("{where}")
            query_components["where_keyword"] = self._get_keyword("WHERE")
            query_components["where"] = self.dispatch(query._where)

        if query._group_by is not None:
            q_template_components.append("{group_by_keyword}")
            q_template_components.append("{group_by}")
            query_components["group_by_keyword"] = self._get_keyword("GROUP_BY")
            query_components["group_by"] = ", ".join(
                [self.dispatch(c) for c in query._group_by]
            )
        query_template = " ".join(q_template_components)

        return query_template.format(**query_components)

    def compile_as_function(self, f):
        """
        Compiles as: 
            dispatch(values[0]) AS dispatch(values[1])
        
        Args:
            f (As):
        
        Returns:
            str
        """
        as_keyword = self._get_keyword("AS")

        return self.compile_infix_function(f, as_keyword)

    def compile_equals_function(self, f):
        """
        Args:
            f (Equals):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("EQUAL"))

    def compile_greaterthan_function(self, f):
        """
        Args:
            f (Equals):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("GREATER_THAN"))

    def compile_bitwiseand_function(self, f):
        """
        Args:
            f (BitwiseAnd):
        
        Returns:
            str
        """
        and_keyword = self._get_operator("AND")

        return self.compile_infix_function(f, and_keyword)

    def compile_bitwiseor_function(self, f):
        """
        Args:
            f (BitwiseOr):
        
        Returns:
            str
        """
        or_keyword = self._get_operator("OR")

        return self.compile_infix_function(f, or_keyword)

    def compile_infix_function(self, f, name=None):
        """
        Compiles a function with 2 arguments as:
            dispatch(values[0]) NAME dispatch(values[1]).
        If name is not given, the function name is used.

        Args:
            f (F):
            name (str): Defaults to None
        
        Returns:
            str
        """
        values = f.__values__

        left = self.dispatch(values[0])
        if name is None:
            name = type(f).__name__.lower()
        right = self.dispatch(values[1])

        return f"{left} {name} {right}"

    def compile_join_query(self, join):
        """
        Compile a join query

        Args:
            join (Query): join Query
        
        Returns:
            str
        """
        join_target = self.dispatch(join._target[-1])
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

        compiled_join = f"{join_type_str} {join_target}"

        if join._on is not None and join._using is not None:
            raise CompilationError("Cannot have both USING and ON in a JOIN")

        if join._on is not None:
            compiled_on = self.dispatch(join._on)
            compiled_join = f"{compiled_join} {self._get_keyword('ON')} {compiled_on}"
        elif join._using is not None:
            using = f"using ({self.dispatch(join._using)})"
            compiled_join = f"{compiled_join} {using}"

        return compiled_join

    def compile_constant(self, val):
        """
        Calls str() on given value object

        Args:
            val (object):
        
        Returns:
            str
        """
        return str(val)

    def compile_str_constant(self, val):
        """
        Wraps a string in quotes

        Args:
            val (str):
        
        Returns:
            str
        """
        quote_char = self._get_symbol("STRING_QUOTE")
        return f"{quote_char}{val}{quote_char}"

    def compile_function(self, f):
        """
        Last resort compile method for functions

        Args:
            function (F):
        
        Returns:
            str
        """
        function_name = type(f).__name__.lower()
        values = f.__values__

        compiled_values = f", ".join([self.dispatch(v) for v in values])

        return f"{function_name}({compiled_values})"

    def compile_notequal_function(self, f):
        """
        Args:
            f (NotEqual):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("NOT_EQUAL"))

    def compile_lessthan_function(self, f):
        """
        Args:
            f (LessThan):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("LESS_THAN"))

    def compile_like_function(self, f):
        """
        Args:
            f (Like):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_name("LIKE"))

    def compile_tablestar_function(self, f):
        """
        Args:
            f (TableStar):
        
        Returns:
            str
        """
        table = f.__values__[0]
        star = self._get_keyword("STAR")

        return f"{self.dispatch(table)}.{star}"

    def compile_star_function(self, f):
        """
        Args:
            f (Star):
        
        Returns:
            str
        """
        return self._get_keyword("STAR")

    def compile_in_function(self, f):
        """
        Args:
            f (In):
        
        Returns:
            str
        """
        values = f.__values__

        left = self.dispatch(values[0])
        name = self._get_operator("IN")
        right = self.dispatch(values[1])

        return f"{left} {name} ({right})"

    def compile_table_reference(self, table):
        """
        Args:
            table (Table):
        
        Returns:
            str
        """
        return table.qualname

    def compile_column_reference(self, column):
        """
        Args:
            column (Column):
        
        Returns:
            str
        """
        return column.name
