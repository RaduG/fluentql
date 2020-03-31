Target use:

table1 = Table("table_name")
table2 = Table("table2_name")


table1().select().where(
    table1.c("abc").isin(
        table2().select(table2.c("name")).where(table2.c("date") <= "2019-01-01")
    )
)
=>
select * from table1
where abc in (
    select name from table2
    where date <= "2019-01-01"
);

