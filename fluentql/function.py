from typing import TypeVar, Union


from .table import (
    AnyColumn,
    NumberColumn,
    StringColumn,
    DateColumn,
    BooleanColumn,
    BooleanType,
)
from .types import validate_call_types


Constant = TypeVar("Constant")
AnyArgs = TypeVar("AnyArgs")
NoArgs = TypeVar("NoArgs")
VarArgs = TypeVar("VarArgs")


class F:
    def __init_subclass__(cls, **kwargs):
        """
        Use init_subclass to map the arguments / return value based
        on type annotations, instead of going hard at it with a metaclass

        Args:
            cls (type):
            **kwargs (dict):
        """
        cls._process_annotations()

    @classmethod
    def _process_annotations(cls):
        """
        Set __args__ and __returns__ attributes to cls. Those will be set
        to the user annotations, if any, or will default to:
        AnyArgs - for __args__
        Any - for __returns__

        Args:
            cls (object):
        """
        try:
            annotations = {**cls.__annotations__}
        except AttributeError:
            annotations = {}

        # Check for "returns"
        if "returns" in annotations:
            cls.__returns__ = annotations.pop("returns")
        else:
            cls.__returns__ = Any

        if len(annotations) == 0:
            cls.__args__ = AnyArgs
        elif len(annotations) == 1 and annotations.values()[0] is NoArgs:
            cls.__args__ = NoArgs
        else:
            cls.__args__ = tuple(annotations.values())

    def __init__(self, *args):
        self._validate_args(args)

    @classmethod
    def new(cls, name):
        """
        Returns a new subclass of cls, with the given name.

        Args:
            name (str):
        
        Returns:
            type
        """
        return type(name, (cls,), {})

    @classmethod
    def _validate_args(cls, args):
        if cls.__args__ is AnyArgs:
            if len(args) == 0:
                raise TypeError(f"{cls.__name__} takes at least one argument")

        elif cls.__args__ is NoArgs:
            if len(args) > 0:
                raise TypeError(f"{cls.__name__} takes no arguments")

        elif len(cls.__args__) != len(args):
            raise TypeError(
                f"{cls.__name__} takes {len(cls.__args__)} arguments, {len(args)} given"
            )
        else:
            validate_call_types(cls.__name__, cls.__args__, args, True)


class Add(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[Constant, AnyColumn]


class Subtract(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[Constant, AnyColumn]


class Multiply(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[Constant, AnyColumn]


class Divide(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[Constant, AnyColumn]


class Modulo(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[Constant, AnyColumn]


class BitwiseOr(F):
    a: Union[BooleanColumn, BooleanType]
    b: Union[BooleanColumn, BooleanType]
    returns: Union[BooleanColumn, BooleanType]


class BitwiseAnd(F):
    a: Union[BooleanColumn, BooleanType]
    b: Union[BooleanColumn, BooleanType]
    returns: Union[BooleanColumn, BooleanType]


class BitwiseXor(F):
    a: Union[BooleanColumn, BooleanType]
    b: Union[BooleanColumn, BooleanType]
    returns: Union[BooleanColumn, BooleanType]


class Equals(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[BooleanType, BooleanColumn]


class LessThan(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[BooleanType, BooleanColumn]


class LesTshanOrEqual(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[BooleanType, BooleanColumn]


class GreaterThan(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[BooleanType, BooleanColumn]


class GreaterThanOrEqual(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[BooleanType, BooleanColumn]


class NotEqual(F):
    a: Union[Constant, AnyColumn]
    b: Union[Constant, AnyColumn]
    returns: Union[BooleanType, BooleanColumn]
