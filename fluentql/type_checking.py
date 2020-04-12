from collections import defaultdict
from operator import itemgetter
import typing
from typing import Any, TypeVar, Union


class TypeCheckingError(Exception):
    pass


class TypeChecker:
    def __init__(self, given, expected):
        """
        Raises ValueError if given and expected don't have the
        same lengths.

        Args:
            given (type|tuple(type)): Types to validate
            expected (type|tuple(type)): Types to validate against
        """
        given = tuple(given)
        expected = tuple(expected)

        if len(given) != len(expected):
            raise ValueError("Given and expected must have the same length")

        self._given = given
        self._expected = expected
        self._matched_types = None

    def validate(self):
        matched_types = []

        # Get type matches for each individual argument
        for index, (given, expected) in enumerate(zip(self._given, self._expected)):
            type_match = get_type_match(given, expected)

            if type_match is None:
                raise TypeError(
                    f"Invalid type for argument {index}: expected {expected}, found {given}."
                )

            matched_types.append(type_match)

        # Resolve TypeVar mappings
        self._type_var_mapping = resolve_type_vars(self._given, matched_types)

        # Check that all type vars were successfully resolved
        for type_var, (indices, resolved_type) in self._type_var_mapping.items():
            if resolved_type is None:
                given_types = [self._given[i] for i in indices]
                raise TypeError(
                    f"Invalid types supplied for TypeVar {type_var} for arguments {indices}: expected one of {type_var.__constraints__}, found {given_types}"
                )

        # Resolve TypeVars using the map
        final_types = apply_type_var_mapping(self._type_var_mapping, matched_types)

        self._matched_types = final_types


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


def apply_type_var_mapping(mapping, matched_types):
    """
    Applies a type var mapping, as returned by resolve_type_vars,
    to a given list of types. Returns the resulting list.
    
    Args:
        mapping (dict):
        matched_types (list(type)):
    
    Returns:
        list(type)
    """
    resolved_types = list(matched_types)

    for type_var, (indices, resolved_type) in mapping.items():
        for i in indices:
            if is_generic(matched_types[i]):
                base = matched_types[i].__base__
                resolved_types[i] = base[resolved_type]
            else:
                resolved_types[i] = resolved_type

    return resolved_types


def resolve_type_vars(given_types, matched_types):
    """
    Resolves TypeVar to concrete types and returns a dict of
    mappings from TypeVar to the concrete type, as well as a list
    of indices of TypeVar occurances in given_types and matched_types.

    Args:
        given_types (list(type)): Given types, as provided, for example,
            in a function call.
        matched_types (list(type)): Types of the argument matching, as returned by
            get_type_match, for given_types.
    
    Returns:
        dict(TypeVar, Tuple(list, type)):
            Values are tuples, where the first element is a list of indices
            and the second is a type.
    """
    # Group matched_types by their use of TypeVar
    type_var_groups = get_typevar_groups(matched_types)

    mapping = {}

    for type_var, type_var_group in type_var_groups.items():
        if len(type_var_group) == 1:
            resolved_type = resolve_type_var(
                type_var,
                [given_types[type_var_group[0]]],
                [matched_types[type_var_group[0]]],
            )
        else:
            get_types = itemgetter(*type_var_group)
            resolved_type = resolve_type_var(
                type_var, list(get_types(given_types)), list(get_types(matched_types))
            )

        mapping[type_var] = (type_var_group, resolved_type)

    return mapping


def find_type_match(given, expected):
    """
    Find a type match in expected (list of eligible types) for given.
    Returns None if there is no match.

    Args:
        given (type):
        expected (list(type)):
    
    Returns:
        type or None
    """
    for t in expected:
        if type_is_valid(given, t):
            return t

    return None


