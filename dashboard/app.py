"""S&P 500 AI Exposure Dashboard.

Market-implied AI exposure of every S&P 500 stock, estimated from the
project's AI Theme and AI Infrastructure factors:

    r_i,t − rf_t = α_i + β_theme·F_AITheme,t + β_infra·F_AIInfra,t + γ′·Controls + ε_i,t

Runs fully offline from pre-built feather/json files under ``data/``.
Launch:  .venv/bin/streamlit run dashboard/app.py
"""

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Project root (parent of this file's directory) so the app works regardless
# of the current working directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis.estimate_exposure import estimate_current, rolling_betas  # noqa: E402

# --------------------------------------------------------------------------
# Constants / theme
# --------------------------------------------------------------------------

C_THEME = "#22d3ee"   # electric cyan  — AI Theme
C_INFRA = "#f59e0b"   # amber          — AI Infrastructure
C_ACCENT = "#a78bfa"  # violet         — generic accent
C_GREEN = "#34d399"
C_RED = "#f87171"
C_GRAY = "#64748b"

QUADRANT_COLORS = {
    "AI Leader": C_ACCENT,
    "Theme Play": C_THEME,
    "Infra Play": C_INFRA,
    "Low Exposure": C_GRAY,
}
QUADRANT_ORDER = ["AI Leader", "Theme Play", "Infra Play", "Low Exposure"]

MODEL_LABELS = {
    "ff": "FF5+UMD (through FF publication date)",
    "market": "Market-only (through yesterday)",
}
MODEL_FILES = {
    "ff": "sp500_ai_exposure_latest.feather",
    "market": "sp500_ai_exposure_market.feather",
}

SECTOR_PALETTE = [
    "#22d3ee", "#a78bfa", "#f59e0b", "#34d399", "#f87171", "#60a5fa",
    "#f472b6", "#facc15", "#4ade80", "#c084fc", "#fb923c", "#94a3b8",
]

# One Plotly template used by every chart.
AI_TEMPLATE = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Inter, Segoe UI, sans-serif", size=13),
        colorway=SECTOR_PALETTE,
        xaxis=dict(
            gridcolor="rgba(148,163,184,0.12)",
            zerolinecolor="rgba(148,163,184,0.35)",
            linecolor="rgba(148,163,184,0.25)",
        ),
        yaxis=dict(
            gridcolor="rgba(148,163,184,0.12)",
            zerolinecolor="rgba(148,163,184,0.35)",
            linecolor="rgba(148,163,184,0.25)",
        ),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=50, b=40),
        hovermode="closest",
    )
)

