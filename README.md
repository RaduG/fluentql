## Status

**PLEASE NOTE THAT THIS IS A WORK IN PROGRESS PROJECT THAT HAS NOT YET BEEN RELEASED TO PYPI.**

|                                            Build                                            |                                                                         Coverage                                                                         | Release |
| :-----------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----: |
| ![Build#develop](https://github.com/RaduG/fluentql/workflows/build/badge.svg?branch=master) | [![Coverage Status](https://coveralls.io/repos/github/RaduG/fluentql/badge.svg?branch=master)](https://coveralls.io/github/RaduG/fluentql?branch=master) |   N/A   |

## Introduction

> 
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

#### Defining Schemas [TODO]
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

#### Using SqlAlchemy Models [TODO]
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
from fluentql import Q, Table


books = Table("books")
Q.select().from_(books)
```
Compiles to:
```sql
select * from books;
```

#### Selecting Specific Columns
By default, as seen in the previous example, calling select() without arguments produces a select all.

To select specific columns:

```python
Q.select([books["id"], books["title"]]).from_(books)
```
Compiles to:
```sql
select id, title from books;
```
#### Aliases
```python
Q.select([books["id"], (books["title"], "book_title")]).from_(books)
```
Compiles to:
```sql
select id, title as book_title from books;
```

#### Where Clause

```python
Q.select().from_(books).where(books["price"], ">", 100)
```
Compiles to
```sql
select * from books where price > 100;
```

You can chain where clauses using *and_where* and *or_where*:
```python
(
    Q.select()
    .from_(books)
    .where(books["price"], ">", 100)
    .and_where(books["title"], "like", "%cars%")
)
```
Compiles to
```sql
select * from books where price > 100 and title like '%cars%';
```

You can also build more complex *where* clauses by using a lambda function that returns a Query object, like so:
```python
(
    Q.select()
    .from_(books)
    .where(books["title"], "like", "%cars%")
    .or_where(lambda q: q.where(books["title"], "like", "%cooking%").and_where(books["price"] < 10))
)
```
Compiles to
```sql
select * from books where title like '%cars%' or (title like '%cooking%' and price < 10);
```

#### Joins
```python
(
    Q.select([books.all(), (authors["books_published"], "n_books_published")])
    .from_(books)
    .inner_join(authors, lambda join: join.on(books["author_id"], "=", authors["id"]))
)
```
Compiles to
```sql
select books.*, authors.books_published as n_books_published from books inner join authors on books.author_id = authors.id;
```

When a query targets more than one table, as it happens with a join, then all references to column names are compiled to their full name, including the parent table.

The following join functions are available:
- inner_join
- outer_join
- left_join
- right_join
- cross_join (this one only takes one argument - the table to join with)

You can also chain multiple calls to *on* and its helpers *and_on* and *or_on* like so:
```python
(
    Q.select([books.all(), authors.all()])
    .from_(books)
    .left_join(
        authors,
        lambda join: join.on(books["author_id"], "=", authors["id"]).and_on(
            authors["id"],
            "in",
            Q.select([best_sellers["author_id"]]).from_(best_sellers),
        ),
    )
)
```
Compiles to:
```sql
select books.*, authors.* from books left join authors on books.author_id = authors.id and authors.id in (select best_sellers.author_id from best_sellers);
```

You can also join using a... *using* clause:

```python
(
    Q.select([books.all(), authors.all()])
    .from_(books)
    .left_join(authors, lambda join: join.using("author_id"))
)
```
Compiles to:
```sql
select books.*, authors.* from books left join authors using (author_id);
```