from typing import Any, Generic, Union, TypeVar

import pytest

from fluentql.type_checking import TypeChecker


T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")

R = TypeVar("R", int, float)


def subclass(t, name):
    """
    Build a named subtype of a given type.

    Args:
        t (type):
        name (str):

    Returns:
        type
    """
    return type(name, (t,), {})


class GenericType(Generic[T]):
    pass


class DualGenericType(Generic[T, U]):
    pass


class TripleGenericType(Generic[T, U, V]):
    pass


@pytest.mark.parametrize(
    ["expected_types", "given_types"],
    [
        [(Any,), (int,)],
        [(int,), (Any,)],
        [(int,), (int,)],
        [(int, str), (int, str)],
        [(str,), (subclass(str, "str_subtype"),)],
        [(T,), (int,)],
        [(T, T), (int, int)],
        [
            (T, GenericType[T]),
            (int, subclass(GenericType[int], "GenericTypeSubclass")),
        ],
        [(T, T), (int, subclass(int, "int1"))],
        [(Union[int, str],), (int,)],
        [(Union[int, str],), (str,)],
        [(Union[T, GenericType[T]],), (int,)],
        [
            (Union[T, GenericType[T]],),
            (subclass(GenericType[int], "GenericTypeSubclass"),),
        ],
        [(Union[T, GenericType[T]], Union[T, GenericType[T]]), (int, int)],
        [(Union[T, GenericType[T]], Union[T, GenericType[T]]), (int, int)],
        [(T, T, T), (int, subclass(int, "int1"), subclass(int, "int2"))],
    ],
)
def test_validate_call_types(expected_types, given_types):
    TypeChecker(given_types, expected_types).validate()


@pytest.mark.parametrize(
    ["expected_types", "given_types"],
    [[(str,), (int,)], [(T, T), (int, float)], [(Union[int, str],), (float,)],],
)
def test_validate_call_types_raises_type_error_if_type_mismatch(
    expected_types, given_types
):
    with pytest.raises(TypeError):
        TypeChecker(given_types, expected_types).validate()
