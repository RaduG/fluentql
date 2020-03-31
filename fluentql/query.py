class Query:
    def __init__(self, target):
        """
        Args:
            target (object): Target object with a 'name' parameter.
        """
        self._target = target

    def select(self, *columns):
        pass


class SelectQuery:
    def __init__(self, target, *columns):
        self._target = target
        self._columns = columns


class WhereQuery:
    def __init__(self, *conditions):
        self._conditions = conditions


class GroupByQuery:
    def __init__(self, *groups):
        self._groups = groups


class JoinQuery:
    def __init__(self, type_, target):
        self._type = type_
        self._target = target


class OnQuery:
    def __init__(self, *conditions):
        self._conditions = conditions


class On
