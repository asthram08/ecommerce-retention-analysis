import duckdb

con = duckdb.connect("data/shop.duckdb", read_only=True)

# Weekly retention for each cohort (first-visit week).
# October cohorts are left out: those users may have visited before the data starts.
by_cohort = con.sql("""
WITH cohorts AS (
    SELECT user_id, cohort_week
    FROM users
    WHERE cohort_week >= DATE '2019-11-04'
),
activity AS (
    SELECT DISTINCT user_id, date_trunc('week', session_start) AS active_week
    FROM sessions
),
sizes AS (
    SELECT cohort_week, COUNT(*) AS cohort_size
    FROM cohorts GROUP BY 1
)
SELECT c.cohort_week,
       s.cohort_size,
       date_diff('day', c.cohort_week, a.active_week) // 7 AS week_number,
       COUNT(DISTINCT c.user_id) AS active_users,
       ROUND(100.0 * COUNT(DISTINCT c.user_id) / s.cohort_size, 2) AS retention_pct
FROM cohorts c
JOIN activity a USING (user_id)
JOIN sizes s USING (cohort_week)
GROUP BY 1, 2, 3
ORDER BY 1, 3
""")
by_cohort.write_csv("results/q1_retention_by_cohort.csv")

# Overall retention curve: for each week N, only count cohorts that have
# had N full weeks of data, so late cohorts don't drag the average down.
con.sql("CREATE TEMP TABLE r AS SELECT * FROM read_csv('results/q1_retention_by_cohort.csv')")
curve = con.sql("""
WITH sizes AS (SELECT DISTINCT cohort_week, cohort_size FROM r),
last_week AS (SELECT MAX(date_trunc('week', session_start)) AS w FROM sessions)
SELECT n.week_number,
       COUNT(*)                         AS cohorts_included,
       SUM(s.cohort_size)               AS users,
       SUM(COALESCE(r.active_users, 0)) AS active_users,
       ROUND(100.0 * SUM(COALESCE(r.active_users, 0)) / SUM(s.cohort_size), 2) AS retention_pct
FROM sizes s
CROSS JOIN range(0, 13) n(week_number)
LEFT JOIN r ON r.cohort_week = s.cohort_week AND r.week_number = n.week_number
WHERE s.cohort_week + to_days(CAST(n.week_number * 7 AS INTEGER)) <= (SELECT w FROM last_week)
GROUP BY 1
ORDER BY 1
""")
curve.write_csv("results/q1_retention_curve.csv")

print("\n== Overall retention curve (weeks 0 to 12) ==")
print(curve)

# Cohort table: rows = cohort week, columns = week number, values = % retained
df = by_cohort.df()
df["cohort_week"] = df["cohort_week"].dt.date
table = df.pivot(index=["cohort_week", "cohort_size"], columns="week_number", values="retention_pct")
print("\n== Retention % by cohort (weeks 1 to 12) ==")
print(table.loc[:, 1:12].to_string(na_rep=""))

con.close()