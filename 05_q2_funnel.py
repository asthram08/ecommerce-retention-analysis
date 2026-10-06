import duckdb

con = duckdb.connect("data/shop.duckdb", read_only=True)

# Part A: session funnel (view -> cart -> purchase)
funnel = con.sql("""
WITH s AS (
    SELECT COUNT(*)                                                   AS total,
           COUNT_IF(views > 0)                                        AS v,
           COUNT_IF(views > 0 AND carts > 0)                          AS vc,
           COUNT_IF(views > 0 AND carts > 0 AND purchased_items > 0)  AS vcp
    FROM sessions
)
SELECT '1. viewed a product' AS step, v AS sessions,
       ROUND(100.0 * v / total, 2) AS pct_of_all_sessions,
       NULL::DOUBLE AS pct_of_previous_step
FROM s
UNION ALL
SELECT '2. added to cart', vc, ROUND(100.0 * vc / total, 2), ROUND(100.0 * vc / NULLIF(v, 0), 2) FROM s
UNION ALL
SELECT '3. purchased', vcp, ROUND(100.0 * vcp / total, 2), ROUND(100.0 * vcp / NULLIF(vc, 0), 2) FROM s
ORDER BY step
""")
funnel.write_csv("results/q2_session_funnel.csv")

# Side check: sessions that skip steps (tracking gaps)
gaps = con.sql("""
SELECT COUNT(*)                                    AS all_sessions,
       COUNT_IF(views = 0)                         AS no_view_at_all,
       COUNT_IF(carts > 0 AND views = 0)           AS cart_without_view,
       COUNT_IF(purchased_items > 0 AND carts = 0) AS purchase_without_cart
FROM sessions
""")

# Part B: product-level funnel, so we can split by price and brand.
# One row per (session, product): was it viewed, carted, purchased?
con.sql("""
CREATE TEMP TABLE sp AS
SELECT user_session, product_id,
       ANY_VALUE(brand)                  AS brand,
       AVG(price)                        AS price,
       BOOL_OR(event_type = 'view')      AS viewed,
       BOOL_OR(event_type = 'cart')      AS carted,
       BOOL_OR(event_type = 'purchase')  AS purchased
FROM events_clean
GROUP BY 1, 2
""")

by_price = con.sql("""
SELECT CASE WHEN price < 5   THEN '1. low (under $5)'
            WHEN price <= 15 THEN '2. mid ($5 to $15)'
            ELSE                  '3. high (over $15)' END AS price_band,
       COUNT_IF(viewed) AS products_viewed,
       ROUND(100.0 * COUNT_IF(viewed AND carted)    / COUNT_IF(viewed), 2)            AS view_to_cart_pct,
       ROUND(100.0 * COUNT_IF(carted AND purchased) / NULLIF(COUNT_IF(carted), 0), 2) AS cart_to_purchase_pct,
       ROUND(100.0 * COUNT_IF(viewed AND purchased) / COUNT_IF(viewed), 2)            AS view_to_purchase_pct
FROM sp
GROUP BY 1
ORDER BY 1
""")
by_price.write_csv("results/q2_funnel_by_price.csv")

by_brand = con.sql("""
SELECT brand,
       COUNT_IF(viewed) AS products_viewed,
       ROUND(100.0 * COUNT_IF(viewed AND carted)    / COUNT_IF(viewed), 2)            AS view_to_cart_pct,
       ROUND(100.0 * COUNT_IF(carted AND purchased) / NULLIF(COUNT_IF(carted), 0), 2) AS cart_to_purchase_pct,
       ROUND(100.0 * COUNT_IF(viewed AND purchased) / COUNT_IF(viewed), 2)            AS view_to_purchase_pct
FROM sp
GROUP BY 1
ORDER BY products_viewed DESC
LIMIT 11
""")
by_brand.write_csv("results/q2_funnel_by_brand.csv")

print("\n== Session funnel ==")
print(funnel)
print("\n== Sessions that skip steps ==")
print(gaps)
print("\n== Product funnel by price band ==")
print(by_price)
print("\n== Product funnel, top brands by views ==")
print(by_brand)

con.close()