from datetime import time, datetime, date
from typing import Any, Union
from numbers import Number


AnyType = Any
StringType = str
NumberType = Number
BooleanType = bool
DateTimeType = datetime
TimeType = time
DateType = Union[DateTimeType, date]
NullType = type(None)


class Column:
    __dtype__ = AnyType

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
        Returns a copy of the current object with the alias
        property set to name.

        Args:
            name (str): Name to alias to
        
        Returns:
            Column
        """
        column = self._copy()
        column._alias = name

        return column

    def bind(self, table):
        """
        Bind column to a table

        Args:
            table (Table):
        
        Returns:
            Column self
        """
        self.table = table
        return self

    def equals(self, other):
        """
        Compare two Column instances. Two columns are identical when they
        point to the same Table object, have the same name and have the same type.

        Args:
            other (Column):
        
        Returns:
            bool
        """
        return (
            isinstance(other, type(self))
            and other.table is self.table
            and other.name == self.name
            and other.type == self.type
        )

    @property
    def is_aliased(self):
        """
        Returns True if _alias is not None, False otherwise.

        Returns:
            bool
        """
        return self._alias is not None

    def _copy(self):
        """
        Create a new object bound to the same table instance
        and column name and of the same type. Useful to implement column aliases.
        The new instance will be equal (as per __eq__) to the
        current instance.

        Returns:
            Column
        """
        return type(self)(self.name, self.type).bind(self.table)


class AnyColumn(Column):
    pass


class NumberColumn(AnyColumn):
    __dtype__ = NumberType


class BooleanColumn(NumberColumn):
    __dtype__ = BooleanType


class FloatColumn(NumberColumn):
    pass


class IntegerColumn(NumberColumn):
    pass


class StringColumn(AnyColumn):
    __dtype__ = StringType


class DateColumn(AnyColumn):
    __dtype__ = DateType


class DateTimeColumn(DateColumn):
    __dtype__ = DateTimeType


class TimeColumn(DateColumn):
    __dtype__ = TimeType


class Table:
    __columns__ = None

    def __init__(self, name, db=None):
        """
        Args:
            name (str): Name of the table
            db (str): Name of the target database, optional
        """
        self.name = name
        self.db = db

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
        To be used when all the columns in a table need to be referenced.
        This returns an instance of Column named "*" bound to the table,
        which when compiled yields tablename.*

        Returns:
            Column
        """
        return Column("*").bind(self)

    @property
    def qualname(self):
        if self.db is None:
            return self.name

        return f"{self.db}.{self.name}"

    def __getitem__(self, name):
        """
        Key access helper for .column(name)

        Args:
            name (str): Column name
        
        Returns:
            Column
        """
        return self.column(name)
