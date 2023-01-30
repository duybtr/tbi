  -- Load expense
CREATE TABLE expense_tmp (address char(50), unit char(20), year int, month int, expense_type char(50), amount double precision, note char(500), verified char(5));
\copy expense_tmp FROM 'monthly_expenses.csv' DELIMITER ',' CSV HEADER;

DROP TABLE expense_type_mappings;
CREATE TABLE expense_type_mappings(sys_value char(50), tmp_value char(50));
INSERT INTO expense_type_mappings VALUES 
('repair_maintenance','Repair & Maint.'),
('misc', 'Misc'),
('gas', 'Gas'),
('commission', 'Commission'),
('landscaping', 'Landscaping'),
('taxes_and_fees', 'Taxes & Fees'),
('management_fee', 'Management Fee'),
('insurance', 'Insurance'),
('water', 'Water'),
('trash', 'Trash'),
('roof', 'Roof'),
('power', 'Power'),
('advertising', 'Advertising');

  DROP SEQUENCE record_seq;
    DROP SEQUENCE expense_tmp_seq;
    CREATE SEQUENCE record_seq;
    SELECT setval('record_seq', (SELECT MAX(id) FROM transactions_record));
    CREATE SEQUENCE expense_tmp_seq;
    SELECT setval('expense_tmp_seq', currval('record_seq'));

    WITH full_address AS (
        SELECT ru.id AS rental_unit_id, CONCAT(address, ' ', suite) full_address FROM transactions_rental_unit ru INNER JOIN transactions_property p 
        ON ru.address_id = p.id
    ),
    expense_tmp_with_ids AS (
        SELECT nextval('expense_tmp_seq') AS id, CONCAT(trim(address), ' ', trim(unit)) AS full_address, * FROM expense_tmp INNER JOIN expense_type_mappings ON expense_type = tmp_value WHERE expense_type = 'Advertising'
    ),
    inserted_record_ids AS (
        INSERT INTO transactions_record(id, record_date, amount, note, date_filed, address_id, author_id) 
        SELECT nextval('record_seq') AS id, MAKE_DATE(year, month, 1) AS record_date, et.amount, et.note, now(), fa.rental_unit_id, 1 
        FROM expense_tmp_with_ids et 
        LEFT JOIN fulL_address fa ON et.full_address = fa.full_address
        RETURNING id
    )
    INSERT INTO transactions_expense(record_ptr_id, expense_type)
    SELECT r.id, et.sys_value
    FROM expense_tmp_with_ids et

--  Load revenue
DROP TABLE revenue_tmp;
CREATE TABLE revenue_tmp (address char(50), suite char(20), month int, year int, rent double precision, reimbursement double precision, note char(500));
\copy revenue_tmp FROM 'tbi_revenue.csv' DELIMITER ',' CSV HEADER;
DELETE FROM revenue_tmp WHERE year IN (2022,2021);

DROP SEQUENCE record_seq;
DROP SEQUENCE revenue_tmp_seq;
CREATE SEQUENCE record_seq;
SELECT setval('record_seq', (SELECT MAX(id) FROM transactions_record));
CREATE SEQUENCE revenue_tmp_seq;
SELECT setval('revenue_tmp_seq', currval('record_seq'));

WITH full_address AS (
SELECT ru.id AS rental_unit_id, CONCAT(address, ' ', suite) full_address FROM transactions_rental_unit ru INNER JOIN transactions_property p 
ON ru.address_id = p.id
),
revenue_tmp_with_ids AS (
    SELECT nextval('revenue_tmp_seq') AS id, CONCAT(trim(address), ' ', trim(suite)) AS full_address, * FROM revenue_tmp_unpivoted
),
inserted_record_ids AS (
    INSERT INTO transactions_record(id, record_date, amount, note, date_filed, address_id, author_id) 
    SELECT nextval('record_seq') AS id, MAKE_DATE(year, month, 1) AS record_date, et.amount, et.note, now(), fa.rental_unit_id, 1 
    FROM revenue_tmp_with_ids et 
    LEFT JOIN fulL_address fa ON et.full_address = fa.full_address
    RETURNING id
)
INSERT INTO transactions_revenue(record_ptr_id, revenue_type)
SELECT r.id, rt.revenue_type
FROM revenue_tmp_with_ids rt
INNER JOIN inserted_record_ids r ON rt.id = r.id;


