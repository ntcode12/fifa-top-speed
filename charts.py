"""FIFA World Cup 2026 — top speed charts, light explorative style."""

import numpy as np
import polars as pl
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import gaussian_kde

matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.spines.left":   False,
    "axes.spines.bottom": False,
    "xtick.major.size":   0,
    "ytick.major.size":   0,
})

# ── palette ───────────────────────────────────────────────────────────────────
BG      = "#f7f5f2"          # warm off-white
PANEL   = "#ffffff"
INK     = "#2b2b2b"          # near-black text
SUB     = "#888888"          # secondary text / axis labels
RULE    = "#e0ddd9"          # grid lines
STROKE  = "#d0cdc9"          # bar outlines / borders
BLUE    = "#5b8db8"          # primary accent — muted steel blue
CORAL   = "#d4745a"          # contrast accent — muted terracotta
SAGE    = "#6a9e7f"          # third accent
SAND    = "#c9a96e"          # warm highlight

ACCENT_SEQ = [BLUE, SAGE, SAND, CORAL]  # four-stop gradient for sequences

df = pl.read_csv("top_speeds.csv")

team_max = (
    df.group_by("team")
    .agg(pl.col("top_speed_kmh").max().alias("max_speed"))
    .sort("max_speed", descending=True)
)
TEAMS_SORTED = team_max["team"].to_list()

_cmap = LinearSegmentedColormap.from_list("seq", [BLUE, SAGE, SAND, CORAL],
                                          N=len(TEAMS_SORTED))
TEAM_COLOR = {t: _cmap(i / (len(TEAMS_SORTED) - 1))
              for i, t in enumerate(TEAMS_SORTED)}


def _fig(w, h):
    fig = plt.figure(figsize=(w, h), facecolor=BG)
    return fig


def _header(fig, title, subtitle, y_title=0.975, y_sub=0.955):
    fig.text(0.5, y_title, title, ha="center", va="top",
             color=INK, fontsize=15, fontweight="bold",
             transform=fig.transFigure)
    fig.text(0.5, y_sub, subtitle, ha="center", va="top",
             color=SUB, fontsize=9, transform=fig.transFigure)


def _clean_ax(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=SUB, labelsize=8.5)
    ax.xaxis.label.set_color(SUB)
    ax.yaxis.label.set_color(SUB)
    ax.xaxis.label.set_size(9)


def save(fig, name: str):
    path = f"exports/{name}.png"
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=BG)
    print(f"  saved → {path}")
    plt.close(fig)


# ── 1. BEESWARM ───────────────────────────────────────────────────────────────
def chart_beeswarm():
    fig = _fig(17, 15)
    ax = fig.add_axes([0.14, 0.04, 0.84, 0.88])
    _clean_ax(ax)
    ax.set_facecolor(BG)

    speeds  = df["top_speed_kmh"].to_numpy()
    teams   = df["team"].to_list()

    rng = np.random.default_rng(42)

    for i, team in enumerate(TEAMS_SORTED):
        mask = np.array([t == team for t in teams])
        xs   = speeds[mask]
        ys   = np.full(len(xs), i) + rng.uniform(-0.32, 0.32, len(xs))
        col  = TEAM_COLOR[team]

        ax.scatter(xs, ys, s=14, color=col, alpha=0.55,
                   linewidths=0.3, edgecolors=col, zorder=3)

        # faint row stripe
        ax.axhspan(i - 0.5, i + 0.5,
                   color=(INK if i % 2 == 0 else BG), alpha=0.02, zorder=0)

        # mean tick
        ax.plot([xs.mean(), xs.mean()], [i - 0.38, i + 0.38],
                color=col, linewidth=1.4, alpha=0.6, zorder=4)

        ax.text(16.3, i, team, va="center", ha="left",
                color=INK, fontsize=7.5, alpha=0.85)

    # top-3 annotations
    top3 = df.sort("top_speed_kmh", descending=True).head(3)
    for idx, row in enumerate(top3.iter_rows(named=True)):
        yi   = TEAMS_SORTED.index(row["team"])
        xpos = row["top_speed_kmh"]
        ax.scatter([xpos], [yi], s=55, color=CORAL, zorder=6,
                   linewidths=0, marker="o")
        ax.annotate(
            f"  {row['player']}  {xpos:.1f} km/h",
            xy=(xpos, yi),
            xytext=(xpos + 0.05, yi - (1.6 + idx * 1.1)),
            color=INK, fontsize=8,
            arrowprops=dict(arrowstyle="-", color=STROKE, lw=0.8),
        )

    # grid
    for x in np.arange(20, 38, 2):
        ax.axvline(x, color=RULE, linewidth=0.6, zorder=1)

    ax.set_xlim(16.0, 38.5)
    ax.set_ylim(-1, len(TEAMS_SORTED))
    ax.set_yticks([])
    ax.set_xticks(np.arange(20, 38, 2))
    ax.set_xticklabels([f"{v} km/h" for v in np.arange(20, 38, 2)],
                       color=SUB, fontsize=8.5)

    # legend note
    ax.text(37.0, len(TEAMS_SORTED) - 1.2,
            "vertical tick = team mean", ha="right",
            color=SUB, fontsize=7.5, style="italic")

    _header(fig, "Every player, every match",
            "FIFA World Cup 2026  ·  top speed by player & team  ·  1,512 records",
            y_title=0.98, y_sub=0.963)
    save(fig, "1_beeswarm")


