from collections import defaultdict
from functools import reduce
from itertools import combinations
import typing
from typing import Any, TypeVar, Union


def raise_type_error(parent_name, arg_name, expected_type, found_type):
    try:
        found_type_name = found_type.__name__
    except AttributeError:
        found_type_name = str(found_type)

    raise TypeError(
        f"Argument {arg_name} for {parent_name}: expected {str(expected_type)}, "
        f"found {found_type_name}"
    )


def raise_generic_type_mismatch(parent_name, arg_names, found_types):
    raise TypeError(
        f"Arguments {', '.join([str(n) for n in arg_names])} of {parent_name} expected to have "
        f"the same type. Found {', '.join([t.__name__ for t in found_types])}"
    )


def validate_call_types(parent_name, expected_types, args, raise_error=False):
    """
    Validate if a function call made with args matches the type hints.

    Args:
        parent_name (str): Name of the class/function for which the validation is performed.
            Only used for reporting purposes.
        expected_types (list(type)): Expected arg types
        args (list(object)): Function call arguments
        raise_error (bool): If True, if there is a type mismatch, a TypeError
            is thrown. Otherwise, the truth value of the condition is returned.
            Defaults to False.
    
    Returns:
        bool
    """
    matched_types = []

    for i, (given, expected) in enumerate(list(zip(args, expected_types))):
        matched_type = get_type_match(given, expected)
        if matched_type is None:
            if raise_error:
                raise_type_error(parent_name, i, expected, given)
            return False

        matched_types.append(matched_type)

    # Group matched_types by their use of TypeVar
    type_var_groups = group_by_typevar(matched_types)

    for indices in type_var_groups.values():
        if len(indices) == 1:
            continue

        group_matched_types = []
        for i in indices:
            # First arg is "real" i, but we need the second number
            # to decompose the given type
            if isinstance(i, tuple):
                i, j = i
                given_generic_arg = get_generic_properties(args[i])[1][j]
                group_matched_types.append(given_generic_arg)
            else:
                group_matched_types.append(args[i])

        type_vars_match = reduce(
            lambda a, ts: (
                a and (type_is_valid(ts[0], ts[1]) or type_is_valid(ts[1], ts[0]))
            ),
            combinations(group_matched_types, 2),
            True,
        )

        if not type_vars_match:
            if raise_error:
                raise_generic_type_mismatch(parent_name, indices, group_matched_types)
            else:
                return False

    return True


def group_by_typevar(types):
    """
    Convers a list of arg types to a dict where types are keys
    and the values are the indices in types where a specific type
    was found. This is required in order to process TypeVars.

    Args:
        types (list(type)):
    
    Returns:
        dict
    """
    type_var_groups = defaultdict(lambda: [])

    for i, t in enumerate(types):
        if is_type_var(t):
            type_var_groups[t].append(i)
        elif is_generic(t):
            # Extract args
            args = t.__args__

            for j, arg in enumerate(args):
                if is_type_var(arg):
                    # i-th argument of the function, j-th generic arg
                    type_var_groups[arg].append((i, j))

    return dict(type_var_groups)


def get_type_match(given, expected):
    """
    Get the type in expected for which given is a
    match. Returns None if there is no match.

    Args:
        given (type):
        expected (type):
    
    Returns:
        type or None
    """
    # Any matches all
    if expected is Any or given is Any:
        return given

    # First, try perfect match
    if given is expected:
        return given

    # Try nicer ways for non-Type variables
    try:
        # Then, try subclass
        if issubclass(given, expected):
            return given

        # Then, try isinstance
        if isinstance(given, expected):
            return given

    except TypeError:
        pass

    # Is this a TypeVar?
    if is_type_var(expected):
        matching_types = expected.__constraints__

        # If the TypeVar has type constraints, check against those. If there are none,
        # return True
        if len(matching_types):
            if any(type_is_valid(given, t) for t in matching_types):
                return expected
        else:
            return expected

    # Is this a Union?
    if is_union(expected):
        matching_types = expected.__args__

        # Get the types part of Union and check against those
        for t in matching_types:
            type_match = get_type_match(given, t)
            if type_match is not None:
                return t

    # Is this a Generic?
    if is_generic(expected):
        if is_generic_subclass(given, expected):
            return expected

    return None


def type_is_valid(given, expected):
    """
    Checks if the given type matches the expected. Will perform
    some validation for types in the typing module, including TypeVar and Union,
    but not all.

    Args:
        given (type):
        expected (type):
    
    Returns:
        bool
    """
    return get_type_match(given, expected) is not None


def get_generic_properties(t):
    """
    Extract the base and args of t, assumed to be
    an instance of a typing.Generic subclass. This function 
    will only look at the first instance of a Generic instance
    in the mro, from right to left.

    Args:
        t (type)
    
    Returns:
        tuple(type, tuple(*type)), where the first
            element is the base and the second element
            is the list of args.
    """
    bases = t.__orig_bases__

    for base in reversed(bases):
        if is_generic(base) and base.__args__ is not None:
            break
    else:
        raise TypeError(f"Type {t} is not a subclass of Generic")

    return base.__origin__, base.__args__


def is_generic_subclass(given, expected):
    """
    Checks if given implements expected, which is assumed to be
    a subclass of a typing.Generic instance. The validation is done down to
    the generic type level (__args__), and given's args must be
    subtypes of expected's args.

    Args:
        given (type):
        expected (Generic):
    
    Returns:
        bool
    """
    # Get the base and args
    expected_origin = expected.__origin__
    expected_args = expected.__args__

    # Quick check: given must be a subclass of expected origin
    if not issubclass(given, expected_origin):
        return False

    # Traverse __orig_bases__ until we find at least one reference to expected
    # origin
    eligible_bases = [
        base
        for base in given.__orig_bases__
        if hasattr(base, "__origin__") and base.__origin__ is expected_origin
    ]

    if len(eligible_bases) == 0:
        # No eligible bases, therefore given may be a Generic but it has nothing to
        # do with the specific given generic
        return False

    for base in eligible_bases:
        # for each base, get __args__
        given_args = base.__args__

        # Don't think is possible, but check this nonetheless
        if len(expected_args) != len(given_args):
            continue

        # Each arg of base must be a matching type for the corresponding
        # expected arg
        for given_arg, expected_arg in zip(given_args, expected_args):
            if not type_is_valid(given_arg, expected_arg):
                break
        else:
            # All types were valid, this is OK, we found a match
            return True

    # Couldn't find any matches
    return False


def is_generic(t):
    """
    Checks if t is a subclass of typing.Generic. The implementation
    is done per Python version, as the typing module has changed over time.

    Args:
        t (type):
    
    Returns:
        bool
    """
    # Python 3.7
    if hasattr(typing, "_GenericAlias"):
        if isinstance(t, typing._GenericAlias):
            return True
        if isinstance(t, typing._SpecialForm):
            return t not in (typing.Any,)

        return False
    else:
        # Python 3.6, 3.5
        if isinstance(t, typing.GenericMeta):
            return True

    return False


def is_type_var(t):
    """
    Checks if t is a typing.TypeVar

    Args:
        t (type):
    
    Returns:
        bool
    """
    return isinstance(t, TypeVar)


def is_union(t):
    """
    Checks if t is a typing.Union

    Args:
        t (type):
    
    Returns:
        bool
    """
    return hasattr(t, "__origin__") and t.__origin__ is Union
