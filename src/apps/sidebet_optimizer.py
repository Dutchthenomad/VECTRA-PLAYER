"""
TGOES Sidebet Optimizer - Streamlit Dashboard
Bayesian survival analysis for optimal sidebet placement.

Run: streamlit run src/apps/sidebet_optimizer.py --theme.base=dark
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="Sidebet Optimizer", page_icon="🎰", layout="wide", initial_sidebar_state="expanded"
)

# Catppuccin Mocha theme
THEME = {
    "bg": "#1e1e2e",
    "surface": "#313244",
    "overlay": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "blue": "#89b4fa",
    "mauve": "#cba6f7",
    "yellow": "#f9e2af",
    "peach": "#fab387",
    "teal": "#94e2d5",
}

# Custom CSS
st.markdown(
    f"""
<style>
    .stApp {{
        background-color: {THEME["bg"]};
    }}
    .metric-card {{
        background: {THEME["surface"]};
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid {THEME["mauve"]};
    }}
    .positive {{ color: {THEME["green"]}; }}
    .negative {{ color: {THEME["red"]}; }}
    .highlight {{ color: {THEME["yellow"]}; }}
    h1, h2, h3 {{ color: {THEME["mauve"]} !important; }}
    .stMetric label {{ color: {THEME["subtext"]} !important; }}
    .stMetric [data-testid="stMetricValue"] {{ color: {THEME["text"]} !important; }}
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# DATA & MODEL
# =============================================================================
@st.cache_data
def load_games():
    """Load game data from games.json."""
    path = (
        Path(__file__).parent.parent.parent
        / "src/rugs_recordings/PRNG CRAK/explorer_v2/data/games.json"
    )
    if not path.exists():
        path = Path(
            "/home/devops/Desktop/VECTRA-PLAYER/src/rugs_recordings/PRNG CRAK/explorer_v2/data/games.json"
        )

    with open(path) as f:
        games = json.load(f)

    df = pd.DataFrame(games).rename(
        columns={"tick_duration": "rug_tick", "peak_multiplier": "peak"}
    )
    return df[df["rug_tick"] >= 10]


@st.cache_data
def build_survival_model(rug_ticks):
    """Build survival model from rug tick data."""
    max_tick = int(max(rug_ticks)) + 1

    # Compute hazard rate
    rug_counts = np.zeros(max_tick)
    at_risk = np.zeros(max_tick)

    for rt in rug_ticks:
        rt = int(rt)
        at_risk[: rt + 1] += 1
        if rt < max_tick:
            rug_counts[rt] += 1

    hazard = np.divide(rug_counts, at_risk, out=np.zeros(max_tick), where=at_risk > 0)
    hazard_smooth = np.convolve(hazard, np.ones(10) / 10, mode="same")
    survival = np.exp(-np.cumsum(hazard_smooth))

    return hazard_smooth, survival, at_risk


def p_win(tick, window, survival):
    """P(rug in next window ticks | at tick) = sidebet win probability."""
    if tick >= len(survival) - 1:
        return 1.0
    s_now = survival[tick]
    s_future = survival[min(tick + window, len(survival) - 1)]
    return 1 - (s_future / s_now) if s_now > 0 else 0.5


def expected_value(p, payout, bet=0.001):
    """EV = bet * [p * (payout + 1) - 1]"""
    return bet * (p * (payout + 1) - 1)


def breakeven(payout):
    """Breakeven probability = 1 / (payout + 1)"""
    return 1 / (payout + 1)


def kelly(p, payout):
    """Kelly criterion: f* = (p*b - q) / b"""
    b = payout - 1
    return max(0, (p * b - (1 - p)) / b)


# =============================================================================
# CHARTS
# =============================================================================
def make_chart_layout():
    """Common Plotly layout settings."""
    return dict(
        paper_bgcolor=THEME["bg"],
        plot_bgcolor=THEME["surface"],
        font=dict(color=THEME["text"], family="monospace"),
        margin=dict(l=50, r=20, t=40, b=40),
        xaxis=dict(gridcolor=THEME["overlay"], zerolinecolor=THEME["overlay"]),
        yaxis=dict(gridcolor=THEME["overlay"], zerolinecolor=THEME["overlay"]),
    )


