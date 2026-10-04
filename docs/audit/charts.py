"""Audit charts for CityPulse (light + dark SVG) from the CSVs in data/, exported from the marts on 2026-10-04.

uv run --with matplotlib python docs/audit/charts.py docs/img
"""

import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

DATA = Path(__file__).parent / "data"
OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "series": "#2a78d6",
        "wash": "#2a78d6",
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#ffffff",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "series": "#3987e5",
        "wash": "#3987e5",
    },
}

plt.rcParams.update(
    {
        "font.family": ["Helvetica", "Arial", "DejaVu Sans"],
        "svg.fonttype": "none",
        "font.size": 11,
    }
)


def read(name):
    with open(DATA / f"{name}.csv") as f:
        return list(csv.DictReader(f))


def frame(fig, ax, t, title, subtitle):
    fig.patch.set_facecolor(t["surface"])
    for a in ax if isinstance(ax, (list, tuple)) else [ax]:
        a.set_facecolor(t["surface"])
        for side in ("top", "right", "left"):
            a.spines[side].set_visible(False)
        a.spines["bottom"].set_color(t["axis"])
        a.tick_params(colors=t["muted"], length=0, labelsize=10)
    fig.text(0.012, 0.965, title, color=t["ink"], fontsize=14, fontweight="bold", va="top")
    fig.text(0.012, 0.885, subtitle, color=t["ink2"], fontsize=10.5, va="top")


def note(fig, t, text):
    fig.text(0.012, 0.02, text, color=t["muted"], fontsize=9, va="bottom")


# ── 1. Coverage: which days reached the marts ────────────────────────────────
def coverage(mode):
    t = THEMES[mode]
    rows = [
        ("Weather", read("weather_daily")),
        ("Air quality", read("aq_daily")),
        ("Citi Bike trips", read("mobility_daily")),
    ]
    fig, ax = plt.subplots(figsize=(10, 3.4))
    fig.subplots_adjust(left=0.13, right=0.985, top=0.70, bottom=0.2)
    frame(
        fig,
        ax,
        t,
        "Where the pipeline actually has data",
        "Each tick is one day present in the marts. Loads stop on 3 Jun 2026; the GCP project's billing is now off.",
    )
    for y, (label, recs) in enumerate(reversed(rows)):
        days = [date.fromisoformat(r["date"]) for r in recs]
        ax.broken_barh([(mdates.date2num(d), 0.8) for d in days], (y - 0.3, 0.6), facecolors=t["series"], linewidth=0)
    ax.set_yticks(range(3), [r[0] for r in reversed(rows)], color=t["ink2"], fontsize=10.5)
    ax.set_ylim(-0.7, 2.7)
    ax.set_xlim(mdates.date2num(date(2024, 12, 20)), mdates.date2num(date(2026, 6, 25)))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=(1, 4, 7, 10)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="x", color=t["grid"], linewidth=1)
    ax.set_axisbelow(True)
    ax.text(
        mdates.date2num(date(2025, 6, 15)),
        1,
        "no data loaded\nFeb – Oct 2025",
        ha="center",
        va="center",
        color=t["muted"],
        fontsize=10,
    )
    ax.annotate(
        "Nov 2025 starts on the 14th:\nonly 1 of 4 CSV files was read",
        xy=(mdates.date2num(date(2025, 11, 14)), 0),
        xytext=(mdates.date2num(date(2025, 8, 20)), -0.05),
        color=t["ink2"],
        fontsize=9.5,
        va="center",
        ha="center",
        arrowprops={"arrowstyle": "-", "color": t["muted"], "linewidth": 1},
    )
    note(fig, t, "Source: citypulse_marts daily_* tables, exported 2026-10-04.")
    fig.savefig(OUT / f"coverage-{mode}.svg", facecolor=t["surface"])
    plt.close(fig)


