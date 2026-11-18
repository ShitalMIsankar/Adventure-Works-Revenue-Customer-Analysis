/* ================================================================
   ADVENTURE WORKS - MYSQL ANALYSIS QUERIES
   Database: adventure_works
   Tables loaded by the Jupyter ETL notebook:
     sales, product, dim_customer, dim_sales_territory, dim_date

   IMPORTANT:
   The column names below follow the notebook's cleaning rule:
   lowercase + replace non-alphanumeric characters with underscores.
   CamelCase source headers become lowercase without added underscores.
   ================================================================ */

-- 1. Select the project database
USE adventure_works;

-- 2. List tables
SHOW TABLES;

-- 3. Check table structures
DESCRIBE sales;
DESCRIBE product;
DESCRIBE dim_customer;
DESCRIBE dim_sales_territory;
DESCRIBE dim_date;

-- 4. Check total number of records in each table
SELECT 'sales' AS table_name, COUNT(*) AS total_rows FROM sales
UNION ALL
SELECT 'product', COUNT(*) FROM product
UNION ALL
SELECT 'dim_customer', COUNT(*) FROM dim_customer
UNION ALL
SELECT 'dim_sales_territory', COUNT(*) FROM dim_sales_territory
UNION ALL
SELECT 'dim_date', COUNT(*) FROM dim_date;

-- 5. Preview records
SELECT * FROM sales LIMIT 10;
SELECT * FROM product LIMIT 10;
SELECT * FROM dim_customer LIMIT 10;
SELECT * FROM dim_sales_territory LIMIT 10;
SELECT * FROM dim_date LIMIT 10;

-- 6. Check NULL values in important sales columns
SELECT
    SUM(productkey IS NULL) AS missing_productkey,
    SUM(customerkey IS NULL) AS missing_customerkey,
    SUM(salesordernumber IS NULL) AS missing_salesordernumber,
    SUM(salesorderlinenumber IS NULL) AS missing_salesorderlinenumber,
    SUM(orderquantity IS NULL) AS missing_orderquantity,
    SUM(unitprice IS NULL) AS missing_unitprice,
    SUM(extendedamount IS NULL) AS missing_extendedamount
FROM sales;

-- 7. Check duplicate sales transaction lines
SELECT
    salesordernumber,
    salesorderlinenumber,
    COUNT(*) AS duplicate_count
FROM sales
GROUP BY salesordernumber, salesorderlinenumber
HAVING COUNT(*) > 1
ORDER BY duplicate_count DESC;

-- 8. Check duplicate dimension keys
SELECT productkey, COUNT(*) AS key_count
FROM product
GROUP BY productkey
HAVING COUNT(*) > 1;

SELECT customerkey, COUNT(*) AS key_count
FROM dim_customer
GROUP BY customerkey
HAVING COUNT(*) > 1;

SELECT salesterritorykey, COUNT(*) AS key_count
FROM dim_sales_territory
GROUP BY salesterritorykey
HAVING COUNT(*) > 1;

SELECT datekey, COUNT(*) AS key_count
FROM dim_date
GROUP BY datekey
HAVING COUNT(*) > 1;

-- 9. Overall sales performance
SELECT
    COUNT(*) AS total_sales_lines,
    COUNT(DISTINCT salesordernumber) AS total_orders,
    SUM(orderquantity) AS total_quantity_sold,
    ROUND(SUM(extendedamount), 2) AS total_sales_amount,
    ROUND(SUM(discountamount), 2) AS total_discount_amount,
    ROUND(SUM(taxamt), 2) AS total_tax,
    ROUND(SUM(freight), 2) AS total_freight
FROM sales;

-- 10. Sales by year
SELECT
    YEAR(orderdate) AS sales_year,
    COUNT(DISTINCT salesordernumber) AS total_orders,
    SUM(orderquantity) AS quantity_sold,
    ROUND(SUM(extendedamount), 2) AS total_sales
FROM sales
WHERE orderdate IS NOT NULL
GROUP BY YEAR(orderdate)
ORDER BY sales_year;

