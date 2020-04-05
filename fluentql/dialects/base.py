from ..function import F, Star
from ..query import Query
from ..errors import CompilationError
from ..types import Column, Table


class Keywords:
    SELECT = "select"
    FROM = "from"
    AS = "as"
    WHERE = "where"
    STAR = "*"
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

    def dispatch(self, o):
        """
        Dispatch to appropriate function

        Args:
            o (object):
        
        Returns:
            str
        """
        method_name = None

        if isinstance(o, Query):
            command = o._command.value.lower()
            method_name = f"compile_{command}_query"

        elif isinstance(o, F):
            # First look for specific function implementations
            f_name = type(o).__name__.lower()
            method_name = f"compile_{f_name}_function"

            # If that method doesn't exist, fall back to generic
            if not hasattr(self, method_name):
                method_name = f"compile_function"

        elif isinstance(o, Column):
            method_name = f"compile_column_reference"

        elif isinstance(o, Table):
            method_name = f"compile_table_reference"

        else:
            # Assume constant
            type_name = type(o).__name__.lower()

            # First look for specific function implementations
            method_name = f"compile_{type_name}_constant"

            if not hasattr(self, method_name):
                # Fall back to generic
                method_name = f"compile_constant"

        return getattr(self, method_name)(o)

    def compile(self, query):
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
        return self.dispatch(query)
        # command = query._command.value
        # compiled_query = getattr(self, f"compile_{command}")(query)

        # if terminal_query:
        #    compiled_query = f"{compiled_query}{self._get_keyword('QUERY_END')}"

        # return compiled_query

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
            q_template_components.append("{where}")
            query_components["where"] = self.dispatch(query._where)

        query_components["query_end"] = self._get_keyword("QUERY_END")
        q_template_components.append("{query_end}")

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
        return self.compile_infix_function(f, "=")

    def compile_bitwiseand_function(self, f):
        and_keyword = self._get_keyword("AND")

        return self.compile_infix_function(f, and_keyword)

    def compile_bitwiseor_function(self, f):
        or_keyword = self._get_keyword("OR")

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
        return f"'{val}'"

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

    def compile_tablestar_function(self, f):
        table = f.__values__[0]
        star = self._get_keyword("STAR")

        return f"{self.dispatch(table)}.{star}"

    def compile_star_function(self, f):
        return self._get_keyword("STAR")

    def compile_table_reference(self, table):
        return table.qualname

    def compile_column_reference(self, column):
        return column.name

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
