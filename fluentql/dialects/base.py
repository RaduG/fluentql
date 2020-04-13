from ..function import F
from ..query import Query
from ..types import Column, Table


class BaseDialect:
    _names = None
    _keywords = None
    _operators = None
    _symbols = None
    _options = {}

    def __init__(self, **options):
        """
        Args:
            options: 
        """
        self._options = {**self._options, **options}

    def dispatch(self, o):
        """
        Dispatch to appropriate function.

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
        Compile a given query.

        Args:
            query (Query):

        Returns:
            str
        """
        return self.dispatch(query)

    def _get_option(self, name):
        """
        Get a dialect option by name.

        Args:
            name (str):

        Returns:
            object
        """
        return self._options[name]

    def _has_option(self, name):
        """
        Check if a given option is set.

        Args:
            name (str):

        Returns:
            bool
        """
        return name in self._options

    def _get_keyword(self, name):
        """
        Get a keyword by name. Applies any relevant options to it.

        Args:
            name (str): Keyword name

        Returns:
            str
        """
        return getattr(self._keywords, name)

    def _get_name(self, name):
        """
        Args:
            name (str):
        
        Returns:
            str
        """
        return getattr(self._names, name)

    def _get_symbol(self, name):
        """
        Args:
            name (str):
        
        Returns:
            str
        """
        return getattr(self._symbols, name)

    def _get_operator(self, name):
        """
        Args:
            name (str):
        
        Returns:
            str
        """
        return getattr(self._operators, name)