-- 11. Monthly sales trend
SELECT
    DATE_FORMAT(orderdate, '%Y-%m') AS sales_month,
    COUNT(DISTINCT salesordernumber) AS total_orders,
    ROUND(SUM(extendedamount), 2) AS total_sales
FROM sales
WHERE orderdate IS NOT NULL
GROUP BY DATE_FORMAT(orderdate, '%Y-%m')
ORDER BY sales_month;

-- 12. Top 10 products by sales amount
SELECT
    p.productkey,
    p.englishproductname,
    SUM(s.orderquantity) AS units_sold,
    ROUND(SUM(s.extendedamount), 2) AS total_sales
FROM sales AS s
INNER JOIN product AS p
    ON s.productkey = p.productkey
GROUP BY p.productkey, p.englishproductname
ORDER BY total_sales DESC
LIMIT 10;

-- 13. Sales by product category
SELECT
    p.englishproductcategoryname AS product_category,
    SUM(s.orderquantity) AS units_sold,
    ROUND(SUM(s.extendedamount), 2) AS total_sales
FROM sales AS s
INNER JOIN product AS p
    ON s.productkey = p.productkey
GROUP BY p.englishproductcategoryname
ORDER BY total_sales DESC;

-- 14. Sales by territory
SELECT
    t.salesterritoryregion,
    t.salesterritorycountry,
    t.salesterritorygroup,
    COUNT(DISTINCT s.salesordernumber) AS total_orders,
    ROUND(SUM(s.extendedamount), 2) AS total_sales
FROM sales AS s
LEFT JOIN dim_sales_territory AS t
    ON s.salesterritorykey = t.salesterritorykey
GROUP BY
    t.salesterritoryregion,
    t.salesterritorycountry,
    t.salesterritorygroup
ORDER BY total_sales DESC;

-- 15. Top 10 customers by sales amount
SELECT
    c.customerkey,
    CONCAT_WS(' ', c.firstname, c.middlename, c.lastname) AS customer_name,
    COUNT(DISTINCT s.salesordernumber) AS total_orders,
    ROUND(SUM(s.extendedamount), 2) AS total_sales
FROM sales AS s
INNER JOIN dim_customer AS c
    ON s.customerkey = c.customerkey
GROUP BY c.customerkey, customer_name
ORDER BY total_sales DESC
LIMIT 10;

-- 16. Average order value
SELECT
    ROUND(SUM(order_total) / NULLIF(COUNT(*), 0), 2) AS average_order_value
FROM (
    SELECT salesordernumber, SUM(extendedamount) AS order_total
    FROM sales
    GROUP BY salesordernumber
) AS order_summary;

-- 17. Discount analysis
SELECT
    CASE
        WHEN unitpricediscountpct = 0 THEN 'No Discount'
        WHEN unitpricediscountpct > 0 THEN 'Discount Applied'
        ELSE 'Unknown / Missing'
    END AS discount_status,
    COUNT(*) AS sales_lines,
    ROUND(SUM(extendedamount), 2) AS total_sales,
    ROUND(SUM(discountamount), 2) AS total_discount
FROM sales
GROUP BY discount_status;

-- 18. Check invalid negative quantity or price values
SELECT COUNT(*) AS negative_quantity_rows
FROM sales
WHERE orderquantity < 0;

SELECT COUNT(*) AS negative_unit_price_rows
FROM sales
WHERE unitprice < 0;

-- 19. Check sales records with unmatched product/customer/territory keys
SELECT COUNT(*) AS unmatched_product_keys
FROM sales AS s
LEFT JOIN product AS p ON s.productkey = p.productkey
WHERE p.productkey IS NULL;

SELECT COUNT(*) AS unmatched_customer_keys
FROM sales AS s
LEFT JOIN dim_customer AS c ON s.customerkey = c.customerkey
WHERE c.customerkey IS NULL;

SELECT COUNT(*) AS unmatched_territory_keys
FROM sales AS s
LEFT JOIN dim_sales_territory AS t
    ON s.salesterritorykey = t.salesterritorykey
WHERE s.salesterritorykey IS NOT NULL
  AND t.salesterritorykey IS NULL;

-- 20. Sales by customer country/region is not included because the
-- customer table in this workbook links through geographykey, and no
-- geography dimension is loaded by this ETL notebook.
