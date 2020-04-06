from typing import Any, TypeVar, Union

from .base_types import BooleanType, StringType, Collection, Referenceable
from .type_checking import validate_call_types


Constant = TypeVar("Constant")
AnyArgs = TypeVar("AnyArgs")
NoArgs = TypeVar("NoArgs")
VarArgs = TypeVar("VarArgs")


class F(Referenceable):
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
        elif len(annotations) == 1 and list(annotations.values())[0] is NoArgs:
            cls.__args__ = NoArgs
        else:
            cls.__args__ = tuple(annotations.values())

    def __init__(self, *args):
        self._validate_args(args)
        self.__values__ = args

    @property
    def values(self):
        return self.__values__

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
            # Replace F arg types with their return values
            arg_types = [
                type(arg).__returns__ if issubclass(type(arg), F) else type(arg)
                for arg in args
            ]
            validate_call_types(cls.__name__, cls.__args__, arg_types, True)


class Add(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Constant, Collection[Any]]


class Subtract(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Constant, Collection[Any]]


class Multiply(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Constant, Collection[Any]]


class Divide(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Constant, Collection[Any]]


class Modulo(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Constant, Collection[Any]]


class BitwiseOr(F):
    a: Union[Collection[BooleanType], BooleanType]
    b: Union[Collection[BooleanType], BooleanType]
    returns: Union[Collection[BooleanType], BooleanType]


class BitwiseAnd(F):
    a: Union[Collection[BooleanType], BooleanType]
    b: Union[Collection[BooleanType], BooleanType]
    returns: Union[Collection[BooleanType], BooleanType]


class BitwiseXor(F):
    a: Union[Collection[BooleanType], BooleanType]
    b: Union[Collection[BooleanType], BooleanType]
    returns: Union[Collection[BooleanType], BooleanType]


class Equals(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Collection[BooleanType], BooleanType]


class LessThan(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Collection[BooleanType], BooleanType]


class LessThanOrEqual(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Collection[BooleanType], BooleanType]


class GreaterThan(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Collection[BooleanType], BooleanType]


class GreaterThanOrEqual(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Collection[BooleanType], BooleanType]


class NotEqual(F):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]
    returns: Union[Collection[BooleanType], BooleanType]


class As(F):
    a: Referenceable
    b: str
    returns: Referenceable


class TableStar(F):
    a: Referenceable
    returns: Any


class Star(F):
    a: NoArgs
    returns: Any


class Like(F):
    a: Collection[StringType]
    b: str
    returns: Union[Collection[BooleanType], BooleanType]


class In(F):
    a: Collection[Any]
    b: Any
    returns: Union[Collection[BooleanType], BooleanType]


class Max(F):
    a: Collection[Any]
    returns: Any


class Min(F):
    a: Collection[Any]
    returns: Any
