from typing import TypeVar


AnyColumn = TypeVar("AnyColumn")


class Column:
    def __init__(self, name, type_=AnyColumn):
        """
        Args:
            name (str): Column name
            type_ (type): Column type, defaults to AnyColumn
        """
        self.name = name
        self.type = type_
        self.table = None

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
            return Column(name).bind(self)

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
