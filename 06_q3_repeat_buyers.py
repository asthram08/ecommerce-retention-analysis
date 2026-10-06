import duckdb

con = duckdb.connect("data/shop.duckdb", read_only=True)

# Buyers to compare. Two filters keep the comparison fair:
#  - first visit on or after Nov 1, so "first session" is really their first
#  - first order before Feb 1, so everyone had at least 4 weeks to buy again
con.sql("""
CREATE TEMP TABLE buyers AS
WITH b AS (
    SELECT * FROM users
    WHERE orders >= 1
      AND first_visit      >= DATE '2019-11-01'
      AND first_order_time <  DATE '2020-02-01'
),
first_order AS (
    SELECT user_id,
           arg_min(order_id,    order_time) AS order_id,
           arg_min(items,       order_time) AS items,
           arg_min(order_value, order_time) AS order_value
    FROM orders
    GROUP BY user_id
),
first_order_brands AS (
    SELECT e.user_session,
           COUNT(DISTINCT e.brand) FILTER (WHERE e.brand <> 'unknown') AS brands
    FROM events_clean e
    JOIN first_order f ON e.user_session = f.order_id
    WHERE e.event_type = 'purchase'
    GROUP BY 1
)
SELECT b.user_id,
       b.buyer_type,
       s.views                                             AS fs_views,
       s.products_viewed                                   AS fs_products_viewed,
       s.brands_viewed                                     AS fs_brands_viewed,
       s.carts                                             AS fs_carts,
       s.purchased_items > 0                               AS bought_in_first_session,
       date_diff('minute', s.session_start, s.session_end) AS fs_minutes,
       f.items                                             AS first_order_items,
       f.order_value                                       AS first_order_value,
       COALESCE(fb.brands, 0)                              AS first_order_brands
FROM b
JOIN sessions s           ON s.user_session = b.first_session
JOIN first_order f        ON f.user_id = b.user_id
LEFT JOIN first_order_brands fb ON fb.user_session = f.order_id
""")

# Part A: side-by-side comparison (medians, since these numbers are skewed)
compare = con.sql("""
SELECT buyer_type,
       COUNT(*)                                            AS buyers,
       MEDIAN(fs_views)                                    AS first_session_views,
       MEDIAN(fs_products_viewed)                          AS first_session_products,
       MEDIAN(fs_brands_viewed)                            AS first_session_brands,
       MEDIAN(fs_carts)                                    AS first_session_carts,
       MEDIAN(fs_minutes)                                  AS first_session_minutes,
       ROUND(100.0 * AVG(bought_in_first_session::INT), 1) AS pct_bought_first_session,
       MEDIAN(first_order_items)                           AS first_order_items,
       ROUND(MEDIAN(first_order_value), 2)                 AS first_order_value,
       MEDIAN(first_order_brands)                          AS first_order_brands
FROM buyers
GROUP BY 1
ORDER BY 1
""")
compare.write_csv("results/q3_compare.csv")

# Part B: repeat rate by first-order size, value and brands (looking for a tipping point)
by_items = con.sql("""
SELECT CASE WHEN first_order_items = 1   THEN 'a. 1 item'
            WHEN first_order_items <= 3  THEN 'b. 2 to 3'
            WHEN first_order_items <= 6  THEN 'c. 4 to 6'
            WHEN first_order_items <= 10 THEN 'd. 7 to 10'
            ELSE                              'e. 11+' END AS first_order_items,
       COUNT(*) AS buyers,
       ROUND(100.0 * AVG((buyer_type = 'repeat')::INT), 1) AS repeat_rate_pct
FROM buyers
GROUP BY 1 ORDER BY 1
""")
by_items.write_csv("results/q3_repeat_by_items.csv")

by_value = con.sql("""
SELECT CASE WHEN first_order_value < 10  THEN 'a. under $10'
            WHEN first_order_value < 25  THEN 'b. $10 to $25'
            WHEN first_order_value < 50  THEN 'c. $25 to $50'
            WHEN first_order_value < 100 THEN 'd. $50 to $100'
            ELSE                              'e. $100+' END AS first_order_value,
       COUNT(*) AS buyers,
       ROUND(100.0 * AVG((buyer_type = 'repeat')::INT), 1) AS repeat_rate_pct
FROM buyers
GROUP BY 1 ORDER BY 1
""")
by_value.write_csv("results/q3_repeat_by_value.csv")

by_brands = con.sql("""
SELECT CASE WHEN first_order_brands <= 1 THEN 'a. 0 to 1 brand'
            WHEN first_order_brands = 2  THEN 'b. 2 brands'
            WHEN first_order_brands <= 4 THEN 'c. 3 to 4 brands'
            ELSE                              'd. 5+ brands' END AS first_order_brands,
       COUNT(*) AS buyers,
       ROUND(100.0 * AVG((buyer_type = 'repeat')::INT), 1) AS repeat_rate_pct
FROM buyers
GROUP BY 1 ORDER BY 1
""")
by_brands.write_csv("results/q3_repeat_by_brands.csv")

print("\n== Repeat vs one-time buyers: first session and first order (medians) ==")
print(compare.df().set_index("buyer_type").T.to_string())
print("\n== Repeat rate by first-order size ==")
print(by_items)
print("\n== Repeat rate by first-order value ==")
print(by_value)
print("\n== Repeat rate by brands in first order ==")
print(by_brands)

con.close()