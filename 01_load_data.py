import duckdb

con = duckdb.connect("data/shop.duckdb")

con.sql("""
CREATE OR REPLACE TABLE raw_events AS
SELECT
    strptime(replace(event_time, ' UTC', ''), '%Y-%m-%d %H:%M:%S') AS event_time,
    event_type, product_id, category_id, category_code,
    brand, price, user_id, user_session
FROM read_csv('data/*.csv', header = true, columns = {
    'event_time': 'VARCHAR', 'event_type': 'VARCHAR',
    'product_id': 'BIGINT', 'category_id': 'BIGINT',
    'category_code': 'VARCHAR', 'brand': 'VARCHAR',
    'price': 'DOUBLE', 'user_id': 'BIGINT', 'user_session': 'VARCHAR'
})
""")

print(con.sql("SELECT COUNT(*) AS total_rows FROM raw_events"))
print(con.sql("""
    SELECT strftime(event_time, '%Y-%m') AS month, COUNT(*) AS rows
    FROM raw_events GROUP BY 1 ORDER BY 1
"""))
print(con.sql("""
    SELECT event_type, COUNT(*) AS rows
    FROM raw_events GROUP BY 1 ORDER BY 2 DESC
"""))

con.close()