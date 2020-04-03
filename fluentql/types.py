from collections import defaultdict
from typing import TypeVar, Union


def raise_type_error(parent_name, arg_name, expected_type, found_type):
    raise TypeError(
        f"Argument {arg_name} for {parent_name}: expected {expected_type.__name__}, found {found_type.__name__}"
    )


def raise_generic_type_mismatch(parent_name, arg_names, found_types):
    raise TypeError(
        f"Arguments {', '.join([str(n) for n in arg_names])} of {parent_name} expected to have the same type. Found {', '.join([t.__name__ for t in found_types])}"
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
            # All TypeVars must strictly match by type
            if not all(
                type(args[indices[0]]) is type(args[indices[i]]) for i in indices[1:]
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
    if isinstance(expected, Union):
        matching_types = expected.__args__

        # Get the types part of Union and check against those
        if all(type_is_valid(given, t) for t in matching_types):
            return True

    return False
