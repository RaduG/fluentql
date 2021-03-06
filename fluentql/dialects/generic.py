from .base import BaseDialect
from ..function import F, Star
from ..errors import CompilationError


class _GenericNames:
    MAX = "max"
    MIN = "min"
    LIKE = "like"
    SUM = "sum"


class _GenericKeywords:
    SELECT = "select"
    DELETE = "delete"
    FROM = "from"
    AS = "as"
    WHERE = "where"
    STAR = "*"
    DISTINCT = "distinct"

    GROUP_BY = "group by"
    HAVING = "having"
    FETCH = "limit"
    SKIP = "offset"
    ORDER_BY = "order by"
    ASCENDING = "asc"
    DESCENDING = "desc"

    JOIN = "join"
    LEFT_JOIN = "left join"
    RIGHT_JOIN = "right join"
    INNER_JOIN = "inner join"
    OUTER_JOIN = "outer join"
    CROSS_JOIN = "join"
    USING = "using"
    ON = "on"

    TRUE = "true"
    FALSE = "false"
    NULL = "null"


class _GenericOperators:
    ADD = "+"
    AND = "and"
    DIVIDE = "/"
    EQUAL = "="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    IN = "in"
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    MODULO = "%"
    MULTIPLY = "*"
    NOT = "not"
    NOT_EQUAL = "<>"
    OR = "or"
    SUBTRACT = "-"
    XOR = "xor"


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
        Add QUERY END at the end.

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
        Compile a select query.

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

        select_keyword = self._get_keyword("SELECT")

        if query.has_option("distinct"):
            distinct_keyword = self._get_keyword("DISTINCT")
            query_components["select"] = f"{select_keyword} {distinct_keyword}"
        else:
            query_components["select"] = select_keyword

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

        if query._having is not None:
            q_template_components.append("{having_keyword}")
            q_template_components.append("{having}")
            query_components["having_keyword"] = self._get_keyword("HAVING")
            query_components["having"] = self.dispatch(query._having)

        if query._order is not None:
            q_template_components.append("{order_by_keyword}")
            q_template_components.append("{order_by}")
            query_components["order_by_keyword"] = self._get_keyword("ORDER_BY")
            query_components["order_by"] = ", ".join(
                [self.dispatch(c) for c in query._order]
            )

        if query.has_option("fetch"):
            q_template_components.append("{fetch_keyword}")
            q_template_components.append("{fetch}")
            query_components["fetch_keyword"] = self._get_keyword("FETCH")
            query_components["fetch"] = self.dispatch(query.get_option("fetch"))

        if query.has_option("skip"):
            q_template_components.append("{skip_keyword}")
            q_template_components.append("{skip}")
            query_components["skip_keyword"] = self._get_keyword("SKIP")
            query_components["skip"] = self.dispatch(query.get_option("skip"))

        query_template = " ".join(q_template_components)

        return query_template.format(**query_components)

    def compile_delete_query(self, query):
        """
        Compiles a delete query

        Args:
            query (Query):
        
        Returns:
            str
        """
        # If there is no target for the delete query, need to raise an error
        if query._target is None or len(query._target) == 0:
            raise CompilationError("Delete query must have a target")

        q_template_components = ["{delete}", "{from_}"]

        query_components = {}

        query_components["delete"] = self._get_keyword("DELETE")
        query_components[
            "from_"
        ] = f"{self._get_keyword('FROM')} {self.dispatch(query._target[0])}"

        if query._where is not None:
            q_template_components.append("{where_keyword}")
            q_template_components.append("{where}")
            query_components["where_keyword"] = self._get_keyword("WHERE")
            query_components["where"] = self.dispatch(query._where)

        query_template = " ".join(q_template_components)

        return query_template.format(**query_components)

    def compile_infix_function(self, f, name=None):
        """
        Compiles a function with 2 arguments as: dispatch(values[0]) NAME
        dispatch(values[1]). If name is not given, the function name is used.

        Args:
            f (F):
            name (str): Defaults to None

        Returns:
            str
        """
        left, right = f.__values__

        left_c = self.dispatch(left)

        if name is None:
            name = type(f).__name__.lower()

        right_c = self.dispatch(right)

        # If rhs is a function and one of its args is a function,
        # wrap it in parantheses
        if isinstance(right, F) and any(isinstance(v, F) for v in right.__values__):
            right_c = f"({right_c})"

        return f"{left_c} {name} {right_c}"

    def compile_join_query(self, join):
        """
        Compile a join query.

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
        Calls str() on given value object.

        Args:
            val (object):

        Returns:
            str
        """
        return str(val)

    def compile_str_constant(self, val):
        """
        Wraps a string in quotes.

        Args:
            val (str):

        Returns:
            str
        """
        quote_char = self._get_symbol("STRING_QUOTE")
        return f"{quote_char}{val}{quote_char}"

    def compile_bool_constant(self, val):
        """
        Returns the dialect name for the boolean values.

        Args:
            val (bool):

        Returns:
            str
        """
        if val is True:
            return self._get_keyword("TRUE")

        return self._get_keyword("FALSE")

    def compile_nonetype_constant(self, val):
        """
        Returns the dialect name for None (null)

        Args:
            val (NoneType):

        Returns:
            str
        """
        return self._get_keyword("NULL")

    def compile_function(self, f, name=None):
        """
        Last resort compile method for functions.

        Args:
            function (F):
            name (str):
        Returns:
            str
        """
        name = name or type(f).__name__.lower()
        values = f.__values__

        compiled_values = f", ".join([self.dispatch(v) for v in values])

        return f"{name}({compiled_values})"

    def compile_add_function(self, f):
        """
        Args:
            f (Add):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("ADD"))

    def compile_subtract_function(self, f):
        """
        Args:
            f (Subtract):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("SUBTRACT"))

    def compile_multiply_function(self, f):
        """
        Args:
            f (Multiply):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("MULTIPLY"))

    def compile_divide_function(self, f):
        """
        Args:
            f (Divide):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("DIVIDE"))

    def compile_modulo_function(self, f):
        """
        Args:
            f (Modulo):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("MODULO"))

    def compile_bitwiseand_function(self, f):
        """
        Args:
            f (BitwiseAnd):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("AND"))

    def compile_bitwiseor_function(self, f):
        """
        Args:
            f (BitwiseOr):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("OR"))

    def compile_bitwisexor_function(self, f):
        """
        Args:
            f (BitwiseXor):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("XOR"))

    def compile_equals_function(self, f):
        """
        Args:
            f (Equals):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("EQUAL"))

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

    def compile_lessthanorequal_function(self, f):
        """
        Args:
            f (LessThanOrEqual):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("LESS_THAN_OR_EQUAL"))

    def compile_greaterthan_function(self, f):
        """
        Args:
            f (GreaterThan):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_operator("GREATER_THAN"))

    def compile_greaterthanorequal_function(self, f):
        """
        Args:
            f (GreaterThanOrEqual):
        
        Returns:
            str
        """
        return self.compile_infix_function(
            f, self._get_operator("GREATER_THAN_OR_EQUAL")
        )

    def compile_not_function(self, f):
        """
        Args:
            f (Not):
        
        Returns:
            str
        """
        not_keyword = self._get_operator("NOT")

        return f"{not_keyword} ({self.dispatch(f.__values__[0])})"

    def compile_as_function(self, f):
        """
        Compiles as: dispatch(values[0]) AS dispatch(values[1])

        Args:
            f (As):

        Returns:
            str
        """
        as_keyword = self._get_keyword("AS")
        left, right = f.__values__

        return f"{self.dispatch(left)} {as_keyword} {right}"

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

    def compile_like_function(self, f):
        """
        Args:
            f (Like):
        
        Returns:
            str
        """
        return self.compile_infix_function(f, self._get_name("LIKE"))

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

    def compile_max_function(self, f):
        """
        Args:
            f (Max):
        
        Returns:
            str
        """
        return self.compile_function(f, self._get_name("MAX"))

    def compile_min_function(self, f):
        """
        Args:
            f (Min):
        
        Returns:
            str
        """
        return self.compile_function(f, self._get_name("MIN"))

    def compile_sum_function(self, f):
        """
        Args:
            f (Sum):
        
        Returns:
            str
        """
        return self.compile_function(f, self._get_name("SUM"))

    def compile_asc_function(self, f):
        """
        Args:
            f (Asc):

        Returns:
            str
        """
        value = f.__values__[0]

        asc_keyword = self._get_keyword("ASCENDING")

        return f"{self.dispatch(value)} {asc_keyword}"

    def compile_desc_function(self, f):
        """
        Args:
            f (Desc):

        Returns:
            str
        """
        value = f.__values__[0]

        desc_keyword = self._get_keyword("DESCENDING")

        return f"{self.dispatch(value)} {desc_keyword}"

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
        option_name = "use_absolute_names_for_columns"
        absolute_name = (
            self._get_option(option_name) if self._has_option(option_name) else False
        )

        if absolute_name:
            return f"{column.table.name}.{column.name}"

        return column.name
