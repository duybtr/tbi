-- transactions_record
-- id | record_date | amount | document_image | note | date_filed | address_id | author_id | file_name
----+-------------+--------+----------------+------+------------+------------+-----------+-----------

-- transactions_revenue
-- record_ptr_id | revenue_type
---------------+--------------

-- transactions_expense
-- record_ptr_id | expense_type | raw_invoice_id
---------------+--------------+----------------

-- transactions_rental_unit
-- id | suite | address_id
----+-------+------------

-- transactions_property
-- id | address | market_price
----+---------+--------------

-- database info
-- 


SELECT rec.record_date, p.address, ru.suite, rec.amount, rec.note, 'Revenue' AS accounting_classification, rev.revenue_type AS category FROM transactions_record rec 
    INNER JOIN transactions_revenue rev ON rec.id = rev.record_ptr_id
    INNER JOIN transactions_rental_unit ru ON rec.address_id = ru.id
    INNER JOIN transactions_property p ON ru.address_id = p.id
UNION
SELECT rec.record_date, p.address, ru.suite, -1*rec.amount AS amount, rec.note, 'Expense' AS accounting_classification, exp.expense_type AS category FROM transactions_record rec 
    INNER JOIN transactions_expense exp ON rec.id = exp.record_ptr_id
    INNER JOIN transactions_rental_unit ru ON rec.address_id = ru.id
    INNER JOIN transactions_property p ON ru.address_id = p.id;