from enum import Enum

from .errors import QueryBuilderError


class QueryTypes(Enum):
    SELECT = 0
    INSERT = 1
    UPDATE = 2
    DELETE = 3
    CREATE = 4
    DROP = 5


class Query:
    def __init__(self, target):
        """
        Args:
            target (object): Main target of the query
        """
        self._target = target

        # Initialise query type
        self._type = None

        # Initialise query sections
        self._create = None
        self._update = None
        self._delete = None
        self._drop = None
        self._select = None
        # self._from = None -- this should be target
        self._join = None
        self._where = None
        self._group_by = None
        self._having = None
        self._order = None
        self._union = None
        self._union_order = None

        # Options
        self._options = {}

    def select(self, columns=("*",)):
        """
        Initialise a select query with a list of columns.

        Args:
            columns (list(str|tuple(str, str))): Iterable of column names
                to select. Each element can either be a string, or a 2-tuple
                where the first element is the original column name and the second
                is an alias. Defaults to ('*'), which means all columns will be
                selected.
        
        Returns:
            Query self
        """
        if self._type is not None:
            raise QueryBuilderError(
                "Select columns already defined or select clause not compatible with statement."
            )
        if self._select is not None:
            raise QueryBuilderError("Select columns already defined")

        # Validate columns argument
        assert all(
            isinstance(c, str)
            or (len(c) == 2 and isinstance(c[0], str) and isinstance(c[1], str))
            for c in columns
        ), "Invalid argument for columns"

        self._type = QueryTypes.SELECT
        self._select = tuple(columns)

        return self