# ── 2. Citi Bike: share of each month that was loaded ────────────────────────
def citibike_share(mode):
    t = THEMES[mode]
    members = defaultdict(list)
    for r in read("citibike_zip_members"):
        members[r["month"]].append(r)
    loaded = {f"{r['year']}{int(r['month']):02d}": int(r["rows_loaded"]) for r in read("citibike_loaded")}
    months, shares, files = [], [], []
    for m, recs in members.items():
        total = sum(int(r["uncompressed_bytes"]) for r in recs)
        first = int(recs[0]["uncompressed_bytes"])  # the processor read the first CSV in archive order
        months.append(date(int(m[:4]), int(m[4:]), 1).strftime("%b %Y"))
        shares.append(100 * first / total)
        files.append(len(recs))
        assert loaded[m] > 0
    fig, ax = plt.subplots(figsize=(10, 3.8))
    fig.subplots_adjust(left=0.06, right=0.985, top=0.72, bottom=0.24)
    frame(
        fig,
        ax,
        t,
        "Only 12–82% of each month's Citi Bike trips reached BigQuery",
        "Each monthly ZIP holds 2–4 CSV files; the processor read just the first one listed in the archive.",
    )
    ax.set_xlim(-0.6, len(shares) - 0.4)
    ax.set_ylim(0, 100)
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    px_x = bbox.width / (len(shares) - 0.2)  # pixels per x unit
    px_y = bbox.height / 100  # pixels per y unit
    width = 24 / px_x  # 24px bars
    r = 4 / px_x  # 4px rounded data-end, in x units
    for i, s in enumerate(shares):
        x0 = i - width / 2
        ax.add_patch(
            FancyBboxPatch(
                (x0, 0),
                width,
                s,
                boxstyle=f"round,pad=0,rounding_size={r}",
                mutation_aspect=px_x / px_y,
                facecolor=t["series"],
                linewidth=0,
            )
        )
        ax.add_patch(Rectangle((x0, 0), width, s / 2, facecolor=t["series"], linewidth=0))  # square base
        ax.text(i, s + 3, f"{s:.0f}%", ha="center", va="bottom", color=t["ink"], fontsize=11, fontweight="bold")
        ax.text(i, -6, f"{months[i]}\n1 of {files[i]} files", ha="center", va="top", color=t["ink2"], fontsize=10)
    ax.set_xticks([])
    ax.set_yticks([0, 25, 50, 75, 100], ["0%", "25%", "50%", "75%", "100%"])
    ax.grid(axis="y", color=t["grid"], linewidth=1)
    ax.set_axisbelow(True)
    note(
        fig,
        t,
        "Share of uncompressed CSV bytes per month (≈ share of trips). ZIP listings read from s3://tripdata on 2026-10-04.",
    )
    fig.savefig(OUT / f"citibike-loaded-{mode}.svg", facecolor=t["surface"])
    plt.close(fig)


# ── 3. Daily temperature and AQI (small multiples, no dual axis) ─────────────
def series(name, col, start):
    xs, ys, prev = [], [], None
    for r in read(name):
        d = date.fromisoformat(r["date"])
        if d < start:
            continue
        if prev and d - prev > timedelta(days=1):
            xs.append(prev + timedelta(days=1))
            ys.append(float("nan"))  # break the line on gaps
        xs.append(d)
        ys.append(float(r[col]))
        prev = d
    return xs, ys


def daily_conditions(mode):
    t = THEMES[mode]
    start = date(2025, 11, 1)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True)
    fig.subplots_adjust(left=0.07, right=0.985, top=0.80, bottom=0.12, hspace=0.45)
    frame(
        fig,
        [a1, a2],
        t,
        "Every month with bike data was a winter month",
        "Daily NYC conditions, Nov 2025 – Jun 2026. Citi Bike data exists only for Nov–Feb, all below 8 °C on average.",
    )
    for ax, (name, col, label) in (
        (a1, ("weather_daily", "temp_avg_c", "Mean temperature (°C)")),
        (a2, ("aq_daily", "aqi_avg", "Mean US AQI")),
    ):
        xs, ys = series(name, col, start)
        ax.axvspan(date(2025, 11, 1), date(2026, 3, 1), color=t["wash"], alpha=0.10, linewidth=0)
        ax.plot(xs, ys, color=t["series"], linewidth=2, solid_capstyle="round", solid_joinstyle="round")
        ax.set_title(label, loc="left", color=t["ink2"], fontsize=10.5, pad=4)
        ax.grid(axis="y", color=t["grid"], linewidth=1)
        ax.set_axisbelow(True)
    a1.axhline(0, color=t["axis"], linewidth=1)
    a1.text(
        date(2026, 1, 1),
        a1.get_ylim()[1] * 0.92,
        "months with Citi Bike data",
        ha="center",
        va="top",
        color=t["ink2"],
        fontsize=9.5,
    )
    a2.xaxis.set_major_locator(mdates.MonthLocator())
    a2.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    note(fig, t, "Source: citypulse_marts daily_weather_summary and daily_air_quality_summary (Open-Meteo).")
    fig.savefig(OUT / f"daily-conditions-{mode}.svg", facecolor=t["surface"])
    plt.close(fig)


for mode in THEMES:
    coverage(mode)
    citibike_share(mode)
    daily_conditions(mode)
print("ok", sorted(p.name for p in OUT.iterdir()))
