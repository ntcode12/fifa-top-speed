"""FIFA World Cup 2026 — Top Speed Explorer."""

import numpy as np
import polars as pl
import streamlit as st
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

st.set_page_config(
    page_title="FIFA WC 2026 · Top Speeds",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── palette ───────────────────────────────────────────────────────────────────
BG     = "#ffffff"
INK    = "#0f172a"
DIM    = "#64748b"
FAINT  = "#94a3b8"
RULE   = "#e2e8f0"
INDIGO = "#4f46e5"
ROSE   = "#e11d48"
SLATE  = "#cbd5e1"
AMBER  = "#d97706"

PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False, "responsive": True}

# ── css ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, sans-serif;
    background: #ffffff;
}
.block-container { padding-top: 2.5rem; padding-bottom: 5rem;
                   padding-left: 2.5rem; padding-right: 2.5rem; max-width: 1180px; }

.hero-eyebrow { font-size: 11px; font-weight: 700; letter-spacing: .16em;
                text-transform: uppercase; color: #4f46e5; margin-bottom: 12px; }
.hero-title   { font-size: 46px; font-weight: 900; color: #0f172a;
                letter-spacing: -1.8px; line-height: 1.04; }
.hero-sub     { font-size: 14px; color: #94a3b8; margin-top: 14px;
                font-weight: 400; line-height: 1.6; max-width: 640px; }

.kpi          { padding: 20px 0 6px 0; border-top: 2px solid #0f172a; }
.kpi.accent   { border-top: 2px solid #4f46e5; }
.kpi-label    { font-size: 10px; font-weight: 700; letter-spacing: .1em;
                text-transform: uppercase; color: #94a3b8; margin-bottom: 9px; }
.kpi-value    { font-size: 28px; font-weight: 800; color: #0f172a;
                letter-spacing: -0.6px; line-height: 1.05; }
.kpi-sub      { font-size: 11.5px; color: #94a3b8; margin-top: 8px; line-height: 1.45; }

.sec-label    { font-size: 10px; font-weight: 700; letter-spacing: .14em;
                text-transform: uppercase; color: #4f46e5; margin-bottom: 8px; }
.sec-title    { font-size: 23px; font-weight: 800; color: #0f172a;
                letter-spacing: -.5px; margin-bottom: 6px; line-height: 1.15; }
.sec-sub      { font-size: 12.5px; color: #94a3b8; margin-bottom: 18px;
                line-height: 1.6; max-width: 720px; }

.footer       { font-size: 11px; color: #cbd5e1; text-align: center;
                margin-top: 2.5rem; letter-spacing: .03em; }

hr { border: none; border-top: 1px solid #f1f5f9; margin: 3.5rem 0; }

/* ── mobile ─────────────────────────────────────────────────────────── */
@media (max-width: 640px) {
    .block-container { padding-left: 1.1rem; padding-right: 1.1rem;
                       padding-top: 1.6rem; }
    .hero-title { font-size: 32px; letter-spacing: -1px; }
    .hero-sub   { font-size: 13px; }
    .sec-title  { font-size: 19px; }
    .sec-sub    { font-size: 12px; }
    .kpi        { padding-top: 14px; }
    .kpi-value  { font-size: 23px; }
    hr { margin: 2.2rem 0; }
    /* let stacked KPI columns breathe instead of squashing side-by-side */
    [data-testid="stHorizontalBlock"] { gap: 0.4rem; }
}

[data-testid="stSidebar"] {
    background: #f8fafc;
    border-right: 1px solid #e2e8f0;
}
[data-testid="stSidebar"],
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span:not(.stCaption),
[data-testid="stSidebar"] div { color: #0f172a !important; }
[data-testid="stSidebar"] .stCaption { color: #64748b !important; }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def lerp(c1: str, c2: str, t: float) -> str:
    """Linear interpolate between two hex colors, return rgb() string."""
    a, b = c1.lstrip("#"), c2.lstrip("#")
    ch = lambda s, i: int(s[i:i + 2], 16)
    r = round(ch(a, 0) + t * (ch(b, 0) - ch(a, 0)))
    g = round(ch(a, 2) + t * (ch(b, 2) - ch(a, 2)))
    bl = round(ch(a, 4) + t * (ch(b, 4) - ch(a, 4)))
    return f"rgb({r},{g},{bl})"


def rgba(c1: str, c2: str, t: float, alpha: float) -> str:
    s = lerp(c1, c2, t)[4:-1]  # strip 'rgb(' and ')'
    return f"rgba({s},{alpha})"


# ── data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load():
    return pl.read_csv("top_speeds.csv")

df_all = load()
ALL_TEAMS   = sorted(df_all["team"].unique().to_list())
ALL_MATCHES = sorted(df_all["match"].unique().to_list())

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("**Filters**")
    st.caption("Drive every chart at once")
    st.divider()
    sel_teams   = st.multiselect("Teams",   ALL_TEAMS,   placeholder="All 48 teams")
    sel_matches = st.multiselect("Matches", ALL_MATCHES, placeholder="All 48 matches")
    st.divider()
    top_n   = st.slider("Leaderboard — top N", 10, 40, 25, 5)
    delta_n = st.slider("Speed delta — top N", 10, 30, 20, 5)
    ridge_n = st.slider("Ridge plot — teams shown", 10, 48, 30, 2)
    st.divider()
    st.caption("FIFA World Cup 2026  \nData · fifatrainingcentre.com")

# ── filtered df ───────────────────────────────────────────────────────────────
df = df_all
if sel_teams:   df = df.filter(pl.col("team").is_in(sel_teams))
if sel_matches: df = df.filter(pl.col("match").is_in(sel_matches))

if len(df) == 0:
    st.warning("No data matches the current filters.")
    st.stop()

TEAMS_BY_MEAN = (
    df.group_by("team")
    .agg(pl.col("top_speed_kmh").mean().alias("m"))
    .sort("m", descending=True)["team"]
    .to_list()
)

cache_key = f"{sel_teams}{sel_matches}"


# ── plotly base ───────────────────────────────────────────────────────────────
def base_layout(**kw):
    base = dict(
        paper_bgcolor=BG, plot_bgcolor=BG,
        font=dict(family="Inter, -apple-system, sans-serif", color=INK, size=11.5),
        xaxis=dict(showgrid=True, gridcolor=RULE, gridwidth=1,
                   zeroline=False, showline=False, fixedrange=True,
                   tickfont=dict(color=DIM, size=10.5)),
        yaxis=dict(showgrid=False, zeroline=False, showline=False, fixedrange=True,
                   tickfont=dict(color=INK, size=10.5)),
        margin=dict(l=10, r=10, t=10, b=40),
        showlegend=False,
        hoverlabel=dict(bgcolor=BG, bordercolor=RULE,
                        font=dict(family="Inter", size=12, color=INK)),
    )
    base.update(kw)
    return base


def fig(**kw):
    return go.Figure(layout=go.Layout(**base_layout(**kw)))


def show(f):
    if f is None:
        return
    f.update_xaxes(fixedrange=True)
    f.update_yaxes(fixedrange=True)
    st.plotly_chart(f, use_container_width=True, config=PLOTLY_CONFIG)


def section(eyebrow, title, sub):
    st.markdown(f'<div class="sec-label">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-sub">{sub}</div>', unsafe_allow_html=True)


def rule():
    st.markdown("<hr>", unsafe_allow_html=True)


# ── hero ──────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-eyebrow">FIFA World Cup 2026</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Top Speed Report</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Every sprint from the group stage, measured. '
    '48 matches · 48 teams · 1,512 player appearances tracked by FIFA\'s '
    'physical performance system.</div>',
    unsafe_allow_html=True,
)
st.markdown("<br>", unsafe_allow_html=True)

fastest   = df.sort("top_speed_kmh", descending=True).row(0, named=True)
mean_spd  = df["top_speed_kmh"].mean()
n_35      = int((df["top_speed_kmh"] >= 35).sum())
best_team = (
    df.group_by("team")
    .agg(pl.col("top_speed_kmh").mean().alias("m"))
    .sort("m", descending=True)
    .row(0, named=True)
)

c1, c2, c3, c4 = st.columns(4, gap="large")
kpis = [
    (c1, "Fastest recorded", f"{fastest['top_speed_kmh']:.1f} km/h",
     f"{fastest['player']} · {fastest['team']}", True),
    (c2, "Fastest team avg", best_team["team"],
     f"{best_team['m']:.1f} km/h mean", False),
    (c3, "Tournament mean", f"{mean_spd:.1f} km/h",
     f"across {len(df):,} appearances", False),
    (c4, "Players ≥ 35 km/h", str(n_35),
     f"{n_35 / len(df) * 100:.1f}% of all appearances", False),
]
for col, label, val, sub, accent in kpis:
    col.markdown(
        f'<div class="kpi{" accent" if accent else ""}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{val}</div>'
        f'<div class="kpi-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )

rule()


# ── 1. CLEVELAND DOT PLOT (leaderboard) ───────────────────────────────────────
section("Leaderboard", f"Top {top_n} fastest player appearances",
        "One dot per player-match · top three highlighted · hover for full context")

@st.cache_data
def cleveland(key, n):
    top  = df.sort("top_speed_kmh", descending=True).head(n)
    rows = list(top.iter_rows(named=True))

    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    speeds = [r["top_speed_kmh"] for r in rows]
    xmin   = min(speeds) - 2.0
    xmax   = max(speeds) + 1.0

    # labels live INSIDE the plot (above each bar) so the chart uses full width
    f = fig(
        height=n * 40 + 70,
        margin=dict(l=14, r=18, t=10, b=44),
        xaxis=dict(title="Top speed (km/h)", ticksuffix=" km/h",
                   range=[xmin, xmax],
                   showgrid=True, gridcolor=RULE, gridwidth=1,
                   zeroline=False, showline=False, fixedrange=True,
                   tickfont=dict(color=DIM, size=10.5)),
        yaxis=dict(visible=False, range=[n - 0.4, -1.0], fixedrange=True),
    )

    for i, row in enumerate(rows):
        col = ROSE if i < 3 else INDIGO
        # track from baseline to value
        f.add_shape(type="line", x0=xmin, x1=row["top_speed_kmh"], y0=i, y1=i,
                    line=dict(color=RULE, width=1.5))
        # value dot
        f.add_trace(go.Scatter(
            x=[row["top_speed_kmh"]], y=[i], mode="markers",
            marker=dict(size=11, color=col, line=dict(width=1.5, color=BG)),
            hovertemplate=(f"<b>{row['player']}</b><br>"
                           f"{row['team']} · {row['match']}<br>"
                           f"<b>{row['top_speed_kmh']:.1f} km/h</b><extra></extra>"),
        ))
        # name + team ABOVE the bar, left-aligned (full width available)
        f.add_annotation(
            x=xmin, y=i - 0.42, xanchor="left", yanchor="bottom",
            text=(f"{medals.get(i, f'{i + 1}.')}  "
                  f"<b>{row['player']}</b>  "
                  f"<span style='color:#94a3b8'>{row['team']}</span>"),
            showarrow=False,
            font=dict(size=11, color=INK if i < 3 else INK))
        # speed value at the dot
        f.add_annotation(x=row["top_speed_kmh"] + 0.12, y=i, xanchor="left",
                         text=f"<b>{row['top_speed_kmh']:.1f}</b>", showarrow=False,
                         font=dict(size=10, color=col))
    return f

show(cleveland(cache_key, top_n))
rule()


# ── 2. RIDGELINE ──────────────────────────────────────────────────────────────
section("Distribution", "How speed distributes within each team",
        "Fastest teams at the top, fading to slowest · curve shape = how each squad's "
        "top speeds spread · rose tick marks the team mean · "
        "dashed line is the tournament median")

@st.cache_data
def ridgeline(key, teams_shown):
    teams = TEAMS_BY_MEAN[:teams_shown]      # fastest first
    n     = len(teams)
    step  = 1.0
    amp   = step * 1.45                       # overlap factor

    speeds_all = df["top_speed_kmh"].to_numpy()
    x_range    = np.linspace(speeds_all.min() - 1.5, speeds_all.max() + 1.5, 320)
    t_median   = float(df["top_speed_kmh"].median())

    # fastest at top → highest y value
    tickvals = [(n - 1 - r) * step for r in range(n)]

    f = fig(
        height=max(n * 26 + 120, 320),
        margin=dict(l=8, r=18, t=20, b=50),
        xaxis=dict(title="Top speed (km/h)", ticksuffix=" km/h",
                   showgrid=True, gridcolor=RULE, gridwidth=1,
                   zeroline=False, showline=False, fixedrange=True,
                   tickfont=dict(color=DIM, size=10.5)),
        yaxis=dict(showgrid=False, zeroline=False, showline=False, fixedrange=True,
                   automargin=True,
                   tickmode="array", tickvals=tickvals, ticktext=teams,
                   range=[-0.5, (n - 1) * step + amp + 0.3],
                   tickfont=dict(color=INK, size=10)),
    )

    # tournament median guide
    f.add_vline(x=t_median, line_color=FAINT, line_width=1, line_dash="dash")
    f.add_annotation(x=t_median, y=(n - 1) * step + amp,
                     text=f"median {t_median:.1f}", showarrow=False,
                     font=dict(size=9.5, color=FAINT), yanchor="bottom", xshift=2)

    # draw back-to-front: slowest (bottom) first, fastest (top) last
    for rank in reversed(range(n)):
        team = teams[rank]
        sub  = df.filter(pl.col("team") == team)["top_speed_kmh"].to_numpy()
        if len(sub) < 2:
            continue
        t    = rank / max(n - 1, 1)            # 0 fastest → 1 slowest
        col  = lerp(INDIGO, SLATE, t)
        fill = rgba(INDIGO, SLATE, t, 0.16)
        base = (n - 1 - rank) * step

        kde = gaussian_kde(sub, bw_method=0.35)
        dens = kde(x_range)
        ys   = dens / dens.max() * amp

        # filled area
        f.add_trace(go.Scatter(
            x=np.concatenate([x_range, x_range[::-1]]),
            y=np.concatenate([base + ys, np.full(len(ys), base)]),
            fill="toself", fillcolor=fill,
            line=dict(width=0), hoverinfo="skip",
        ))
        # outline
        f.add_trace(go.Scatter(
            x=x_range, y=base + ys, mode="lines",
            line=dict(color=col, width=1.4), hoverinfo="skip",
        ))
        # mean tick
        mean_v = float(sub.mean())
        mean_h = kde(np.array([mean_v]))[0] / dens.max() * amp
        f.add_shape(type="line", x0=mean_v, x1=mean_v,
                    y0=base, y1=base + mean_h,
                    line=dict(color=ROSE, width=1.4))
        f.add_trace(go.Scatter(
            x=[mean_v], y=[base + mean_h], mode="markers",
            marker=dict(size=5, color=ROSE, line=dict(width=0)),
            hovertemplate=(f"<b>{team}</b><br>Mean {mean_v:.1f} km/h<br>"
                           f"Range {sub.min():.1f}–{sub.max():.1f}<br>"
                           f"n={len(sub)}<extra></extra>"),
        ))

    return f

show(ridgeline(cache_key, min(ridge_n, len(TEAMS_BY_MEAN))))
rule()


# ── 3. SLOPE CHART ────────────────────────────────────────────────────────────
section("Speed delta", "Who performed most differently between matches?",
        "Players with 2+ appearances, sorted by swing size · hollow dot = slower match · "
        "filled dot = faster match · click any row to hide it")

if "slope_hidden" not in st.session_state:
    st.session_state.slope_hidden = set()
if "slope_key" not in st.session_state:
    st.session_state.slope_key = 0


@st.cache_data
def slope_rows(key, n):
    delta = (
        df.group_by("player")
        .agg([
            pl.col("top_speed_kmh").max().alias("fast"),
            pl.col("top_speed_kmh").min().alias("slow"),
            pl.col("top_speed_kmh").count().alias("n"),
            pl.col("team").first(),
            pl.col("match").sort().str.join(" / ").alias("matches"),
        ])
        .filter(pl.col("n") >= 2)
        .with_columns((pl.col("fast") - pl.col("slow")).alias("delta"))
        .sort("delta", descending=True)
        .head(n)
    )
    return list(delta.iter_rows(named=True))


def slope_fig(rows, hidden):
    """Horizontal dumbbell — one row per player, no label collisions."""
    n = len(rows)
    all_slow = [r["slow"] for r in rows]
    all_fast = [r["fast"] for r in rows]
    xmin = min(all_slow) - 1.5
    xmax = max(all_fast) + 1.5

    f = fig(
        height=n * 40 + 70,
        margin=dict(l=14, r=18, t=10, b=44),
        xaxis=dict(title="Top speed (km/h)", ticksuffix=" km/h",
                   range=[xmin, xmax],
                   showgrid=True, gridcolor=RULE, gridwidth=1,
                   zeroline=False, showline=False, fixedrange=True,
                   tickfont=dict(color=DIM, size=10.5)),
        yaxis=dict(visible=False, range=[n - 0.4, -1.0], fixedrange=True),
        clickmode="event+select",
    )

    for i, row in enumerate(rows):
        active = row["player"] not in hidden
        # connector
        f.add_shape(type="line", x0=row["slow"], x1=row["fast"], y0=i, y1=i,
                    line=dict(color=RULE if active else "#f1f5f9",
                              width=2.5 if active else 1.5))

        if active:
            # wide invisible hit-line so a click anywhere on the row hides it
            xs = np.linspace(row["slow"], row["fast"], 14)
            cdata = [[row["player"], row["team"], row["slow"],
                      row["fast"], row["delta"]]] * 14
            f.add_trace(go.Scatter(
                x=xs, y=[i] * 14, mode="markers",
                marker=dict(size=16, color=INDIGO, opacity=0.001),
                customdata=cdata,
                hovertemplate=("<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                               "Slower %{customdata[2]:.1f} · Faster %{customdata[3]:.1f}"
                               "  (Δ %{customdata[4]:.1f})<extra></extra>"),
            ))
            # slow dot (hollow) + fast dot (filled)
            f.add_trace(go.Scatter(
                x=[row["slow"], row["fast"]], y=[i, i], mode="markers",
                marker=dict(size=10, color=[BG, INDIGO],
                            line=dict(color=INDIGO, width=1.8)),
                hoverinfo="skip",
            ))
            # numeric endpoints
            f.add_annotation(x=row["slow"], y=i, xanchor="right", xshift=-6,
                             text=f"{row['slow']:.1f}", showarrow=False,
                             font=dict(size=8.5, color=DIM))
            f.add_annotation(x=row["fast"], y=i, xanchor="left", xshift=6,
                             text=f"<b>{row['fast']:.1f}</b>", showarrow=False,
                             font=dict(size=8.5, color=INDIGO))

        # name above the row, left-aligned inside the plot (full width)
        name_col = INK if active else FAINT
        f.add_annotation(
            x=xmin, y=i - 0.42, xanchor="left", yanchor="bottom",
            text=(f"<b>{row['player']}</b>  "
                  f"<span style='color:#94a3b8'>{row['team']} · Δ{row['delta']:.1f}</span>"),
            showarrow=False, font=dict(size=11, color=name_col))
    return f


_rows = slope_rows(cache_key, delta_n)
if not _rows:
    st.info("Not enough players with multiple appearances in this filter.")
else:
    hidden = st.session_state.slope_hidden
    if hidden:
        cols = st.columns([6, 1])
        cols[1].button("↺ Show all", use_container_width=True,
                       on_click=lambda: (st.session_state.slope_hidden.clear(),
                                         st.session_state.__setitem__(
                                             "slope_key",
                                             st.session_state.slope_key + 1)))

    f = slope_fig(_rows, hidden)
    f.update_xaxes(fixedrange=True)
    f.update_yaxes(fixedrange=True)
    event = st.plotly_chart(
        f, use_container_width=True, config=PLOTLY_CONFIG,
        on_select="rerun", selection_mode="points",
        key=f"slope_{st.session_state.slope_key}",
    )
    if event and getattr(event, "selection", None):
        pts = event.selection.get("points", [])
        clicked = {p["customdata"][0] for p in pts
                   if p.get("customdata")}
        new = clicked - st.session_state.slope_hidden
        if new:
            st.session_state.slope_hidden |= new
            st.rerun()

st.markdown(
    '<div class="footer">FIFA World Cup 2026 · Top Speed Report · '
    'Data scraped from fifatrainingcentre.com</div>',
    unsafe_allow_html=True,
)
