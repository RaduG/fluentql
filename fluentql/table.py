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


class Table:
    __columns__ = None
    __tablename__ = None

    def __init__(self, table_name):
        """
        Args:
            table_name (str): Name of the table
        """
        self.__tablename__ = table_name

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

    def __getitem__(self, name):
        """
        Key access helper for .column(name)

        Args:
            name (str): Column name
        
        Returns:
            Column
        """
        return self.column(name)
