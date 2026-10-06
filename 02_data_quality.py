import duckdb

con = duckdb.connect("data/shop.duckdb", read_only=True)

def show(title, query):
    print(f"\n== {title} ==")
    print(con.sql(query))

show("Date range", """
SELECT MIN(event_time) AS first_event, MAX(event_time) AS last_event
FROM raw_events
""")

show("Unique counts", """
SELECT COUNT(DISTINCT user_id)      AS users,
       COUNT(DISTINCT user_session) AS sessions,
       COUNT(DISTINCT product_id)   AS products,
       COUNT(DISTINCT brand)        AS brands
FROM raw_events
""")

show("Missing values (percent of rows)", """
SELECT ROUND(100.0 * COUNT_IF(user_session  IS NULL) / COUNT(*), 2) AS session_missing,
       ROUND(100.0 * COUNT_IF(brand         IS NULL) / COUNT(*), 2) AS brand_missing,
       ROUND(100.0 * COUNT_IF(category_code IS NULL) / COUNT(*), 2) AS category_missing,
       ROUND(100.0 * COUNT_IF(price         IS NULL) / COUNT(*), 2) AS price_missing,
       ROUND(100.0 * COUNT_IF(user_id       IS NULL) / COUNT(*), 2) AS user_missing
FROM raw_events
""")

show("Exact duplicate rows", """
SELECT (SELECT COUNT(*) FROM raw_events)
     - (SELECT COUNT(*) FROM (SELECT DISTINCT * FROM raw_events)) AS duplicate_rows
""")

show("Prices by event type", """
SELECT event_type,
       COUNT_IF(price <= 0)     AS zero_or_negative,
       ROUND(MIN(price), 2)     AS min_price,
       ROUND(MEDIAN(price), 2)  AS median_price,
       ROUND(MAX(price), 2)     AS max_price
FROM raw_events
GROUP BY 1 ORDER BY 1
""")

show("Sessions shared by more than one user", """
SELECT COUNT(*) AS sessions FROM (
    SELECT user_session FROM raw_events
    WHERE user_session IS NOT NULL
    GROUP BY 1 HAVING COUNT(DISTINCT user_id) > 1
)
""")

show("Sessions with a purchase but no cart", """
SELECT COUNT(*) AS sessions FROM (
    SELECT user_session FROM raw_events
    GROUP BY 1
    HAVING COUNT_IF(event_type = 'purchase') > 0
       AND COUNT_IF(event_type = 'cart') = 0
)
""")

con.close()