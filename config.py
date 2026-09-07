"""
config.py
---------
Central configuration for the F1 Race Data Dashboard: page setup, theming,
default demo selections, session-type mappings and team colour palette.
"""

import streamlit as st

# --------------------------------------------------------------------------
# App metadata
# --------------------------------------------------------------------------
APP_TITLE = "F1 Race Data Dashboard"
APP_ICON = "🏎️"

# --------------------------------------------------------------------------
# Default demo selections (used on first load)
# --------------------------------------------------------------------------
DEFAULT_SEASON = 2024
DEFAULT_GP = "Monaco"
DEFAULT_SESSION = "Race"
DEFAULT_DRIVER_1 = "LEC"
DEFAULT_DRIVER_2 = "VER"

# --------------------------------------------------------------------------
# Season range shown in the selector
# --------------------------------------------------------------------------
MIN_SEASON = 2018
import datetime as _dt
MAX_SEASON = _dt.datetime.now().year

# --------------------------------------------------------------------------
# Session type display name -> FastF1 session identifier
# --------------------------------------------------------------------------
SESSION_TYPE_MAP = {
    "Practice 1": "FP1",
    "Practice 2": "FP2",
    "Practice 3": "FP3",
    "Sprint Qualifying": "SQ",
    "Sprint Shootout": "SS",
    "Sprint": "S",
    "Qualifying": "Q",
    "Race": "R",
}

# Fallback ordered list (not every event has every session)
ALL_SESSION_LABELS = [
    "Practice 1",
    "Practice 2",
    "Practice 3",
    "Sprint Qualifying",
    "Sprint Shootout",
    "Sprint",
    "Qualifying",
    "Race",
]

# --------------------------------------------------------------------------
# Tyre compound colours (F1-style)
# --------------------------------------------------------------------------
COMPOUND_COLORS = {
    "SOFT": "#DA291C",
    "MEDIUM": "#FFD700",
    "HARD": "#F0F0F0",
    "INTERMEDIATE": "#43B02A",
    "WET": "#0067AD",
    "UNKNOWN": "#8A8A8A",
    "TEST_UNKNOWN": "#8A8A8A",
}

# --------------------------------------------------------------------------
# Generic team-agnostic colour pair for driver comparisons (fallback only;
# real team colours are pulled from FastF1 where possible)
# --------------------------------------------------------------------------
DRIVER_1_FALLBACK_COLOR = "#00D2BE"
DRIVER_2_FALLBACK_COLOR = "#DC0000"

PLOTLY_TEMPLATE = "plotly_dark"
PAPER_BG = "#15151E"
PLOT_BG = "#1E1E2A"
GRID_COLOR = "#31313F"
FONT_COLOR = "#E8E8ED"
ACCENT_RED = "#E10600"
ACCENT_GOLD = "#FFB800"


def configure_page():
    """Set global Streamlit page config. Must be the first st.* call."""
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Titillium+Web:wght@400;600;700;900&family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
}

/* App background */
.stApp {
    background: radial-gradient(circle at 15% 0%, #1b1b28 0%, #0e0e14 55%, #0a0a0f 100%);
    color: #E8E8ED;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #14141d 0%, #0c0c12 100%);
    border-right: 1px solid #26262f;
}
section[data-testid="stSidebar"] .stRadio label {
    font-size: 0.95rem;
}

/* Headings */
h1, h2, h3 {
    font-family: 'Titillium Web', sans-serif !important;
    letter-spacing: 0.3px;
}
h1 {
    font-weight: 900 !important;
    background: linear-gradient(90deg, #FFFFFF 0%, #FF3B30 60%, #E10600 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Sidebar title */
.f1-brand {
    font-family: 'Titillium Web', sans-serif;
    font-weight: 900;
    font-size: 1.35rem;
    color: #fff;
    padding: 0.4rem 0 0.2rem 0;
    border-bottom: 3px solid #E10600;
    margin-bottom: 0.8rem;
}
.f1-brand span {
    color: #E10600;
}

/* Metric cards */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #1a1a24, #14141c);
    border: 1px solid #2b2b38;
    border-radius: 14px;
    padding: 14px 16px 10px 16px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.35);
}
div[data-testid="stMetric"] label {
    color: #9A9AB0 !important;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.72rem !important;
    letter-spacing: 0.6px;
}
div[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
    font-family: 'Titillium Web', sans-serif;
    font-weight: 700 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #2b2b38;
}
.stTabs [data-baseweb="tab"] {
    background-color: #16161f;
    border-radius: 8px 8px 0 0;
    padding: 8px 16px;
    color: #9A9AB0;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background-color: #24242f !important;
    color: #FFFFFF !important;
    border-bottom: 3px solid #E10600 !important;
}

/* Buttons */
.stButton>button {
    background: linear-gradient(90deg, #E10600, #B00500);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.5rem 1.1rem;
}
.stButton>button:hover {
    background: linear-gradient(90deg, #FF3B30, #E10600);
    color: white;
}

/* DataFrames */
div[data-testid="stDataFrame"] {
    border: 1px solid #2b2b38;
    border-radius: 10px;
    overflow: hidden;
}

/* Expander */
details {
    background-color: #16161f;
    border: 1px solid #2b2b38;
    border-radius: 10px;
}

/* Section divider */
.f1-section-title {
    font-family: 'Titillium Web', sans-serif;
    font-weight: 700;
    font-size: 1.25rem;
    color: #fff;
    border-left: 5px solid #E10600;
    padding-left: 10px;
    margin: 0.6rem 0 0.8rem 0;
}

.f1-caption {
    color: #9A9AB0;
    font-size: 0.85rem;
    margin-top: -0.4rem;
}

hr {
    border-color: #26262f;
}
</style>
"""


def inject_custom_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def section_title(text: str, caption: str = ""):
    st.markdown(f'<div class="f1-section-title">{text}</div>', unsafe_allow_html=True)
    if caption:
        st.markdown(f'<div class="f1-caption">{caption}</div>', unsafe_allow_html=True)
