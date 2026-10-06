import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ---- Shared style: light surface, quiet axes, one accent color ----
BLUE   = "#2a78d6"   # main series
ORANGE = "#eb6834"   # second series (only where two measures are compared)
GRAY   = "#b9b8b2"   # de-emphasized bars
INK    = "#0b0b0b"
INK_2  = "#52514e"
GRID   = "#e6e5e0"
BG     = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
    "xtick.color": INK_2, "ytick.color": INK_2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "text.parse_math": False,   # so "$5 to $15" prints as plain text
})

def strip_prefix(s):
    # "a. 1 item" -> "1 item"
    return s.split(". ", 1)[1] if ". " in s[:4] else s

def finish(fig, ax, title, subtitle, path):
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=28)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=INK_2, fontsize=10.5)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print("saved", path)


# ---- Q1a: retention curve ----
curve = pd.read_csv("results/q1_retention_curve.csv")
c = curve[curve.week_number >= 1]
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.plot(c.week_number, c.retention_pct, color=BLUE, linewidth=2, marker="o", markersize=5)
for w in (1, 4, 12):
    v = c.loc[c.week_number == w, "retention_pct"].iloc[0]
    ax.annotate(f"{v:.1f}%", (w, v), textcoords="offset points", xytext=(0, 9),
                ha="center", color=INK, fontsize=10)
ax.set_xticks(range(1, 13))
ax.set_xlabel("Weeks since first visit")
ax.set_ylabel("% of cohort active")
ax.set_ylim(0, 10)
ax.grid(axis="x", visible=False)
finish(fig, ax, "92% of new shoppers don't come back the next week",
       "Weekly retention, Nov 2019 to Feb 2020 cohorts. Levels off near 2% after week 7.",
       "charts/q1_retention_curve.png")


# ---- Q1b: cohort heatmap ----
bc = pd.read_csv("results/q1_retention_by_cohort.csv", parse_dates=["cohort_week"])
bc = bc[(bc.week_number >= 1) & (bc.week_number <= 12)]
grid = bc.pivot(index="cohort_week", columns="week_number", values="retention_pct")
grid.index = grid.index.strftime("%b %d")
cmap = LinearSegmentedColormap.from_list("blues", ["#eef4fc", "#9cc0ee", BLUE, "#123f78"])
cmap.set_bad(BG)
fig, ax = plt.subplots(figsize=(9, 6.5))
im = ax.imshow(grid.values, cmap=cmap, aspect="auto", vmin=0, vmax=grid.values[~pd.isna(grid.values)].max())
ax.set_xticks(range(grid.shape[1]), grid.columns)
ax.set_yticks(range(grid.shape[0]), grid.index)
ax.grid(False)
for s in ax.spines.values():
    s.set_visible(False)
for i in range(grid.shape[0]):
    for j in range(grid.shape[1]):
        v = grid.values[i, j]
        if pd.notna(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=8,
                    color="white" if v > im.norm.vmax * 0.55 else INK)
ax.set_xlabel("Weeks since first visit")
ax.set_ylabel("First-visit week")
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("% active", color=INK_2)
cb.outline.set_visible(False)
finish(fig, ax, "Every cohort drops fast; December cohorts drop the most",
       "% of each weekly cohort active N weeks later. Darker = more shoppers returned.",
       "charts/q1_cohort_heatmap.png")


# ---- Q2a: session funnel ----
f = pd.read_csv("results/q2_session_funnel.csv")
labels = [strip_prefix(s).capitalize() for s in f.step]
fig, ax = plt.subplots(figsize=(8, 3.8))
y = range(len(f))[::-1]
ax.barh(list(y), f.pct_of_all_sessions, color=BLUE, height=0.55)
for yi, (pct, prev) in zip(y, zip(f.pct_of_all_sessions, f.pct_of_previous_step)):
    note = f"{pct:.1f}% of sessions" + ("" if pd.isna(prev) else f"  ({prev:.1f}% of previous step)")
    ax.text(pct + 1.5, yi, note, va="center", fontsize=10, color=INK)
ax.set_yticks(list(y), labels)
ax.set_xlim(0, 135)
ax.set_xticks([0, 25, 50, 75, 100])
ax.set_xlabel("% of all sessions")
ax.grid(axis="y", visible=False)
finish(fig, ax, "Most shoppers leave before adding anything to cart",
       "Session funnel: view, then cart, then purchase. 4.5M sessions.",
       "charts/q2_funnel.png")


# ---- Q2b: price band, two conversion steps ----
p = pd.read_csv("results/q2_funnel_by_price.csv")
bands = [strip_prefix(s) for s in p.price_band]
x = range(len(p))
w = 0.36
fig, ax = plt.subplots(figsize=(8, 4.5))
b1 = ax.bar([i - w/2 - 0.01 for i in x], p.view_to_cart_pct, width=w, color=BLUE, label="Viewed, then added to cart")
b2 = ax.bar([i + w/2 + 0.01 for i in x], p.cart_to_purchase_pct, width=w, color=ORANGE, label="Added to cart, then bought")
for bars in (b1, b2):
    for b in bars:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.3, f"{b.get_height():.1f}%",
                ha="center", fontsize=10, color=INK)
ax.set_xticks(list(x), bands)
ax.set_ylabel("Conversion %")
ax.set_ylim(0, 22)
ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="upper right", labelcolor=INK_2)
finish(fig, ax, "Expensive items lose shoppers at the cart, not at checkout",
       "Product-level conversion by price band. Items over $15 are carted half as often.",
       "charts/q2_price_band.png")


# ---- Q3 and Q4: repeat rate bar charts ----
def repeat_bars(csv, col, title, subtitle, xlabel, path, highlight):
    d = pd.read_csv(csv)
    names = [strip_prefix(s) for s in d[col]]
    colors = [BLUE if i in highlight else GRAY for i in range(len(d))]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    names = [f"{nm}\n{n:,} buyers" for nm, n in zip(names, d.buyers)]
    bars = ax.bar(names, d.repeat_rate_pct, color=colors, width=0.6)
    for b in bars:
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.4, f"{b.get_height():.1f}%",
                ha="center", fontsize=10.5, color=INK, fontweight="bold")
    ax.set_ylabel("% who bought again")
    ax.set_xlabel(xlabel)
    ax.set_ylim(0, max(d.repeat_rate_pct) * 1.18)
    ax.grid(axis="x", visible=False)
    finish(fig, ax, title, subtitle, path)

repeat_bars("results/q3_repeat_by_items.csv", "first_order_items",
            "Bigger first orders, twice the repeat rate",
            "Repeat rate by number of items in the first order. Buyers with 4+ weeks to return.",
            "Items in first order", "charts/q3_repeat_by_items.png", highlight={0, 4})

repeat_bars("results/q4_repeat_by_speed.csv", "speed",
            "Impulse buyers are the least likely to return",
            "Repeat rate by time from first visit to first purchase.",
            "Time to first purchase", "charts/q4_repeat_by_speed.png", highlight={0, 3})