# ── 2. DISTRIBUTION ───────────────────────────────────────────────────────────
def chart_distribution():
    fig = _fig(12, 5.5)
    ax = fig.add_axes([0.06, 0.1, 0.88, 0.72])
    _clean_ax(ax)
    ax.set_facecolor(BG)

    speeds = df["top_speed_kmh"].to_numpy()
    xs = np.linspace(speeds.min() - 0.5, speeds.max() + 0.5, 600)
    kde = gaussian_kde(speeds, bw_method=0.22)
    ys  = kde(xs)

    # soft fill
    ax.fill_between(xs, ys, color=BLUE, alpha=0.12)
    ax.plot(xs, ys, color=BLUE, linewidth=1.8)

    # rug
    rng = np.random.default_rng(0)
    jitter = rng.uniform(-0.0003, 0.0003, len(speeds))
    ax.scatter(speeds, jitter, s=4, color=INK, alpha=0.12,
               linewidths=0, zorder=2)

    # percentile lines
    pcts = {
        50: ("median", STROKE, "solid"),
        90: ("90th", SAND, "dashed"),
        95: ("95th", CORAL, "dashed"),
    }
    for p, (label, col, ls) in pcts.items():
        v = float(np.percentile(speeds, p))
        ax.axvline(v, color=col, linewidth=1.1, linestyle=ls, alpha=0.9, zorder=3)
        ax.text(v + 0.08, max(ys) * 0.92,
                f"{label}  {v:.1f}", color=col, fontsize=8, va="top")

    n_fast = int((speeds >= 35).sum())
    ax.annotate(
        f"{n_fast} players\nbroke 35 km/h",
        xy=(35, kde(np.array([35]))[0]),
        xytext=(35.4, max(ys) * 0.55),
        color=CORAL, fontsize=8.5,
        arrowprops=dict(arrowstyle="-", color=STROKE, lw=0.7),
    )

    for x in np.arange(20, 38, 2):
        ax.axvline(x, color=RULE, linewidth=0.5, zorder=0)

    ax.set_xlim(xs[0], xs[-1])
    ax.set_ylim(-0.003, max(ys) * 1.18)
    ax.set_xticks(np.arange(20, 38, 2))
    ax.set_xticklabels([f"{v}" for v in np.arange(20, 38, 2)],
                       color=SUB, fontsize=8.5)
    ax.set_yticks([])
    ax.set_xlabel("Top speed (km/h)", labelpad=6)

    _header(fig, "How fast did the tournament run?",
            f"Speed distribution across 1,512 player appearances  ·  mean {speeds.mean():.1f} km/h",
            y_title=0.97, y_sub=0.945)
    save(fig, "2_distribution")


