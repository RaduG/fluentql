## Introduction

FluentQL is a lightweight, fast and intuitive Python SQL query builder. It helps you build cross-dialect queries straight in your code, as well as test and validate your queries.

Using SqlAlchemy and Pandas? FluentQL seamlessly integrates with your existing codebase, providing type checking capabilities out of the box.

## Supported SQL Dialects
There are many varieties of SQL out there, and while FluentQL comes with popular dialects implemented out of the box, you might need additional functionality for your use case. This library was built with extensibility in mind, so you can easily extend an existing Dialect implementation or implement your own. No only that, but you can roll out your custom functions with ease.

FluentQL includes the following dialect implementations:
- Microsoft SQL
- PosgreSQL
- Teradata

## Installation
FluentQL has no external dependencies, so no matter what platform you're on you should be good to go once installing via pip. Keep in mind that FluentQL is only actively being tested on CPython 3.6 and above and while it may work for other versions or implementations, it is not guaranteed to do so.

```bash
pip install fluentql
```

## Usage
### Column
A column has a *name* and a *type* and it is bound to a *table*. By default, a Column has the Any type. You should not have to create a Column manually, but you can do so like this:

```python
from fluentql import Column
from fluentql.column import Any

col = Column("age", Any)
```
### Table
Tables are used as targets for Queries and as containers for columns. That does not mean you need to define a schema, as you will see below.

#### Basic usage
```python
from fluentql import Table

books = Table("books")
```
The snippet above only creates a Table object, pointing to a table called *books* in your database. Think of this as a schema-less table.

You can access columns in two ways:

```python
books.column("title")
# Or, shorter
books["title"]
```
Even though we didn't define a schema, FluentQL assumes we know what we're doing and automatically creates columns of type Any (the default type) as we reference them.

To define a schema, you must subclass Table and use PEP484 type hints, like so:

#### Defining Schemas
```python
from fluentql.column import String, Float, Integer

class Books(Table):
    id: Integer
    title: String
    qty: Integer
    price: Float

books = Books()
```

Then, reference the columns as normal:

```python
books.column("title")
# Or
books["title"]
```

#### Using SqlAlchemy Models
```python
from fluentql import Table

from project.models import MySqlAlchemyModel

# MySqlAlchemyModel is a subclass of DeclarativeBase
table = Table.from_model(MySqlAlchemyModel)
```
The table name and schema are automatically copied from the model class.

### SELECT queries

#### Basic
```python
from fluentql import Query, Table


books = Table("books")
Query(books).select()
```
Compiles to:
```sql
select * from books;
```

#### Selecting Specific Columns
By default, as seen in the previous example, calling select() without arguments produces a select all.

To select specific columns:

```python
Query(books).select([books["id"], books["title"]])
```
Compiles to:
```sql
select id, title from books;
```
#### Aliases
```python
Query(books).select([books["id"], (books["title"], "book_title")])
```
Compiles to:
```sql
select id, title as book_title from books;
```





