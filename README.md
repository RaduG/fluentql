## Status

**FLUENTQL IS WORK IN PROGRESS. WHILE IT IS AVAILABLE ON PYPI, USE IT WITH CAUTION. PUBLIC APIS MAY CHANGE UNEXPECTEDLY WHILE FEATURES ARE ADDED AT PACE.**

|                                            Build                                             |                                                                          Coverage                                                                          | Release |
| :------------------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----: |
| ![Build#develop](https://github.com/RaduG/fluentql/workflows/build/badge.svg?branch=develop) | [![Coverage Status](https://coveralls.io/repos/github/RaduG/fluentql/badge.svg?branch=develop)](https://coveralls.io/github/RaduG/fluentql?branch=develop) |   N/A   |

## Introduction

> 
FluentQL is a lightweight, fast and intuitive Python SQL query builder. It helps you build cross-dialect queries straight in your code, as well as test and validate your queries.

Using SqlAlchemy and Pandas? FluentQL seamlessly integrates with your existing codebase, providing type checking capabilities out of the box.

## Getting Started
Fluentql requires Python 3.5 and up.

```bash
pip install fluentql
```

## Quick overview
```python
from fluentql import GenericSQLDialect, Q, Table

table1 = Table("table1")
table2 = Table("table2")

query = (
    Q.select(table1.all(), table2["col_x"])
    .set_from(table1)
    .left_join(table2, lambda q: q.on(table1["id"] == table2["id"]))
    .order_by(table1["col_y"])
    .fetch(10)
    .distinct()
)

compiled_query = query.compile(GenericSQLDialect)

print(compiled_query)
```
will output
```
select distinct table1.*, table2.col_x from table1 left join table2 on table1.id = table2.id order by col_y limit 10;
```

## Supported SQL Dialects
There are many varieties of SQL out there, and while FluentQL comes with popular dialects implemented out of the box, you might need additional functionality for your use case. This library was built with extensibility in mind, so you can easily extend an existing Dialect implementation or implement your own. No only that, but you can roll out your custom functions with ease.

FluentQL includes the following dialect implementations:
- Generic SQL - should provide compatibility with a variety of dialects for basic queries
- Microsoft SQL (coming soon)
- PosgreSQL (coming soon)
- Teradata (coming soon)


## Usage
### Overview
Fluentql comes with a built-in runtime type checking system based on Python's typing module and PEP484 type annotations. However, by default, all types are *Any*, thus giving users control over how much they want type checking to be used.

If using type checking, errors are thrown as queries are constructed if types don't match, such as when adding a string column to a number column, or when using SUM on a Date column. 

The core logical units of fluentql are:
* Column
* Table
* Function
* Query
* Dialect


### Column

A column has a *name* and a *type* and it is bound to a *table*. The base class Column should never be instantiated on its own; the correct way to create a column that holds a numeric type is as follows:

```python
from fluentql.base_types import Collection
from fluentql.types import Column, NumberType


class NumberColumn(Collection[NumberType], Column):
    pass
```
Or just use ```fluentql.types.NumberColumn```.

The ```Generic``` type```Collection``` provides the functionality required by the type checking engine and it is simply a subclass of ```typing.Generic```.

Fluentql comes with a number of concrete column types in ```fluentql.types```:
* AnyColumn
* BooleanColumn
* DateColumn
* DateTimeColumn
* NumberColumn
* StringColumn
* TimeColumn

Those implementations are based on their base type counterparts found in ```fluentql.base_types```:
* BooleanType
* DateTime
* DateTimeType
* NumberType
* StringType
* TimeType


### Table
Tables are used as targets for Queries and as containers for columns. That does not mean you need to define a schema, as you will see below. Tables can have schemas, but by default they hold any column:

```python
from fluentql import Table

books = Table("books")
```

In this case, ```books``` is a table that will pass ```AnyColumn``` columns of a given name when asked, like so:

```python
book_id = books["id"] # Instance of AnyColumn
title = books["title"] # Instance of AnyColumn
```

However, tables can have schemas. Schemas can be defined using PEP484 type hints, like so:


```python
from fluentql import Table
from fluentql.types import BooleanColumn, NumberColumn, StringColumn


class Books(Table):
    id: NumberColumn
    title: StringColumn
    is_available: BooleanColumn

    def __init__(self, db=None):
        super().__init__("books", db)

books = Books()
```

Then, reference the columns as normal:
```python
title = books["title"] # Instance of StringColumn
```

However, now, this raises a KeyError:
```python
release_date = books["release_date"]
```

#### Using SqlAlchemy Models [TODO]
```python
from fluentql import Table

from project.models import MySqlAlchemyModel

# MySqlAlchemyModel is a subclass of DeclarativeBase
table = Table.from_model(MySqlAlchemyModel)
```
The table name and schema are automatically copied from the model class.


### Functions

Functions are the most important units in fluentql. They *implement* (well, semantically only) various functionalities of SQL and are the main interface between queries and the type checking system.

The base class for all functions is ```fluentql.F```. The theory is:
* a function takes 0 or more arguments of a given type
* a function returns a typed value

Let's look at a couple of examples. First, let's imagine a function CoolFunction that takes two Boolean columns as arguments and returns a Boolean column:

```python
from fluentql import F
from fluentql.base_types import BooleanType, Collection


class CoolFunction(F):
    a: Collection[BooleanType]
    b: Collection[BooleanType]
    returns: Collection[BooleanType]
```
*Note: the arguments a and b must be provided in order, as you expect the function to be called; however, their name is irrelevant. The only name that matters here is returns, that will always be used as the return type*

Remember, there is no functionality associated to CoolFunction, meaning that it's purpose is not to be called with two booleans and return a value after applying some logic - the snippet above is all there is to it. However, let's assume that our hypothetical SQL dialect actually has this function, and we'd call it like so:

```sql
select * from my_table where CoolFunction(boolcol1, boolcol2) = True;
```

Fluentql wants to tell you when the query you're building doesn't really make sense (meaning that it's not type safe). 

```python
class Books(Table):
    id: NumberColumn
    title: StringColumn
    is_on_sale: BooleanColumn
    is_sold_out: BooleanColumn

books = Books()
```

So, while this is OK:
```
CoolFunction(books["is_on_sale"], books["is_sold_out"])
```
this is not:
```
CoolFunction(books["is_on_sale"], books["title"]) # raises TypeError
```
and neither is this:
```
CoolFunction(books["is_on_sale"]) # raises TypeError
```

Let's take this one step further and look at a function Add that takes either scalars or columns of type String and Number:

```python
from typing import TypeVar

T = TypeVar("T", NumberType, StringType)


class Add(F):
    arg1: Union[T, Collection[T]] # scalar or collection
    arg2: Union[T, Collection[T]] # scalar or collection
    returns: Union[T, Collection[T]] # scalar or collection
```
This behaves as you'd expect a TypeVar to behave. You can pass it two Numbers, two NumberColumns, or one of each (same for Strings and StringColumn). However, the return type is quite vague, so let's enhance this.

*Note: When a ```F``` is instantiated, all the types are checked and ran through the typing engine. Each instance of F will have a __type_checker__ object which holds details about the types that were matched, including a mapping from all the TypeVars found in the expected arg types list to concrete types that were matched against the given values. Explore ```fluentql.type_checking.TypeChecker``` to get a better feel of it.*

Instead of passing a type annotation for ```returns```, we can create a function. This function must take ```matched_types``` and ```type_var_mapping``` as its only arguments. 

```matched_types``` is a list of types that the given arguments matched against the expected type definition. Effectively, if our arg of type ```A``` is matched against ```Union[A, B]```, the matched type for it will be A. The reference here is against the expected type, not the given type, so if we instead saw ```Union[AS, B]```, where ```AS``` is a superclass of ```A```, the matched type would've been ```AS```. There's obviously a bit more to it, but it's easy to think of it as a *Union unpacker*.

```type_var_mapping``` is a dict, where keys are TypeVars and the value is a tuple of two elements: the first is a list of argument indices, showing which arguments in our list were actually matched against that TypeVar; the second is the concrete type that *resolves* the TypeVar for that specific function call.

So, back to our example, we can be a bit smarter with our Add function and determine exactly what it will return, like so:

```python
class Add(F):
    arg1: Union[T, Collection[T]] # scalar or collection
    arg2: Union[T, Collection[T]] # scalar or collection
    
    def returns(self, matched_types, type_var_mapping):
        # Get the type that resolved T
        t_type = type_var_mapping[T][1]

        # If any of the arguments is an instance of Collection
        # Please note that isinstance behaviour is inconsistent with tying.Generic subtypes, hence this unusual check
        if any(Collection in t.__mro__ for t in matched_types if hasattr(t, "__mro__")):
            return Collection[t_type]
        
        return t_type
```

Now, we can observe:

```python
nc1 = NumberColumn("nc1")
nc2 = NumberColumn("nc2")

a1 = Add(nc1, nc2) # a1.__returns__ is Collection[NumberType]
a2 = Add(nc1, 100) # a2.__returns__ is Collection[NumberType]
a3 = Add(200, 300) # a3.__returns__ is NumberType
a4 = Add(nc1, "abc") # TypeError: T was not matched
```
    

*more coming soon*