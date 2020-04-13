from typing import Any

from .base_types import (
    BooleanType,
    Collection,
    DateType,
    DateTimeType,
    NumberType,
    Referenceable,
    StringType,
    TimeType,
)

from .function import (
    As,
    Asc,
    Desc,
    In,
    Like,
    Max,
    Min,
    Sum,
    TableStar,
    WithOperatorSupport,
)


class Column(WithOperatorSupport, Referenceable):
    def __init__(self, name):
        """
        Args:
            name (str): Column name
        """
        self.name = name
        self._alias = None
        self.table = None

    def alias(self, name):
        """
        Returns a copy of the current object with the alias property set to
        name.

        Args:
            name (str): Name to alias to

        Returns:
            Column
        """
        return As(self, name)

    def bind(self, table):
        """
        Bind column to a table.

        Args:
            table (Table):

        Returns:
            Column self
        """
        self.table = table
        return self

    def equals(self, other):
        """
        Compare two Column instances. Two columns are identical when they point
        to the same Table object, have the same name and have the same type.

        Args:
            other (Column):

        Returns:
            bool
        """
        return (
            type(other) == type(self)
            and other.table is self.table
            and other.type is self.type
            and other.name == self.name
        )

    def asc(self):
        """
        Shorthand for Asc(self)

        Returns:
            Asc
        """
        return Asc(self)

    def desc(self):
        """
        Shorthand for Desc(self)

        Returns:
            Desc
        """
        return Desc(self)

    @property
    def is_aliased(self):
        """
        Returns True if _alias is not None, False otherwise.

        Returns:
            bool
        """
        return self._alias is not None

    def isin(self, values):
        """
        Shorthand for In(self, values)

        Args:
            values (object):

        Returns:
            In
        """
        return In(self, values)

    def max(self):
        """
        Shorthand for Max(self)

        Returns:
            Max
        """
        return Max(self)

    def min(self):
        """
        Shorthand for Min(self)

        Returns:
            Min
        """
        return Min(self)

    def like(self, pattern):
        """
        Shorthand for Like(self, pattern)

        Returns:
            Like
        """
        return Like(self, pattern)

    def sum(self):
        """
        Shorthand for Sum(self)

        Returns:
            Sum
        """
        return Sum(self)

    def _copy(self):
        """
        Create a new object bound to the same table instance and column name
        and of the same type. Useful to implement column aliases. The new
        instance will be equal (as per __eq__) to the current instance.

        Returns:
            Column
        """
        return type(self)(self.name, self.type).bind(self.table)


class AnyColumn(Collection[Any], Column):
    pass


class NumberColumn(Collection[NumberType], Column):
    pass


class BooleanColumn(Collection[BooleanType], Column):
    pass


class StringColumn(Collection[StringType], Column):
    pass


class DateColumn(Collection[DateType], Column):
    pass


class DateTimeColumn(Collection[DateTimeType], Column):
    pass


class TimeColumn(Collection[TimeType], Column):
    pass


class Table(Referenceable):
    __columns__ = None

    def __init__(self, name, db=None):
        """
        Args:
            name (str): Name of the table
            db (str): Name of the target database, optional
        """
        self.name = name
        self.db = db
        self._process_annotations()

    def column(self, name):
        """
        Returns a Column object for a given column name.

        If the Table has a defined schema, this will raise a
        TODO: create error
        error if the column does not exist in the schema. Otherwise,
        a new instance of Column is created, with type AnyColumn.

        Args:
            name (str): Column name

        Returns
            Column
        """
        if self.__columns__ is None:
            return AnyColumn(name).bind(self)

        return self.__columns__[name]

    def all(self):
        """
        To be used when all the columns in a table need to be referenced. This
        returns an instance of Column named "*" bound to the table, which when
        compiled yields tablename.*

        Returns:
            TableStar
        """
        return TableStar(self)

    def alias(self, alias):
        """
        Args: 
            alias (str):
        
        Returns:
            As
        """
        return As(self, alias)

    @property
    def qualname(self):
        if self.db is None:
            return self.name

        return f"{self.db}.{self.name}"

    @property
    def is_typed(self):
        return self.__columns__ is not None

    @property
    def columns(self):
        if self.__columns__ is not None:
            return dict(self.__columns__)

        return None

    def _process_annotations(self):
        """
        Processes class annotations and creates Column instances
        bound to the current instance.
        """
        if not hasattr(self, "__annotations__"):
            return

        annotations = dict(self.__annotations__)

        if not all(issubclass(t, Column) for t in annotations.values()):
            raise TypeError("Table column types must be subclasses of Column")

        columns = {}

        for name, column_type in annotations.items():
            if not issubclass(column_type, Column):
                raise TypeError(
                    f"Table column types must be subclasses of Column, {column_type} found"
                )

            columns[name] = column_type(name).bind(self)

        self.__columns__ = columns

    def __getitem__(self, name):
        """
        Key access helper for .column(name)

        Args:
            name (str): Column name

        Returns:
            Column
        """
        return self.column(name)
