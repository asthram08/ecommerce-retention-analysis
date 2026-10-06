import duckdb

con = duckdb.connect("data/shop.duckdb")

# 1. events_clean: raw events with the problems from Step 3 removed
con.sql("""
CREATE OR REPLACE TABLE events_clean AS
WITH dedup AS (
    SELECT DISTINCT * FROM raw_events
),
shared_sessions AS (
    SELECT user_session FROM dedup
    WHERE user_session IS NOT NULL
    GROUP BY 1 HAVING COUNT(DISTINCT user_id) > 1
)
SELECT event_time, event_type, product_id, category_id,
       COALESCE(brand, 'unknown') AS brand,
       price, user_id, user_session
FROM dedup
WHERE user_session IS NOT NULL
  AND price > 0
  AND user_session NOT IN (SELECT user_session FROM shared_sessions)
""")

# 2. sessions: one row per session
con.sql("""
CREATE OR REPLACE TABLE sessions AS
SELECT user_session,
       user_id,
       MIN(event_time) AS session_start,
       MAX(event_time) AS session_end,
       COUNT_IF(event_type = 'view')             AS views,
       COUNT_IF(event_type = 'cart')             AS carts,
       COUNT_IF(event_type = 'remove_from_cart') AS removes,
       COUNT_IF(event_type = 'purchase')         AS purchased_items,
       COUNT(DISTINCT product_id) FILTER (WHERE event_type = 'view') AS products_viewed,
       COUNT(DISTINCT brand)      FILTER (WHERE event_type = 'view') AS brands_viewed,
       COALESCE(SUM(price) FILTER (WHERE event_type = 'purchase'), 0) AS revenue
FROM events_clean
GROUP BY user_session, user_id
""")

# 3. orders: one row per session that has a purchase
con.sql("""
CREATE OR REPLACE TABLE orders AS
SELECT user_session    AS order_id,
       user_id,
       MIN(event_time) AS order_time,
       COUNT(*)        AS items,
       SUM(price)      AS order_value
FROM events_clean
WHERE event_type = 'purchase'
GROUP BY user_session, user_id
""")

# 4. users: one row per user
con.sql("""
CREATE OR REPLACE TABLE users AS
WITH visits AS (
    SELECT user_id,
           MIN(session_start) AS first_visit,
           MAX(session_end)   AS last_visit,
           COUNT(*)           AS total_sessions,
           arg_min(user_session, session_start) AS first_session
    FROM sessions
    GROUP BY user_id
),
buys AS (
    SELECT user_id,
           COUNT(*)         AS orders,
           MIN(order_time)  AS first_order_time,
           SUM(order_value) AS total_spend
    FROM orders
    GROUP BY user_id
)
SELECT v.*,
       date_trunc('week', v.first_visit) AS cohort_week,
       COALESCE(b.orders, 0)      AS orders,
       b.first_order_time,
       COALESCE(b.total_spend, 0) AS total_spend,
       CASE WHEN b.orders >= 2 THEN 'repeat'
            WHEN b.orders = 1  THEN 'one_time'
            ELSE 'never_bought' END AS buyer_type
FROM visits v
LEFT JOIN buys b USING (user_id)
""")

# Sanity checks
print(con.sql("""
SELECT 'raw_events'   AS table_name, COUNT(*) AS rows FROM raw_events   UNION ALL
SELECT 'events_clean', COUNT(*) FROM events_clean UNION ALL
SELECT 'sessions',     COUNT(*) FROM sessions     UNION ALL
SELECT 'orders',       COUNT(*) FROM orders       UNION ALL
SELECT 'users',        COUNT(*) FROM users
"""))

print(con.sql("""
SELECT buyer_type, COUNT(*) AS users,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM users GROUP BY 1 ORDER BY 2 DESC
"""))

print(con.sql("""
SELECT (SELECT COUNT(*) FROM events_clean WHERE event_type = 'purchase') AS purchase_events,
       (SELECT SUM(items) FROM orders)                                    AS items_in_orders
"""))

con.close()