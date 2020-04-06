from collections import defaultdict
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
    types_group = group_arg_types(expected_types)

    for t, indices in types_group.items():
        for i in indices:
            if not type_is_valid(args[i], t):
                if raise_error:
                    raise_type_error(parent_name, i, t, args[i])
                else:
                    return False

        # Now we need to look at groups, specifically for TypeVars
        if isinstance(t, TypeVar) and len(indices) > 1:
            # All TypeVars must strictly match by type or be subtypes of each other
            if not all(
                type_is_valid(args[indices[0]], args[indices[i]])
                or type_is_valid(args[indices[i]], args[indices[0]])
                for i in indices[1:]
            ):
                if raise_error:
                    raise_generic_type_mismatch(
                        parent_name, indices, [type(args[i]) for i in indices]
                    )
                else:
                    return False
    return True


def group_arg_types(types):
    """
    Convers a list of arg types to a dict where types are keys
    and the values are the indices in types where a specific type
    was found. This is required in order to process TypeVars.

    Args:
        types (list(type)):
    
    Returns:
        dict
    """
    # Create a copy of types
    types = list(types)

    types_group = defaultdict(lambda: [])

    for i, t in enumerate(types):
        types_group[t].append(i)

    return dict(types_group)


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
    # Any matches all
    if expected is Any or given is Any:
        return True

    # First, try perfect match
    if given is expected:
        return True

    # Try nicer ways for non-Type variables
    try:
        # Then, try subclass
        if issubclass(given, expected):
            return True

        # Then, try isinstance
        if isinstance(given, expected):
            return True

    except TypeError:
        pass

    # Is this a TypeVar?
    if isinstance(expected, TypeVar):
        matching_types = expected.__constraints__

        # If the TypeVar has type constraints, check against those. If there are none,
        # the all() call will return True
        if all(type_is_valid(given, t) for t in matching_types):
            return True

    # Is this a Union?
    if hasattr(expected, "__origin__") and expected.__origin__ is Union:
        matching_types = expected.__args__

        # Get the types part of Union and check against those
        if any(type_is_valid(given, t) for t in matching_types):
            return True

    # Is this a Generic?
    if is_generic(expected):
        if is_generic_subclass(given, expected):
            return True

    return False


def is_generic_subclass(given, expected):
    """
    Checks if given implements expected, which is assumed to be
    a subclass of typing.Generic. The validation is done down to
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
