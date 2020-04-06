from datetime import date, datetime, time
from numbers import Number
from typing import Generic, TypeVar, Union

StringType = str
NumberType = Number
BooleanType = bool
DateTimeType = datetime
TimeType = time
DateType = Union[DateTimeType, date]
NullType = type(None)


T = TypeVar("T")


class Collection(Generic[T]):
    def __init_subclass__(cls, *args, **kwargs):
        """
        Hook into subclasses and set the __dtype__ attribute.
        This is a pretty dumb implementation at the moment so it
        should be revisited as it makes too many assumptions about the way
        subclasses are constructed, assumptions which are NOT made in type_checking
        """
        cls.__dtype__ = cls.__orig_bases__[0].__args__[0]


class Referenceable:
    pass