# --------------------------------------------------------------------------
# Page config + CSS
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="S&P 500 AI Exposure",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .stApp { background: radial-gradient(1200px 800px at 85% -10%, #172033 0%, #0e1117 55%); }

  /* Blend the default header/toolbar into the dark background */
  [data-testid="stHeader"] {
      background: rgba(14,17,23,0.85);
      backdrop-filter: blur(6px);
  }
  [data-testid="stToolbar"] { right: 1rem; }

  /* Metric cards */
  .kpi-card {
      background: linear-gradient(180deg, rgba(30,41,59,0.65), rgba(15,23,42,0.65));
      border: 1px solid rgba(148,163,184,0.18);
      border-left: 3px solid var(--accent, #22d3ee);
      border-radius: 10px;
      padding: 14px 16px 10px 16px;
      box-shadow: 0 0 18px rgba(34,211,238,0.06);
      min-height: 92px;
  }
  .kpi-label { color: #94a3b8; font-size: 0.78rem; text-transform: uppercase;
               letter-spacing: 0.06em; margin-bottom: 4px; }
  .kpi-value { color: #f1f5f9; font-size: 1.7rem; font-weight: 700; line-height: 1.1; }
  .kpi-sub   { color: #64748b; font-size: 0.75rem; margin-top: 4px; }

  /* Section headers */
  .sec-header {
      color: #f1f5f9; font-size: 1.15rem; font-weight: 650;
      border-left: 3px solid #a78bfa; padding-left: 10px;
      margin: 18px 0 6px 0;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { gap: 6px; }
  .stTabs [data-baseweb="tab"] {
      background: rgba(30,41,59,0.5); border-radius: 8px 8px 0 0;
      color: #94a3b8; padding: 8px 18px;
  }
  .stTabs [aria-selected="true"] {
      background: rgba(167,139,250,0.15) !important; color: #e2e8f0 !important;
      border-bottom: 2px solid #a78bfa;
  }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #0b0e14; border-right: 1px solid rgba(148,163,184,0.12); }
  .sb-title { color: #f1f5f9; font-size: 1.15rem; font-weight: 700; }
  .sb-sub   { color: #22d3ee; font-size: 0.8rem; letter-spacing: 0.08em; text-transform: uppercase; }

  /* Quadrant cards */
  .quad-card {
      background: rgba(15,23,42,0.6); border: 1px solid rgba(148,163,184,0.15);
      border-top: 3px solid var(--accent); border-radius: 10px; padding: 12px 14px;
      min-height: 120px;
  }
  .quad-title { color: var(--accent); font-weight: 700; font-size: 0.95rem; }
  .quad-count { color: #f1f5f9; font-size: 1.5rem; font-weight: 700; }
  .quad-tickers { color: #94a3b8; font-size: 0.78rem; }

  div[data-testid="stMetric"] { display: none; }  /* we use custom cards */
</style>
""",
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------
# Data loading (all cached, offline)
# --------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_exposure(model: str) -> pd.DataFrame:
    return pd.read_feather(PROJECT_ROOT / "data" / "exposure" / MODEL_FILES[model])


@st.cache_data(show_spinner=False)
def load_metadata() -> dict:
    with open(PROJECT_ROOT / "data" / "exposure" / "metadata.json") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_factors() -> pd.DataFrame:
    df = pd.read_feather(PROJECT_ROOT / "data" / "factors" / "ai_factor_daily.feather")
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(show_spinner=False)
def load_ff() -> pd.DataFrame:
    df = pd.read_feather(PROJECT_ROOT / "data" / "reference" / "ff_factors_daily.feather")
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(show_spinner=False)
def load_stock_returns() -> pd.DataFrame:
    """S&P 500 returns plus SPY (needed for the market-control rolling model)."""
    sr = pd.read_feather(PROJECT_ROOT / "data" / "raw" / "sp500" / "sp500_returns.feather")
    spy_path = PROJECT_ROOT / "data" / "raw" / "sp500" / "spy_returns.feather"
    if spy_path.exists():
        spy = pd.read_feather(spy_path)
        sr = pd.concat([sr, spy], ignore_index=True)
    sr["date"] = pd.to_datetime(sr["date"])
    return sr


@st.cache_data(show_spinner=False)
def compute_rolling_betas(ticker: str, window: int, controls: str) -> pd.DataFrame:
    """Rolling beta series for one stock (delegates to the analysis module)."""
    return rolling_betas(
        load_stock_returns(), load_factors(), load_ff(),
        ticker, window=window, controls=controls,
    )


@st.cache_data(show_spinner=False)
def load_constituents() -> pd.DataFrame:
    return pd.read_feather(
        PROJECT_ROOT / "data" / "raw" / "sp500" / "sp500_constituents.feather"
    )


@st.cache_data(show_spinner=False)
def load_trading_days() -> list[dt.date]:
    """Sorted unique trading days available in the stock-returns panel."""
    sr = pd.read_feather(PROJECT_ROOT / "data" / "raw" / "sp500" / "sp500_returns.feather")
    return sorted(pd.to_datetime(sr["date"]).dt.date.unique())


@st.cache_data(show_spinner=False)
def compute_exposure_period(start: dt.date, end: dt.date, model: str) -> pd.DataFrame:
    """Recompute the full cross-section for a custom [start, end] period.

    ~500 OLS + Newey-West fits; measured ≈3.3 s — kept on the statsmodels
    HAC path (no approximation) and cached per (start, end, model).
    min_obs=None lets the estimator adapt its floor to the period length.
    """
    return estimate_current(
        load_stock_returns(),  # includes SPY for the market control
        load_factors(),
        load_ff(),
        load_constituents(),
        controls=model,
        start_date=str(start),
        end_date=str(end),
        min_obs=None,
    )


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------

def kpi_card(label: str, value: str, sub: str = "", accent: str = C_ACCENT) -> str:
    return (
        f'<div class="kpi-card" style="--accent:{accent}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-sub">{sub}</div></div>'
    )


def render_cards(cards: list[tuple[str, str, str, str]]) -> None:
    cols = st.columns(len(cards))
    for col, (label, value, sub, accent) in zip(cols, cards):
        col.markdown(kpi_card(label, value, sub, accent), unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="sec-header">{title}</div>', unsafe_allow_html=True)


def sig_star(t: float) -> str:
    """Asterisk marker for |t| >= 2 (Newey–West t-stat)."""
    return "*" if pd.notna(t) and abs(t) >= 2 else ""


def styled_fig(fig: go.Figure, height: int = 480) -> go.Figure:
    """Apply the project template with explicit figure-level overrides.

    Streamlit registers its own theme as plotly's default template and its
    frontend can override template-level backgrounds/fonts, so the critical
    values are set explicitly on the figure itself (figure-level always wins).
    """
    fig.update_layout(template=AI_TEMPLATE, height=height)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", family="Inter, Segoe UI, sans-serif", size=13),
    )
    return fig


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

meta = load_metadata()

st.sidebar.markdown('<div class="sb-title">📡 AI Exposure Terminal</div>', unsafe_allow_html=True)
st.sidebar.markdown('<div class="sb-sub">S&P 500 · Market-Implied AI Betas</div>', unsafe_allow_html=True)
st.sidebar.divider()

model_label = st.sidebar.radio("Model", list(MODEL_LABELS.values()), index=0)
model = [k for k, v in MODEL_LABELS.items() if v == model_label][0]

# --- Regression period selector ---
# Bounds: first stock-return day → FF through-date (FF model) or price
# through-date (Market-only, no FF publication lag).
trading_days = load_trading_days()
model_end = dt.date.fromisoformat(
    meta["ff_data_through"] if model == "ff" else meta["price_data_through"]
)
days_upto_end = [d for d in trading_days if d <= model_end]
default_end = days_upto_end[-1]
default_start = (
    days_upto_end[-meta["window"]]
    if len(days_upto_end) >= meta["window"]
    else days_upto_end[0]
)
start_sel, end_sel = st.sidebar.slider(
    "Regression period",
    min_value=trading_days[0],
    max_value=default_end,
    value=(default_start, default_end),
    format="YYYY-MM-DD",
    key=f"period_{model}",  # per-model widget state: bounds differ (FF lag)
    help="Start and end date of the OLS regression sample (identical for every "
         "stock). The default is the pre-built trailing 252-trading-day window "
         "and loads instantly; any other period recomputes all ~500 "
         "regressions on the fly (a few seconds, then cached).",
)
n_common_days = sum(1 for d in days_upto_end if start_sel <= d <= end_sel)

window = st.sidebar.select_slider(
    "Rolling window (deep-dive chart)", options=[126, 252, 504], value=252,
    help="Applies to the Stock Deep Dive rolling-beta chart only; "
         "independent of the regression period above.",
)

# --- Load or recompute the cross-section for the selected period ---
is_default_period = (start_sel, end_sel) == (default_start, default_end)
period_source = "precomputed 252d window"

# Refuse degenerately short periods (< ~40 common trading days)
if not is_default_period and n_common_days < 40:
    st.error(
        f"Selected period {start_sel} → {end_sel} spans only {n_common_days} "
        "common trading days — too few for a meaningful cross-sectional "
        "regression (minimum 40). Please widen the regression period."
    )
    st.stop()

if is_default_period:
    exposure_all = load_exposure(model)  # precomputed feather: instant startup
else:
    with st.spinner(
        f"Recomputing {meta['n_stocks_total']} regressions for "
        f"{start_sel} → {end_sel}…"
    ):
        exposure_all = compute_exposure_period(start_sel, end_sel, model)
    period_source = "recomputed on the fly (cached)"
n_estimated = int(exposure_all["beta_theme"].notna().sum())
period_caption = (
    f"Regression period: {start_sel} → {end_sel} "
    f"({n_common_days} trading days, {n_estimated} stocks estimated)"
)

sectors = sorted(exposure_all["gics_sector"].dropna().unique())
sel_sectors = st.sidebar.multiselect("GICS sectors", sectors, default=sectors)
min_r2 = st.sidebar.slider("Min R²", 0.0, 1.0, 0.0, 0.05)
ticker_query = st.sidebar.text_input("Ticker / name search", "").strip().upper()

st.sidebar.divider()
st.sidebar.caption(f"**{period_caption}** ({period_source})")
st.sidebar.caption(f"Prices through: **{meta['price_data_through']}**")
st.sidebar.caption(f"AI factors through: **{meta['factor_data_through']}**")
st.sidebar.caption(f"FF controls through: **{meta['ff_data_through']}**")
st.sidebar.caption(
    "ℹ️ Fama–French factors are published with a lag, so the FF5+UMD model "
    "uses the trailing 252 days of common data. The Market-only model is "
    "valid through the latest price date."
)

# Apply global filters
exposure = exposure_all[exposure_all["gics_sector"].isin(sel_sectors)].copy()
exposure = exposure[exposure["r2"].fillna(0) >= min_r2]
if ticker_query:
    mask = (
        exposure["ticker"].str.upper().str.contains(ticker_query, na=False)
        | exposure["name"].str.upper().str.contains(ticker_query, na=False)
    )
    exposure = exposure[mask]
valid = exposure.dropna(subset=["beta_theme", "beta_infra"]).copy()
unestimable = exposure[exposure["beta_theme"].isna()]

med_theme = valid["beta_theme"].median()
med_infra = valid["beta_infra"].median()

# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------

tabs = st.tabs([
    "Overview", "Leaderboards", "Stock Deep Dive", "Sector Analysis",
    "Distributions", "Factors", "Data & Methodology",
])

# ============================ 1. OVERVIEW ==================================
with tabs[0]:
    st.markdown("## S&P 500 AI Exposure — Overview")
    st.caption(
        f"Model: **{model_label}** · **{period_caption}** · "
        f"{len(valid)} of {len(exposure)} filtered stocks shown"
    )

    sig_share = (
        (valid["t_theme"].abs() >= 2) | (valid["t_infra"].abs() >= 2)
    ).mean() * 100 if len(valid) else 0.0
    n_leaders = int((valid["quadrant"] == "AI Leader").sum())

    _fmt = lambda v: f"{v:+.3f}" if pd.notna(v) else "—"  # noqa: E731
    render_cards([
        ("Stocks estimated", f"{valid['beta_theme'].notna().sum():,}",
         f"of {meta['n_stocks_total']} constituents", C_ACCENT),
        ("Median β_theme", _fmt(med_theme), "AI Theme factor loading", C_THEME),
        ("Median β_infra", _fmt(med_infra), "AI Infra factor loading", C_INFRA),
        ("Significant AI exposure", f"{sig_share:.1f}%",
         "|t| ≥ 2 on either AI beta (NW HAC)", C_GREEN),
        ("AI Leaders", f"{n_leaders}", "both betas above cross-sectional median", C_ACCENT),
    ])

    section("AI Exposure Map — β_theme × β_infra")
    if valid.empty:
        st.warning("No stocks pass the current filters.")
    else:
        fig = go.Figure()
        for i, (sector, grp) in enumerate(valid.groupby("gics_sector")):
            fig.add_trace(go.Scatter(
                x=grp["beta_theme"], y=grp["beta_infra"],
                mode="markers", name=sector,
                marker=dict(
                    size=6 + 10 * grp["r2"].clip(0, 1),
                    color=SECTOR_PALETTE[i % len(SECTOR_PALETTE)],
                    opacity=0.75, line=dict(width=0.5, color="rgba(255,255,255,0.25)"),
                ),
                customdata=np.stack([
                    grp["ticker"], grp["name"], grp["t_theme"], grp["t_infra"],
                    grp["r2"], grp["quadrant"].fillna("—"),
                ], axis=-1),
                hovertemplate=(
                    "<b>%{customdata[0]}</b> — %{customdata[1]}<br>"
                    "Sector: " + sector + " · %{customdata[5]}<br>"
                    "β_theme: %{x:.3f} (t=%{customdata[2]:.2f})<br>"
                    "β_infra: %{y:.3f} (t=%{customdata[3]:.2f})<br>"
                    "R²: %{customdata[4]:.2f}<extra></extra>"
                ),
            ))
        fig.add_vline(x=med_theme, line_dash="dash", line_color="rgba(34,211,238,0.5)")
        fig.add_hline(y=med_infra, line_dash="dash", line_color="rgba(245,158,11,0.5)")

        # Annotate a few extreme points (largest |combined exposure|)
        extremes = valid.reindex(valid["exp_combined"].abs().sort_values(ascending=False).index).head(8)
        for _, r in extremes.iterrows():
            fig.add_annotation(
                x=r["beta_theme"], y=r["beta_infra"], text=r["ticker"],
                showarrow=True, arrowhead=0, arrowsize=0.6, ax=0, ay=-22,
                font=dict(size=10, color="#e2e8f0"),
                arrowcolor="rgba(226,232,240,0.4)",
            )
        # Quadrant corner labels
        xr = [valid["beta_theme"].min(), valid["beta_theme"].max()]
        yr = [valid["beta_infra"].min(), valid["beta_infra"].max()]
        for text, x, y in [
            ("AI LEADERS", xr[1], yr[1]), ("THEME PLAYS", xr[1], yr[0]),
            ("INFRA PLAYS", xr[0], yr[1]), ("LOW EXPOSURE", xr[0], yr[0]),
        ]:
            fig.add_annotation(x=x, y=y, text=text, showarrow=False,
                               xanchor="right" if x == xr[1] else "left",
                               yanchor="top" if y == yr[1] else "bottom",
                               font=dict(size=10, color="rgba(148,163,184,0.55)"))
        fig.update_xaxes(title_text="β_theme (AI Theme factor loading)")
        fig.update_yaxes(title_text="β_infra (AI Infra factor loading)")
        st.plotly_chart(styled_fig(fig, height=560), width="stretch", theme=None)
        st.caption(
            "Bubble size ∝ regression R². Dashed lines are cross-sectional medians "
            "(quadrant boundaries). Labels mark the largest |vol-scaled combined exposures|."
        )

    section("Exposure quadrants")
    qcards = []
    for q in QUADRANT_ORDER:
        grp = valid[valid["quadrant"] == q]
        examples = grp.nlargest(3, "exp_combined")["ticker"].tolist()
        qcards.append((
            f"{q}", f"{len(grp)}",
            "e.g. " + ", ".join(examples) if examples else "—",
            QUADRANT_COLORS[q],
        ))
    cols = st.columns(4)
    for col, (title, count, examples, accent) in zip(cols, qcards):
        col.markdown(
            f'<div class="quad-card" style="--accent:{accent}">'
            f'<div class="quad-title">{title}</div>'
            f'<div class="quad-count">{count} stocks</div>'
            f'<div class="quad-tickers">{examples}</div></div>',
            unsafe_allow_html=True,
        )

    if len(unestimable):
        st.info(
            "⚠️ Not estimable in the selected period (too few observations): "
            + ", ".join(unestimable["ticker"]) + ". Excluded from charts."
        )

# ========================== 2. LEADERBOARDS ================================
with tabs[1]:
    st.markdown("## Leaderboards")
    n = st.slider("Top / bottom N", 5, 30, 15, key="lb_n")

    lb_specs = [
        ("beta_theme", "t_theme", "β_theme", C_THEME),
        ("beta_infra", "t_infra", "β_infra", C_INFRA),
        ("exp_combined", None, "Combined vol-scaled exposure E = Σβ·σ(F)", C_ACCENT),
    ]
    cols = st.columns(3)
    for col, (col_name, t_col, title, color) in zip(cols, lb_specs):
        with col:
            section(title)
            if valid.empty:
                st.warning("No data under current filters.")
                continue
            top = valid.nlargest(n, col_name)
            bot = valid.nsmallest(n, col_name)
            board = pd.concat([top, bot]).drop_duplicates("ticker")
            board = board.sort_values(col_name)
            # Significance marker: for exp_combined use either t-stat
            if t_col:
                sig = board[t_col].abs() >= 2
            else:
                sig = (board["t_theme"].abs() >= 2) | (board["t_infra"].abs() >= 2)
            labels = board["ticker"] + np.where(sig, "*", "")
            colors = np.where(board[col_name] >= 0, color, C_RED)
            fig = go.Figure(go.Bar(
                x=board[col_name], y=labels, orientation="h",
                marker_color=colors, opacity=0.85,
                customdata=np.stack([board["name"], board[col_name]], axis=-1),
                hovertemplate="<b>%{y}</b> %{customdata[0]}<br>"
                              + col_name + ": %{x:.4f}<extra></extra>",
            ))
            fig.add_vline(x=0, line_color="rgba(148,163,184,0.5)")
            fig.update_layout(showlegend=False)
            st.plotly_chart(styled_fig(fig, height=640), width="stretch", theme=None)
            st.caption("*\\*|t| ≥ 2 (significant)*" if t_col else "*\\*significant on either AI beta*")

# ========================= 3. STOCK DEEP DIVE ==============================
with tabs[2]:
    st.markdown("## Stock Deep Dive")
    tickers = sorted(exposure_all["ticker"].unique())
    ticker = st.selectbox(
        "Select a stock", tickers,
        index=tickers.index("NVDA") if "NVDA" in tickers else 0,
        format_func=lambda t: f"{t} — {exposure_all.loc[exposure_all['ticker'] == t, 'name'].iloc[0]}",
    )
    row = exposure_all[exposure_all["ticker"] == ticker].iloc[0]

    if pd.isna(row["beta_theme"]):
        st.warning(
            f"**{ticker} ({row['name']})** could not be estimated for the "
            f"selected period — only {int(row['n_obs'])} valid observations "
            "(below the minimum required for a stable regression)."
        )
    else:
        section(f"{row['name']} ({ticker}) — {row['gics_sector']}")
        render_cards([
            ("Quadrant", str(row["quadrant"]), "vs cross-sectional medians",
             QUADRANT_COLORS.get(row["quadrant"], C_ACCENT)),
            ("β_theme", f"{row['beta_theme']:+.3f}",
             f"t = {row['t_theme']:.2f} · pctl {row['pct_beta_theme']:.0f}", C_THEME),
            ("β_infra", f"{row['beta_infra']:+.3f}",
             f"t = {row['t_infra']:.2f} · pctl {row['pct_beta_infra']:.0f}", C_INFRA),
            ("Combined exposure", f"{row['exp_combined']:+.4f}",
             f"E = Σβ·σ(F) · pctl {row['pct_exp_combined']:.0f}", C_ACCENT),
            ("Alpha (ann.)", f"{row['alpha_ann']:+.1%}", f"R² = {row['r2']:.2f}", C_GREEN),
        ])

        # Rolling betas
        section(f"Rolling {window}d AI betas — {model_label.split(' (')[0]} model")
        with st.spinner("Computing rolling betas…"):
            rb = compute_rolling_betas(ticker, window, model)
        if rb.empty:
            st.info(f"Not enough history for a {window}-day rolling window on {ticker}.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=rb["date"], y=rb["beta_theme"], name="β_theme",
                line=dict(color=C_THEME, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>β_theme: %{y:.3f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=rb["date"], y=rb["beta_infra"], name="β_infra",
                line=dict(color=C_INFRA, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>β_infra: %{y:.3f}<extra></extra>",
            ))
            fig.add_hrect(y0=-0.05, y1=0.05, fillcolor="rgba(148,163,184,0.08)",
                          line_width=0)
            fig.add_hline(y=0, line_color="rgba(148,163,184,0.5)")
            fig.update_yaxes(title_text="Rolling beta")
            st.plotly_chart(styled_fig(fig, height=380), width="stretch", theme=None)
            st.caption(
                "The rolling chart uses its own window length (sidebar selector) "
                "and is independent of the regression period above."
            )

        # Normalized price vs AI Theme factor
        section("Stock vs AI Theme factor (normalized, growth of $1)")
        sr = load_stock_returns()
        px = sr[sr["ticker"] == ticker][["date", "return"]].dropna()
        fac = load_factors()[["date", "ai_theme_excess_return", "rf_rate"]].dropna()
        merged = px.merge(fac, on="date", how="inner")
        if merged.empty:
            st.info("No overlapping price/factor history.")
        else:
            stock_g = (1 + merged["return"]).cumprod()
            theme_g = (1 + merged["ai_theme_excess_return"] + merged["rf_rate"]).cumprod()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=merged["date"], y=stock_g, name=f"{ticker} (total return)",
                line=dict(color=C_ACCENT, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=merged["date"], y=theme_g, name="AI Theme factor (incl. rf)",
                line=dict(color=C_THEME, width=2),
                hovertemplate="%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>",
            ))
            fig.update_yaxes(title_text="Growth of $1")
            st.plotly_chart(styled_fig(fig, height=360), width="stretch", theme=None)
            st.caption(
                "AI Theme is a long–short AUM-weighted basket excess return; "
                "the risk-free leg is added back for a comparable growth-of-$1 basis."
            )

        # Regression stats (reflect the selected regression period)
        section(f"Regression statistics ({start_sel} → {end_sel})")
        stats = pd.DataFrame({
            "Statistic": ["β_theme", "t(β_theme)", "β_infra", "t(β_infra)",
                          "Alpha (annualized)", "R²", "Observations", "Window end",
                          "σ(F_theme) daily", "σ(F_infra) daily",
                          "E_theme = β·σ", "E_infra = β·σ", "E_combined"],
            "Value": [
                f"{row['beta_theme']:+.4f}", f"{row['t_theme']:.2f}",
                f"{row['beta_infra']:+.4f}", f"{row['t_infra']:.2f}",
                f"{row['alpha_ann']:+.2%}", f"{row['r2']:.3f}",
                f"{int(row['n_obs'])}", f"{row['window_end']:%Y-%m-%d}",
                f"{row['vol_theme']:.4f}", f"{row['vol_infra']:.4f}",
                f"{row['exp_theme']:+.4f}", f"{row['exp_infra']:+.4f}",
                f"{row['exp_combined']:+.4f}",
            ],
        })
        st.dataframe(stats, hide_index=True, width=420)

        # Sector peers
        section(f"Sector peers — {row['gics_sector']} (by combined exposure)")
        peers = (
            exposure_all[exposure_all["gics_sector"] == row["gics_sector"]]
            .dropna(subset=["exp_combined"])
            .sort_values("exp_combined", ascending=False)
            [["ticker", "name", "beta_theme", "beta_infra", "exp_combined", "quadrant"]]
        )

        def _hl(r):
            return ["background-color: rgba(167,139,250,0.25)"] * len(r) if r["ticker"] == ticker else [""] * len(r)

        st.dataframe(
            peers.style.apply(_hl, axis=1).format({
                "beta_theme": "{:+.3f}", "beta_infra": "{:+.3f}", "exp_combined": "{:+.4f}",
            }),
            hide_index=True, width="stretch", height=280,
        )

# ========================= 4. SECTOR ANALYSIS ==============================
with tabs[3]:
    st.markdown("## Sector Analysis")
    if valid.empty:
        st.warning("No stocks pass the current filters.")
    else:
        sec = valid.groupby("gics_sector").agg(
            n=("ticker", "count"),
            med_theme=("beta_theme", "median"),
            med_infra=("beta_infra", "median"),
            med_r2=("r2", "median"),
            med_exp=("exp_combined", "median"),
            n_sig=("ticker", lambda s: 0),  # placeholder, filled below
        )
        sig = valid.assign(sig=(valid["t_theme"].abs() >= 2) | (valid["t_infra"].abs() >= 2))
        sec["pct_sig"] = sig.groupby("gics_sector")["sig"].mean() * 100
        sec = sec.drop(columns=["n_sig"]).sort_values("med_theme", ascending=True)

        section("Median AI betas by GICS sector")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=sec.index, x=sec["med_theme"], name="β_theme",
                             orientation="h", marker_color=C_THEME, opacity=0.9,
                             hovertemplate="%{y}<br>median β_theme: %{x:.3f}<extra></extra>"))
        fig.add_trace(go.Bar(y=sec.index, x=sec["med_infra"], name="β_infra",
                             orientation="h", marker_color=C_INFRA, opacity=0.9,
                             hovertemplate="%{y}<br>median β_infra: %{x:.3f}<extra></extra>"))
        fig.update_layout(barmode="group")
        fig.update_xaxes(title_text="Median beta")
        fig.update_yaxes(automargin=True)  # long sector names need room
        st.plotly_chart(styled_fig(fig, height=460), width="stretch", theme=None)

        section("AI Leaders per sector")
        leaders = valid[valid["quadrant"] == "AI Leader"]
        lc = leaders.groupby("gics_sector").size().reindex(sec.index, fill_value=0)
        fig = go.Figure(go.Bar(
            x=lc.index, y=lc.values, marker_color=C_ACCENT, opacity=0.9,
            text=lc.values, textposition="outside",
            hovertemplate="%{x}<br>AI Leaders: %{y}<extra></extra>",
        ))
        fig.update_yaxes(title_text="# AI Leader stocks")
        fig.update_xaxes(automargin=True)  # long sector names need room
        st.plotly_chart(styled_fig(fig, height=380), width="stretch", theme=None)

        section("Sector summary table")
        tbl = sec.reset_index().rename(columns={
            "gics_sector": "Sector", "n": "Stocks", "med_theme": "Median β_theme",
            "med_infra": "Median β_infra", "med_exp": "Median E_combined",
            "med_r2": "Median R²", "pct_sig": "% significant",
        })
        st.dataframe(
            tbl.style.format({
                "Median β_theme": "{:+.3f}", "Median β_infra": "{:+.3f}",
                "Median E_combined": "{:+.4f}", "Median R²": "{:.2f}",
                "% significant": "{:.1f}%",
            }).background_gradient(subset=["Median β_theme"], cmap="cividis"),
            hide_index=True, width="stretch",
        )

# ========================== 5. DISTRIBUTIONS ===============================
with tabs[4]:
    st.markdown("## Cross-Sectional Distributions")
    if valid.empty:
        st.warning("No stocks pass the current filters.")
    else:
        dist_specs = [
            ("beta_theme", "β_theme", C_THEME,
             "How much a stock co-moves with the AI Theme basket after controls. "
             "Right of zero: returns amplified by AI sentiment."),
            ("beta_infra", "β_infra", C_INFRA,
             "Loading on the AI Infrastructure factor (data centers, power, "
             "semis capex chain)."),
            ("exp_combined", "Combined exposure E = β_theme·σ(F_theme) + β_infra·σ(F_infra)",
             C_ACCENT,
             "Vol-scaled exposure: expected daily return contribution per unit "
             "of factor movement, comparable across stocks."),
        ]
        cols = st.columns(3)
        for col, (col_name, title, color, caption) in zip(cols, dist_specs):
            with col:
                section(title.split(" E =")[0])
                x = valid[col_name].dropna()
                fig = go.Figure(go.Histogram(
                    x=x, nbinsx=40, marker_color=color, opacity=0.75,
                    hovertemplate="%{x:.3f}: %{y} stocks<extra></extra>",
                ))
                med, p90 = x.median(), x.quantile(0.9)
                fig.add_vline(x=med, line_dash="dash", line_color="#e2e8f0",
                              annotation_text=f"median {med:.3f}",
                              annotation_font_size=10)
                fig.add_vline(x=p90, line_dash="dot", line_color=C_ACCENT,
                              annotation_text=f"p90 {p90:.3f}",
                              annotation_font_size=10)
                fig.update_layout(showlegend=False)
                fig.update_xaxes(title_text=col_name)
                fig.update_yaxes(title_text="# stocks")
                st.plotly_chart(styled_fig(fig, height=360), width="stretch", theme=None)
                st.caption(caption)

# ============================= 6. FACTORS ==================================
with tabs[5]:
    st.markdown("## AI Factors")
    fac = load_factors().dropna(subset=["ai_theme_excess_return", "ai_infra_excess_return"])
    full = st.toggle("Full history (since 2010)", value=False)
    fac_view = fac if full else fac[fac["date"] >= fac["date"].max() - pd.DateOffset(years=3)]

    section("Cumulative performance — growth of $1")
    theme_g = (1 + fac_view["ai_theme_excess_return"] + fac_view["rf_rate"]).cumprod()
    infra_g = (1 + fac_view["ai_infra_excess_return"] + fac_view["rf_rate"]).cumprod()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fac_view["date"], y=theme_g, name="AI Theme",
                             line=dict(color=C_THEME, width=2),
                             hovertemplate="%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=fac_view["date"], y=infra_g, name="AI Infrastructure",
                             line=dict(color=C_INFRA, width=2),
                             hovertemplate="%{x|%Y-%m-%d}<br>$%{y:.2f}<extra></extra>"))
    fig.update_yaxes(title_text="Growth of $1")
    st.plotly_chart(styled_fig(fig, height=420), width="stretch", theme=None)
    st.caption("Long–short factor excess returns with the risk-free rate added back.")

    section("Rolling 63d theme–infra correlation")
    roll_corr = fac["ai_theme_excess_return"].rolling(63).corr(fac["ai_infra_excess_return"])
    fig = go.Figure(go.Scatter(
        x=fac["date"], y=roll_corr, name="63d corr",
        line=dict(color=C_ACCENT, width=1.8),
        fill="tozeroy", fillcolor="rgba(167,139,250,0.12)",
        hovertemplate="%{x|%Y-%m-%d}<br>corr: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_color="rgba(148,163,184,0.5)")
    fig.update_yaxes(title_text="Correlation")
    st.plotly_chart(styled_fig(fig, height=320), width="stretch", theme=None)

    section("Factor statistics (full history, annualized)")
    cards = []
    for name, col_r, color in [
        ("AI Theme", "ai_theme_excess_return", C_THEME),
        ("AI Infrastructure", "ai_infra_excess_return", C_INFRA),
    ]:
        r = fac[col_r]
        ann_ret, ann_vol = r.mean() * 252, r.std() * np.sqrt(252)
        sharpe = ann_ret / ann_vol if ann_vol else np.nan
        cards.append((f"{name} ann. return", f"{ann_ret:+.1%}", "excess over rf", color))
        cards.append((f"{name} ann. vol", f"{ann_vol:.1%}", "σ·√252", color))
        cards.append((f"{name} Sharpe", f"{sharpe:.2f}", "ann. ret / ann. vol", color))
    render_cards(cards)

# ======================= 7. DATA & METHODOLOGY =============================
with tabs[6]:
    st.markdown("## Data & Methodology")

    section("Full exposure table")
    st.caption(f"{period_caption} · {period_source}")
    show = exposure.sort_values("exp_combined", ascending=False, na_position="last")
    st.dataframe(
        show.style.format({
            "beta_theme": "{:+.3f}", "t_theme": "{:+.2f}",
            "beta_infra": "{:+.3f}", "t_infra": "{:+.2f}",
            "alpha_ann": "{:+.1%}", "r2": "{:.3f}",
            "vol_theme": "{:.4f}", "vol_infra": "{:.4f}",
            "exp_theme": "{:+.4f}", "exp_infra": "{:+.4f}", "exp_combined": "{:+.4f}",
            "pct_beta_theme": "{:.0f}", "pct_beta_infra": "{:.0f}",
            "pct_exp_combined": "{:.0f}",
        }, na_rep="—").background_gradient(subset=["exp_combined"], cmap="cividis"),
        hide_index=True, width="stretch", height=520,
    )
    st.download_button(
        "⬇️ Download CSV",
        show.to_csv(index=False).encode("utf-8"),
        file_name=f"sp500_ai_exposure_{model}_{start_sel}_{end_sel}.csv",
        mime="text/csv",
    )
    if len(unestimable):
        st.caption(
            "Rows with “—”: " + ", ".join(unestimable["ticker"])
            + " — insufficient valid observations in the selected period; "
            "betas not estimable."
        )

    section("Methodology")
    st.markdown(
        f"""
**Regression.** For each S&P 500 stock *i*, daily OLS over the **regression period
selected in the sidebar** — every trading day in [start, end] where all inputs are
non-NaN. Default: the trailing **{meta['window']}-trading-day** window (minimum 200
valid observations). For custom periods the observation floor adapts to the period
length (~75% of the available common days, clamped to [40, 200]) so short periods
remain estimable:

```
r_i,t − rf_t = α_i + β_theme·F_AITheme,t + β_infra·F_AIInfra,t + γ′·Controls_t + ε_i,t
```

- **Period selector** — any start/end within the available data (FF5+UMD ends
  {meta['ff_data_through']}, Market-only ends {meta['price_data_through']}). The
  default period loads precomputed estimates instantly; a custom period recomputes
  all ~{meta['n_stocks_total']} Newey–West regressions on the fly (≈3 s, then
  cached per period+model). Periods with fewer than 40 common trading days are
  refused. All cross-sectional tabs and the Deep-Dive regression stats reflect
  the selected period; the Deep-Dive rolling chart keeps its own window length.
- **F_AITheme** — AUM-weighted basket of AI-theme ETFs, excess over the risk-free rate.
- **F_AIInfra** — AI-infrastructure ETF factor (data centers, power, semis capex chain), excess over rf.
- **Controls** — Fama–French 5 factors + momentum (`mkt_rf, smb, hml, rmw, cma, umd`)
  for the FF5+UMD model; market excess return (SPY − rf) only for the Market-only model.
- **Inference** — Newey–West (HAC, 5 lags) t-statistics. |t| ≥ 2 ≈ significant at 5%.
- **Vol-scaled exposure** — E = β · σ(F), with σ(F) the daily factor standard deviation
  over the window; E_combined = E_theme + E_infra. Comparable in return units across stocks.
- **Quadrants** — vs cross-sectional medians of β_theme / β_infra:
  **AI Leader** (both above), **Theme Play** (theme only), **Infra Play** (infra only),
  **Low Exposure** (both below).

**As-of dates**

| Series | Through |
|---|---|
| Prices / stock returns | {meta['price_data_through']} |
| AI factors | {meta['factor_data_through']} |
| FF controls | {meta['ff_data_through']} |

Fama–French factors are published with a lag. The FF5+UMD regression therefore uses the
trailing 252 days of *common* data (window ends {meta['ff_data_through']}); the
Market-only control model is valid through {meta['price_data_through']}.

**Coverage** — {meta['n_stocks_estimated']} of {meta['n_stocks_total']} constituents estimated;
3 recent spin-offs (FDXF, HONA, Q) lack 200 observations and are not estimable.

**Limitations**

- *FF publication lag* — the primary model cannot use the most recent ~2 months of returns.
- *Current-AUM weights* — factor baskets reflect today's fund weights, not historical composition.
- *Market-implied ≠ fundamental* — betas measure how prices co-move with AI factors,
  not a company's actual AI revenue or strategy; they can reflect sentiment and flows.
- *Spin-offs* — FDXF, HONA and Q have insufficient history for a stable estimate.
- One-year windows are sensitive to regime shifts; rolling betas (Deep Dive tab) show stability.
"""
    )