# ── 3. TEAM RANGE CHART ───────────────────────────────────────────────────────
def chart_teams():
    fig = _fig(13, 17)
    ax = fig.add_axes([0.20, 0.04, 0.72, 0.90])
    _clean_ax(ax)
    ax.set_facecolor(BG)

    rng = np.random.default_rng(7)

    for i, team in enumerate(TEAMS_SORTED):
        sub = df.filter(pl.col("team") == team)["top_speed_kmh"].to_numpy()
        lo, hi, mn = sub.min(), sub.max(), sub.mean()
        col = TEAM_COLOR[team]

        # whisker
        ax.plot([lo, hi], [i, i], color=col, linewidth=1.8,
                alpha=0.35, solid_capstyle="round", zorder=2)
        # dots
        jitter = rng.uniform(-0.22, 0.22, len(sub))
        ax.scatter(sub, np.full(len(sub), i) + jitter, s=13,
                   color=col, alpha=0.6, linewidths=0, zorder=3)
        # mean
        ax.scatter([mn], [i], s=50, color=col, marker="|",
                   linewidths=2, zorder=5, alpha=0.9)

        ax.text(16.3, i, team, va="center", ha="left",
                color=INK, fontsize=7.8)
        ax.text(hi + 0.2, i, f"{hi:.1f}", va="center",
                color=col, fontsize=7.2, alpha=0.85)

    for x in np.arange(20, 38, 2):
        ax.axvline(x, color=RULE, linewidth=0.5, zorder=1)

    ax.set_xlim(16.0, 38.5)
    ax.set_ylim(-0.8, len(TEAMS_SORTED) - 0.2)
    ax.set_yticks([])
    ax.set_xticks(np.arange(20, 38, 2))
    ax.set_xticklabels([f"{v}" for v in np.arange(20, 38, 2)],
                       color=SUB, fontsize=8.5)
    ax.set_xlabel("Top speed (km/h)", labelpad=6)

    ax.text(37.5, len(TEAMS_SORTED) - 1.4,
            "| = team mean", ha="right", color=SUB, fontsize=7.5, style="italic")

    _header(fig, "Which teams are fastest?",
            "Sorted by max recorded speed  ·  each dot is one player appearance",
            y_title=0.974, y_sub=0.956)
    save(fig, "3_teams")


# ── 4. PLAYER LEADERBOARD (Plotly) ───────────────────────────────────────────
def chart_leaderboard(top_n: int = 25):
    import plotly.graph_objects as go

    top  = df.sort("top_speed_kmh", descending=True).head(top_n)
    rows = list(reversed(list(top.iter_rows(named=True))))

    players = [r["player"]        for r in rows]
    teams   = [r["team"]          for r in rows]
    matches = [r["match"]         for r in rows]
    speeds  = [r["top_speed_kmh"] for r in rows]

    spd_min, spd_max = min(speeds), max(speeds)

    # soft blue → coral gradient matching palette
    def _color(t):
        r0, g0, b0 = 91,  141, 184   # BLUE
        r1, g1, b1 = 212, 116,  90   # CORAL
        r = int(r0 + t * (r1 - r0))
        g = int(g0 + t * (g1 - g0))
        b = int(b0 + t * (b1 - b0))
        return f"rgb({r},{g},{b})"

    norm   = [(s - spd_min) / (spd_max - spd_min) for s in speeds]
    colors = [_color(1 - n) for n in norm]  # fastest = coral at top

    ranks_rev = list(range(top_n, 0, -1))
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    y_labels = [
        f"{medals.get(r, f'#{r}')}  {p}  ·  {t}"
        for r, p, t in zip(ranks_rev, players, teams)
    ]
    custom = [f"{t}  ·  {m}" for t, m in zip(teams, matches)]

    fig = go.Figure()

    # light background bars (full width for visual anchor)
    fig.add_trace(go.Bar(
        x=[spd_max + 2] * top_n,
        y=y_labels,
        orientation="h",
        marker=dict(color="rgba(0,0,0,0.04)", line=dict(width=0)),
        hoverinfo="skip",
        showlegend=False,
    ))

    fig.add_trace(go.Bar(
        x=speeds,
        y=y_labels,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(width=0),
            opacity=0.85,
        ),
        text=[f"  {s:.1f}" for s in speeds],
        textposition="outside",
        textfont=dict(color="#555555", size=11, family="Helvetica Neue"),
        customdata=custom,
        hovertemplate="<b>%{y}</b><br>%{customdata}<br><b>%{x:.1f} km/h</b><extra></extra>",
    ))

    h = top_n * 30 + 130
    fig.update_layout(
        barmode="overlay",
        paper_bgcolor="#f7f5f2",
        plot_bgcolor="#ffffff",
        height=h,
        width=900,
        margin=dict(l=230, r=90, t=80, b=50),
        title=dict(
            text=(
                "<span style='color:#2b2b2b;font-weight:bold;font-size:18px'>"
                "Who ran fastest?</span>  "
                "<span style='color:#888888;font-size:12px'>"
                f"Top {top_n}  ·  FIFA World Cup 2026</span>"
            ),
            x=0.5, xanchor="center",
            font=dict(family="Helvetica Neue", color="#2b2b2b"),
            pad=dict(b=10),
        ),
        xaxis=dict(
            range=[spd_min - 1.2, spd_max + 2.8],
            tickfont=dict(color="#888888", size=10, family="Helvetica Neue"),
            gridcolor="rgba(0,0,0,0.07)",
            gridwidth=1,
            zeroline=False,
            showline=False,
            ticksuffix=" km/h",
        ),
        yaxis=dict(
            tickfont=dict(color="#2b2b2b", size=10.5, family="Helvetica Neue"),
            showgrid=False,
            zeroline=False,
            showline=False,
        ),
        showlegend=False,
    )

    path = "exports/4_leaderboard.png"
    fig.write_image(path, scale=2)
    print(f"  saved → {path}")