def chart_survival(hazard, survival):
    """Hazard and survival function charts."""
    ticks = np.arange(len(hazard))

    fig = make_subplots(
        rows=1, cols=2, subplot_titles=["Hazard Rate h(t)", "Survival Function S(t)"]
    )

    fig.add_trace(
        go.Scatter(
            x=ticks,
            y=hazard,
            mode="lines",
            name="Hazard",
            line=dict(color=THEME["red"], width=2),
            fill="tozeroy",
            fillcolor="rgba(243, 139, 168, 0.2)",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=ticks,
            y=survival * 100,
            mode="lines",
            name="Survival",
            line=dict(color=THEME["blue"], width=2),
            fill="tozeroy",
            fillcolor="rgba(137, 180, 250, 0.2)",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(**make_chart_layout(), height=300, showlegend=False)
    fig.update_xaxes(title_text="Tick", range=[0, 600])
    fig.update_yaxes(title_text="P(rug at t | survived)", row=1, col=1)
    fig.update_yaxes(title_text="Survival %", row=1, col=2)

    return fig


def chart_ev_by_tick(survival, window, payout):
    """Win probability and EV by entry tick."""
    ticks = np.arange(10, min(600, len(survival) - window), 2)
    p_wins = [p_win(t, window, survival) for t in ticks]
    evs = [expected_value(p, payout) * 1000 for p in p_wins]  # % per SOL
    be = breakeven(payout)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[
            f"Win Probability ({window}-tick window)",
            f"Expected Value ({payout}x payout)",
        ],
    )

    # Win probability
    fig.add_trace(
        go.Scatter(
            x=ticks,
            y=np.array(p_wins) * 100,
            mode="lines",
            line=dict(color=THEME["mauve"], width=2),
            name="P(win)",
            hovertemplate="Tick %{x}<br>P(win): %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )

    fig.add_hline(y=be * 100, line=dict(color=THEME["yellow"], dash="dash"), row=1, col=1)

    # EV with color fill
    pos_mask = np.array(evs) > 0

    fig.add_trace(
        go.Scatter(
            x=ticks[pos_mask],
            y=np.array(evs)[pos_mask],
            mode="lines",
            line=dict(color=THEME["green"], width=2),
            fill="tozeroy",
            fillcolor="rgba(166, 227, 161, 0.3)",
            name="+EV",
            hovertemplate="Tick %{x}<br>EV: %{y:.2f}%/SOL<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=ticks[~pos_mask],
            y=np.array(evs)[~pos_mask],
            mode="lines",
            line=dict(color=THEME["red"], width=2),
            fill="tozeroy",
            fillcolor="rgba(243, 139, 168, 0.3)",
            name="-EV",
            hovertemplate="Tick %{x}<br>EV: %{y:.2f}%/SOL<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.add_hline(y=0, line=dict(color=THEME["text"], width=1), row=2, col=1)

    # Mark optimal
    best_idx = np.argmax(evs)
    fig.add_vline(x=ticks[best_idx], line=dict(color=THEME["green"], dash="dash"), row=1, col=1)
    fig.add_vline(x=ticks[best_idx], line=dict(color=THEME["green"], dash="dash"), row=2, col=1)

    fig.update_layout(**make_chart_layout(), height=450, showlegend=False)
    fig.update_xaxes(title_text="Entry Tick", row=2, col=1)
    fig.update_yaxes(title_text="Win %", row=1, col=1)
    fig.update_yaxes(title_text="EV (%/SOL)", row=2, col=1)

    return fig, ticks, p_wins, evs


def chart_heatmap(survival, payout, current_window):
    """EV heatmap: tick × window."""
    tick_vals = np.arange(20, 500, 8)
    window_vals = np.arange(20, 80, 4)

    ev_matrix = np.zeros((len(window_vals), len(tick_vals)))
    for i, w in enumerate(window_vals):
        for j, t in enumerate(tick_vals):
            p = p_win(int(t), int(w), survival)
            ev_matrix[i, j] = expected_value(p, payout) * 1000

    fig = go.Figure(
        data=go.Heatmap(
            z=ev_matrix,
            x=tick_vals,
            y=window_vals,
            colorscale=[[0, THEME["red"]], [0.5, THEME["overlay"]], [1, THEME["green"]]],
            zmid=0,
            colorbar=dict(title="EV %"),
            hovertemplate="Tick: %{x}<br>Window: %{y}<br>EV: %{z:.2f}%<extra></extra>",
        )
    )

    fig.add_hline(y=current_window, line=dict(color=THEME["mauve"], width=2, dash="dash"))

    fig.update_layout(
        **make_chart_layout(),
        height=350,
        title=dict(text="Entry Zone Heatmap", font=dict(color=THEME["mauve"])),
        xaxis_title="Entry Tick",
        yaxis_title="Window (ticks)",
    )

    return fig


def chart_distribution(df):
    """Game duration and peak distribution."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=["Game Duration", "Peak Multiplier"])

    fig.add_trace(
        go.Histogram(
            x=df["rug_tick"], nbinsx=50, marker_color=THEME["mauve"], opacity=0.7, name="Duration"
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Histogram(
            x=df["peak"].clip(upper=20),
            nbinsx=50,
            marker_color=THEME["teal"],
            opacity=0.7,
            name="Peak",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(**make_chart_layout(), height=250, showlegend=False)
    fig.update_xaxes(title_text="Ticks", row=1, col=1)
    fig.update_xaxes(title_text="Multiplier", row=1, col=2)

    return fig


# =============================================================================
# MAIN APP
# =============================================================================
def main():
    # Load data
    df = load_games()
    hazard, survival, at_risk = build_survival_model(df["rug_tick"].values)

    # Sidebar controls
    st.sidebar.title("⚙️ Parameters")

    window = st.sidebar.slider("Sidebet Window", 10, 100, 40, 5, help="Ticks for sidebet to win")
    payout = st.sidebar.radio("Payout Multiplier", [5, 10, 20], horizontal=True)

    st.sidebar.divider()

    bankroll = st.sidebar.number_input("Bankroll (SOL)", 0.01, 10.0, 0.1, 0.01)
    kelly_frac = st.sidebar.slider(
        "Kelly Fraction", 0.1, 1.0, 0.25, 0.05, help="Use fractional Kelly to reduce variance"
    )

    st.sidebar.divider()
    st.sidebar.caption(f"📊 {len(df):,} games analyzed")

    # Header
    st.title("🎰 Sidebet Optimizer")
    st.caption("TGOES - Bayesian Survival Analysis for Optimal Entry Timing")

    # Key metrics
    be = breakeven(payout)
    ticks = np.arange(50, min(550, len(survival) - window), 2)
    p_wins = [p_win(t, window, survival) for t in ticks]
    evs = [expected_value(p, payout) for p in p_wins]

    best_idx = np.argmax(evs)
    best_tick = ticks[best_idx]
    best_p = p_wins[best_idx]
    best_ev = evs[best_idx]
    kelly_bet = kelly(best_p, payout) * kelly_frac
    bet_size = bankroll * kelly_bet

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Optimal Entry", f"Tick {best_tick}")
    with col2:
        st.metric("Win Probability", f"{best_p:.1%}")
    with col3:
        delta_color = "normal" if best_ev > 0 else "inverse"
        st.metric(
            "Expected Value",
            f"{best_ev * 1000:+.2f}%/SOL",
            delta="+EV" if best_ev > 0 else "-EV",
            delta_color=delta_color,
        )
    with col4:
        st.metric(
            "Recommended Bet", f"{bet_size:.4f} SOL", delta=f"{kelly_bet * 100:.1f}% of bankroll"
        )

    st.divider()

    # Charts
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "📈 Win Probability & EV",
            "🔥 Entry Heatmap",
            "📊 Survival Analysis",
            "📉 Data Distribution",
        ]
    )

    with tab1:
        fig, _, _, _ = chart_ev_by_tick(survival, window, payout)
        st.plotly_chart(fig, use_container_width=True)

        # Strategy rules
        pos_ev_ticks = ticks[np.array(evs) > 0]

        c1, c2 = st.columns(2)
        with c1:
            st.success(f"""
            **✅ PLACE sidebet when:**
            - Game age > {pos_ev_ticks.min() if len(pos_ev_ticks) > 0 else "N/A"} ticks
            - P(win) > {be:.1%}
            - Bet size: {bet_size:.4f} SOL ({kelly_frac * 100:.0f}% Kelly)
            """)
        with c2:
            st.error(f"""
            **❌ AVOID sidebet when:**
            - Game age < 100 ticks (instarug risk)
            - Rapid price pump (momentum)
            - P(win) < {be:.1%}
            """)

    with tab2:
        fig = chart_heatmap(survival, payout, window)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Green = +EV zones, Red = -EV zones. Dashed line = your selected window.")

    with tab3:
        fig = chart_survival(hazard, survival)
        st.plotly_chart(fig, use_container_width=True)

        # Survival percentiles
        st.subheader("Survival Probabilities")
        surv_data = []
        for t in [50, 100, 200, 300, 400, 500]:
            if t < len(survival):
                surv_data.append(
                    {
                        "Tick": t,
                        "P(survives)": f"{survival[t]:.1%}",
                        "Games at risk": int(at_risk[t]),
                    }
                )
        st.dataframe(pd.DataFrame(surv_data), hide_index=True, use_container_width=True)

    with tab4:
        fig = chart_distribution(df)
        st.plotly_chart(fig, use_container_width=True)

        # Stats
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Median Duration", f"{df['rug_tick'].median():.0f} ticks")
        with c2:
            st.metric("Median Peak", f"{df['peak'].median():.2f}x")
        with c3:
            st.metric("Games Analyzed", f"{len(df):,}")


if __name__ == "__main__":
    main()
