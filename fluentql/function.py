from typing import Any, TypeVar, Union
from types import MethodType, FunctionType

from .base_types import BooleanType, Constant, StringType, Collection, Referenceable
from .type_checking import TypeChecker


AnyArgs = TypeVar("AnyArgs")
NoArgs = TypeVar("NoArgs")
VarArgs = TypeVar("VarArgs")
T = TypeVar("T")


class F(Referenceable):
    def __init_subclass__(cls, **kwargs):
        """
        Use init_subclass to map the arguments / return value based on type
        annotations, instead of going hard at it with a metaclass.

        Args:
            cls (type):
            **kwargs (dict):
        """
        cls._process_annotations()

    @classmethod
    def _process_annotations(cls):
        """
        Set __args__ and __returns__ attributes to cls. Those will be set to
        the user annotations, if any, or will default to:

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
        elif hasattr(cls, "returns"):
            cls.__returns__ = cls.returns
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

        self.__returns__ = self._get_return_type()

    def _get_return_type(self):
        # If __returns__ is a function, the result of it called
        # on args is the actual return type
        if isinstance(self.__returns__, (FunctionType, MethodType)):
            # Replace F arg types with their return values
            return self.__returns__(
                tuple(self.__type_checker__._matched_types),
                self.__type_checker__._type_var_mapping,
            )

        return self.__returns__

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

    def _validate_args(self, args):
        if self.__args__ is AnyArgs:
            if len(args) == 0:
                raise TypeError(f"{type(self).__name__} takes at least one argument")

            # All expected args are Any
            arg_types = [Any] * len(args)

        elif self.__args__ is NoArgs:
            if len(args) > 0:
                raise TypeError(f"{type(self).__name__} takes no arguments")

            return

        elif len(self.__args__) != len(args):
            raise TypeError(
                f"{type(self).__name__} takes {len(self.__args__)} arguments, {len(args)} given"
            )
        else:
            # Replace F arg types with their return values
            arg_types = [
                arg.__returns__ if issubclass(type(arg), F) else type(arg)
                for arg in args
            ]

        self.__type_checker__ = TypeChecker(arg_types, self.__args__)
        self.__type_checker__.validate()


class ArithmeticF(F):
    @classmethod
    def returns(cls, matched_types, type_var_mapping):
        """
        If both args are Constant, the return value is Constant. Otherwise, the
        return value is Collection.

        Args:
            args (list(type)): Argument types, in order

        Returns:
            type
        """
        constant_type = type_var_mapping[Constant][1]

        if any(Collection in t.__mro__ for t in matched_types if hasattr(t, "__mro__")):
            return Collection[constant_type]

        return constant_type


class BooleanF(F):
    @classmethod
    def returns(cls, matched_types, type_var_mapping):
        """
        If both args are BooleanType, the return value is BooleanType.
        Otherwise, the return value is collection.

        Args:
            args (list(type)): Argument types, in order

        Returns:
            type
        """
        if any(Collection in t.__mro__ for t in matched_types if hasattr(t, "__mro__")):
            return Collection[BooleanType]

        return Collection[BooleanType]


class AggregateF(F):
    @classmethod
    def returns(cls, matched_types, type_var_mapping):
        return type_var_mapping[Constant][1]


class ComparisonF(F):
    pass


class OrderF(F):
    pass


class Add(ArithmeticF):
    a: Union[Constant, Collection[Constant]]
    b: Union[Constant, Collection[Constant]]


class Subtract(ArithmeticF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class Multiply(ArithmeticF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class Divide(ArithmeticF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class Modulo(ArithmeticF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class BitwiseOr(BooleanF):
    a: Union[Collection[BooleanType], BooleanType]
    b: Union[Collection[BooleanType], BooleanType]


class BitwiseAnd(BooleanF):
    a: Union[Collection[BooleanType], BooleanType]
    b: Union[Collection[BooleanType], BooleanType]


class BitwiseXor(BooleanF):
    a: Union[Collection[BooleanType], BooleanType]
    b: Union[Collection[BooleanType], BooleanType]


class Equals(BooleanF):
    a: Union[Constant, Collection[Constant]]
    b: Union[Constant, Collection[Constant]]


class LessThan(BooleanF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class LessThanOrEqual(BooleanF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class GreaterThan(BooleanF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class GreaterThanOrEqual(BooleanF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class NotEqual(BooleanF):
    a: Union[Constant, Collection[Any]]
    b: Union[Constant, Collection[Any]]


class Not(BooleanF):
    a: Union[BooleanType, Collection[BooleanType]]


class As(F):
    a: T
    b: str
    returns: T


class TableStar(F):
    a: Referenceable
    returns: Any


class Star(F):
    a: NoArgs
    returns: Any


class Like(BooleanF):
    a: Collection[StringType]
    b: str


class In(BooleanF):
    a: Collection[Any]
    b: Any


class Max(AggregateF):
    a: Collection[Constant]


class Min(AggregateF):
    a: Collection[Constant]


class Asc(OrderF):
    a: Collection[Any]

    returns: Collection[Any]


class Desc(OrderF):
    a: Collection[Any]

    returns: Collection[Any]