# ── 5. SPEED DELTA BETWEEN GAMES ─────────────────────────────────────────────
def chart_delta(top_n: int = 20):
    delta = (
        df.group_by("player")
        .agg([
            pl.col("top_speed_kmh").max().alias("max"),
            pl.col("top_speed_kmh").min().alias("min"),
            pl.col("top_speed_kmh").count().alias("n_matches"),
            pl.col("team").first(),
            pl.col("match").sort().str.join("  /  ").alias("matches"),
        ])
        .filter(pl.col("n_matches") >= 2)
        .with_columns((pl.col("max") - pl.col("min")).alias("delta"))
        .sort("delta", descending=True)
        .head(top_n)
    )

    rows       = list(delta.iter_rows(named=True))
    labels     = [f"{r['player']}  ·  {r['team']}" for r in rows]
    deltas     = [r["delta"]   for r in rows]
    mins       = [r["min"]     for r in rows]
    maxs       = [r["max"]     for r in rows]
    match_strs = [r["matches"] for r in rows]

    fig = _fig(14, top_n * 0.54 + 2.2)
    ax  = fig.add_axes([0.01, 0.05, 0.88, 0.87])
    _clean_ax(ax)
    ax.set_facecolor(BG)

    for i, (lo, hi, d, label, mstr) in enumerate(
        zip(mins, maxs, deltas, labels, match_strs)
    ):
        t   = i / (top_n - 1)
        col = LinearSegmentedColormap.from_list("d", [BLUE, CORAL])(t)

        # faint stripe
        ax.axhspan(i - 0.45, i + 0.45,
                   color=INK if i % 2 == 0 else BG, alpha=0.02, zorder=0)

        # connecting line
        ax.plot([lo, hi], [i, i], color=col, linewidth=2, alpha=0.4,
                solid_capstyle="round", zorder=2)

        # dots
        ax.scatter([lo], [i], s=55, color=BLUE,  zorder=4, linewidths=0)
        ax.scatter([hi], [i], s=55, color=CORAL, zorder=4, linewidths=0)

        # speed labels
        ax.text(lo - 0.15, i, f"{lo:.1f}", ha="right", va="center",
                color=BLUE,  fontsize=7.8)
        ax.text(hi + 0.15, i, f"{hi:.1f}", ha="left",  va="center",
                color=CORAL, fontsize=7.8)

        # Δ label
        ax.text((lo + hi) / 2, i - 0.36, f"Δ {d:.1f}",
                ha="center", va="top", color=SUB,
                fontsize=7, style="italic")

        # player / match
        ax.text(16.2, i, label, va="center", ha="left",
                color=INK, fontsize=7.8)
        ax.text(38.2, i, mstr, va="center", ha="left",
                color=SUB, fontsize=6.5)

    for x in np.arange(18, 38, 2):
        ax.axvline(x, color=RULE, linewidth=0.5, zorder=1)

    ax.set_xlim(16.0, 38.5)
    ax.set_ylim(-0.7, top_n - 0.3)
    ax.set_yticks([])
    ax.set_xticks(np.arange(18, 38, 2))
    ax.set_xticklabels([f"{v}" for v in np.arange(18, 38, 2)],
                       color=SUB, fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Top speed (km/h)", labelpad=6)

    # legend
    ax.scatter([], [], s=55, color=BLUE,  label="Slower match")
    ax.scatter([], [], s=55, color=CORAL, label="Faster match")
    ax.legend(loc="lower right", frameon=False,
              labelcolor=INK, fontsize=8.5, markerscale=0.85)

    _header(fig, "Biggest speed swings between matches",
            "Players with 2+ appearances  ·  dot-to-dot = top speed range across their matches",
            y_title=0.975, y_sub=0.957)
    save(fig, "5_delta")


if __name__ == "__main__":
    print("Generating charts...")
    chart_beeswarm()
    chart_distribution()
    chart_teams()
    chart_leaderboard()
    chart_delta()
    print("Done.")