def resolve_type_var(type_var, given_types, matched_types):
    """
    Resolves TypeVars to a concrete type and returns those types. Returns
    None if the validation fails.

    Args:
        given_types (list(type)): Types of given arguments
        matched_types (list(type)): Types matched to the given_type, as returned
            by get_type_match
    
    Returns:
        list(type) or None
    """
    # Is the TypeVar a ResolvedTypeVar?
    is_constrained_type_var = len(type_var.__constraints__) > 0

    # Index types of T
    type_var_types = []

    for given_type, matched_type in zip(given_types, matched_types):
        if is_generic(matched_type):
            arg = get_generic_properties(given_type)[1][0]
            if is_constrained_type_var:
                type_var_type = find_type_match(arg, type_var.__constraints__)
                type_var_types.append(type_var_type)
            else:
                type_var_types.append(arg)

        elif is_constrained_type_var:
            type_var_type = find_type_match(given_type, type_var.__constraints__)
            type_var_types.append(type_var_type)

        else:
            type_var_types.append(given_type)

    if is_constrained_type_var:
        if len(set(type_var_types)) == 1:
            return type_var_types[0]
    else:
        gcs = greatest_common_superclass(*type_var_types)

        if gcs is not None:
            return gcs

    return None


def get_typevar_groups(types):
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
            # For generics, we need to check if they have
            # any TypeVar args
            if is_type_var(t.__args__[0]):
                type_var_groups[t.__args__[0]].append(i)

    return dict(type_var_groups)


def get_type_match(given, expected):
    """
    Get type in expected that given matched to::
        - if given is Any, expected is returned
        - if expected is Any, given is returned
        - if given is a subclass/instance of expected, it is returned
        - if expected is a TypeVar:
            - if restricted, return MatchedTypeVar(expected, matched_type)
            - otherwise, return expected
        - if expected is Union, return the type in expected to which
        given matches
        - if expected is Generic, GenericType[matched_type] is returned, where
        GenericType is the instance of Generic in expected

    Args:
        given (type):
        expected (type):
    
    Returns:
        type or None
    """
    # Any matches all
    if expected is Any:
        return given
    if given is Any:
        return expected

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
            t = find_type_match(given, matching_types)

            if t is not None:
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
                return type_match

    # Is this a Generic?
    if is_generic(expected):
        generic_type_match = get_generic_type_match(given, expected)

        if generic_type_match is not None:
            return generic_type_match

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


def get_generic_type_match(given, expected):
    """
    Compares two typing.Generic types, given and expected, and returns:
        - instance of generic base with the actual matched arguments, as returned
        by get_matched_type
        - None if the given doesn't match expected

    This function assumes that the Generic type has only one argument

    Args:
        given (type):
        expected (Generic):
    
    Returns:
        bool
    """
    assert len(expected.__args__) == 1, "Only 1-arg Generics are supported"

    # Get the base and arg
    expected_origin = expected.__origin__
    expected_arg = expected.__args__[0]

    # Quick check: given must be a subclass of expected origin
    if not issubclass(given, expected_origin):
        return None

    # Traverse __orig_bases__ until we find at least one reference to expected
    # origin
    eligible_bases = [
        base
        for base in [given, *given.__orig_bases__]
        if hasattr(base, "__origin__") and base.__origin__ is expected_origin
    ]

    if len(eligible_bases) == 0:
        # No eligible bases, therefore given may be a Generic but it has nothing to
        # do with the specific given generic
        return None

    for base in eligible_bases:
        # Ensure that this has one arg as well
        if len(base.__args__) != 1:
            continue

        # Get the arg
        given_arg = base.__args__[0]

        # Check that given_arg matches expected_arg
        matched_type = get_type_match(given_arg, expected_arg)

        # Return the same generic but of the matched type
        if matched_type is not None:
            return base.__origin__[matched_type]

    # Couldn't find any matches
    return None


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


def greatest_common_superclass(*types):
    """
    Finds the greatest common superclass of the given *types.
    Returns None if the types are unrelated.

    Args:
        *types (type):
    
    Returns:
        type or None
    """
    if len(types) == 1:
        return types[0]

    mros = [t.__mro__ for t in types]

    for t in mros[0]:
        if all(t in mro for mro in mros[1:]):
            break
    else:
        return None

    if t is object:
        return None

    return t
