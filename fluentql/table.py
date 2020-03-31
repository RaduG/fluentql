from .query import Query


class Table:
    def __init__(self, table_name):
        """
        Args:
            table_name (str): Name of the table
        """
        self._name = table_name

    @property
    def name(self):
        """
        Returns the table name.

        Returns:
            str
        """
        return self._name

    def __call__(self):
        """
        Returns a query bound to this table

        Returns:
            Query
        """
        return Query(target=self)
