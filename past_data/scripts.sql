-- Load expense
CREATE TABLE expense_tmp (address char(50), unit char(20), year int, month int, expense_type char(50), amount double precision, note char(500), verified char(5));
\copy expense_tmp FROM 'monthly_expenses.csv' DELIMITER ',' CSV HEADER;


UPDATE expense_tmp SET address='6135 Cupertino Trl' WHERE address='6135 Cupertino Trail';
UPDATE expense_tmp SET unit = '' WHERE unit = 'All';
UPDATE expense_tmp SET unit = 'D1' WHERE unit = 'D1 and D2';

INSERT INTO transactions_rental_unit (suite, address_id, is_available) VALUES
('D3', 7, False);
INSERT INTO transactions_property (address,purchase_price,full_address,market_price) VALUES 
('8061 19th St',0,'',0),
('16591 Rhone Ln',0,'',0);
INSERT INTO transactions_rental_unit (suite, address_id, is_available) VALUES
('',20, False),
('',21, False);

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

UPDATE revenue_tmp SET reimbursement = rent, rent=0 WHERE suite='Reimbursement';
UPDATE revenue_tmp SET suite = '' WHERE suite='Reimbursement';

DROP TABLE revenue_tmp_unpivoted;
CREATE TABLE revenue_tmp_unpivoted AS
SELECT address, suite, month, year, 
    unnest(array['rent', 'reimb']) AS revenue_type, 
    unnest(array[rent, reimbursement]) AS amount, note 
    FROM revenue_tmp;

DELETE FROM revenue_tmp_unpivoted WHERE amount IS NULL;

INSERT INTO transactions_rental_unit(suite, address_id, is_available) VALUES
('D', 7, False);

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

-- Test scripts
SELECT year,COUNT(1) FROM expense_tmp GROUP BY year;
SELECT address, year,COUNT(1) FROM expense_tmp WHERE year=2019 GROUP BY address, year ORDER BY address;

SELECT date_part('year', record_date), COUNT(1) FROM transactions_record WHERE id IN (SELECT record_ptr_id FROM transactions_expense) GROUP BY date_part('year', record_date)

SELECT p.address, date_part('year', record_date), COUNT(1) FROM transactions_record r
INNER JOIN transactions_rental_unit ru ON r.address_id = ru.id
INNER JOIN transactions_property p ON ru.address_id = p.id 
WHERE date_part('year', record_date) = 2019 AND r.id IN (SELECT record_ptr_id FROM transactions_expense) GROUP BY p.address, date_part('year', record_date) ORDER BY p.address


SELECT COUNT(1) FROM revenue_tmp_unpivotted GROUP BY year;
SELECT date_part('year', record_date), COUNT(1) FROM transactions_record WHERE id IN (SELECT record_ptr_id FROM transactions_revenue) GROUP BY date_part('year', record_date)