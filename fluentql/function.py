class F:
    def __init_subclass__(cls):
        """
        Ensure that every subclass has a name attribute. If an
        explicit attribute is not set, the name of the class in lowercase
        is set to .name
        """
        if not hasattr(cls, "name"):
            setattr(cls, "name", cls.__name__.lower())


class ColumnArgF(F):
    def __init__(self, column):
        self.column = column

    @property
    def args(self):
        return (self.column,)


class Min(ColumnArgF):
    name = "min"


class Max(ColumnArgF):
    name = "max"


class Avg(ColumnArgF):
    name = "avg"
