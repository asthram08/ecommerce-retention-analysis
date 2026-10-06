# Metric definitions

All metrics use the cleaned data (duplicates, bad prices, missing sessions,
and shared sessions removed).

**Session:** all events with the same `user_session`.

**Order:** a session with at least one purchase event.
Order value = sum of price for purchase events in that session.

**First visit:** a user's earliest event of any type.

**Cohort:** users grouped by the week (Monday start) of their first visit.
October 2019 cohorts are excluded because those users may have visited
before the data starts.

**Active user (week N):** a user with at least one event of any type
in week N after their cohort week.

**Retention (week N):** active users in week N / users in the cohort.
Only compared for weeks every cohort has data for.

**Funnel conversion:** percent of sessions that reach each step:
view, then cart, then purchase. A session "reaches" a step if it has
at least one event of that type, in any order.

**Repeat buyer:** a user with 2 or more orders.
**One-time buyer:** a user with exactly 1 order.

**Time to first purchase:** days from first visit to first order.
Groups: same day, 1 to 7 days, 8+ days.

**Price band:** low (under $5), mid ($5 to $15), high (over $15).