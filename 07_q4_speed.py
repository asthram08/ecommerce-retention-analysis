import duckdb

con = duckdb.connect("data/shop.duckdb", read_only=True)

# One row per user: days from first visit to first purchase,
# and whether the first purchase happened in the very first session.
con.sql("""
CREATE TEMP TABLE speed AS
WITH first_order AS (
    SELECT user_id, arg_min(order_id, order_time) AS first_order_id
    FROM orders
    GROUP BY user_id
)
SELECT u.user_id,
       u.buyer_type,
       u.first_visit,
       u.first_order_time,
       date_diff('day', u.first_visit, u.first_order_time) AS days_to_buy,
       f.first_order_id = u.first_session                  AS bought_first_session,
       CASE WHEN u.first_order_time IS NULL                                THEN NULL
            WHEN f.first_order_id = u.first_session                        THEN 'a. first visit'
            WHEN date_diff('day', u.first_visit, u.first_order_time) = 0   THEN 'b. same day, later visit'
            WHEN date_diff('day', u.first_visit, u.first_order_time) <= 7  THEN 'c. 1 to 7 days'
            WHEN date_diff('day', u.first_visit, u.first_order_time) <= 30 THEN 'd. 8 to 30 days'
            ELSE 'e. 31+ days' END AS speed
FROM users u
LEFT JOIN first_order f USING (user_id)
WHERE u.first_visit >= DATE '2019-11-01'
""")

# Part A: when do new shoppers make their first purchase?
# Only users who first visited in Nov or Dec, so everyone had 60+ days to buy.
when_buy = con.sql("""
WITH n AS (
    SELECT CASE WHEN first_order_time IS NULL OR days_to_buy > 60 THEN 'f. not within 60 days'
                WHEN speed = 'e. 31+ days' THEN 'e. 31 to 60 days'
                ELSE speed END AS speed
    FROM speed
    WHERE first_visit < DATE '2020-01-01'
),
counts AS (
    SELECT speed, COUNT(*) AS users FROM n GROUP BY 1
)
SELECT speed,
       users,
       ROUND(100.0 * users / SUM(users) OVER (), 2) AS pct_of_new_users,
       CASE WHEN speed <> 'f. not within 60 days'
            THEN ROUND(100.0 * users / SUM(users) FILTER (WHERE speed <> 'f. not within 60 days') OVER (), 1)
       END AS pct_of_buyers
FROM counts
ORDER BY speed
""")
when_buy.write_csv("results/q4_when_first_purchase.csv")

# Part B: does speed matter? Repeat rate by time to first purchase.
# Same fairness filter as Q3: first order before Feb 1 (4+ weeks to buy again).
repeat_by_speed = con.sql("""
SELECT speed,
       COUNT(*) AS buyers,
       ROUND(100.0 * AVG((buyer_type = 'repeat')::INT), 1) AS repeat_rate_pct
FROM speed
WHERE first_order_time < DATE '2020-02-01'
GROUP BY 1
ORDER BY 1
""")
repeat_by_speed.write_csv("results/q4_repeat_by_speed.csv")

summary = con.sql("""
SELECT buyer_type,
       COUNT(*)                                         AS buyers,
       MEDIAN(days_to_buy)                              AS median_days_to_buy,
       ROUND(AVG(days_to_buy), 1)                       AS avg_days_to_buy,
       ROUND(100.0 * AVG(bought_first_session::INT), 1) AS pct_bought_first_visit
FROM speed
WHERE first_order_time < DATE '2020-02-01'
GROUP BY 1
ORDER BY 1
""")

print("\n== Part A: when new shoppers make their first purchase (Nov to Dec visitors) ==")
print(when_buy)
print("\n== Part B: repeat rate by time to first purchase ==")
print(repeat_by_speed)
print("\n== Days to first purchase: repeat vs one-time buyers ==")
print(summary)

con.close()