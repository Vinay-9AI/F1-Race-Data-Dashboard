"""
utils/helpers.py
-----------------
Small, reusable formatting / safety helpers used across the dashboard.
No FastF1-specific logic lives here on purpose, so it stays trivially
testable and reusable.
"""

from __future__ import annotations

import functools
import traceback
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd
import streamlit as st


# --------------------------------------------------------------------------
# Time formatting
# --------------------------------------------------------------------------
def format_timedelta(td, precision: int = 3) -> str:
    """Format a pandas.Timedelta / datetime.timedelta as m:ss.mmm.

    Returns 'N/A' for NaT/None/NaN so it is always safe to call.
    """
    if td is None:
        return "N/A"
    try:
        if pd.isna(td):
            return "N/A"
    except (TypeError, ValueError):
        pass

    total_seconds = td.total_seconds() if hasattr(td, "total_seconds") else float(td)
    if total_seconds is None or (isinstance(total_seconds, float) and np.isnan(total_seconds)):
        return "N/A"

    negative = total_seconds < 0
    total_seconds = abs(total_seconds)
    minutes = int(total_seconds // 60)
    seconds = total_seconds - minutes * 60
    sign = "-" if negative else ""
    if minutes > 0:
        return f"{sign}{minutes}:{seconds:06.3f}"
    return f"{sign}{seconds:.{precision}f}s"


def seconds_to_laptime_str(seconds: Optional[float]) -> str:
    """Format a raw float number of seconds as m:ss.mmm."""
    if seconds is None or (isinstance(seconds, float) and np.isnan(seconds)):
        return "N/A"
    minutes = int(seconds // 60)
    rem = seconds - minutes * 60
    if minutes > 0:
        return f"{minutes}:{rem:06.3f}"
    return f"{rem:.3f}s"


def timedelta_to_seconds(series: pd.Series) -> pd.Series:
    """Vectorized conversion of a Timedelta series to float seconds (NaT -> NaN)."""
    return series.dt.total_seconds()


# --------------------------------------------------------------------------
# Safe access helpers
# --------------------------------------------------------------------------
def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """getattr that never raises and treats NaN-like values as missing."""
    try:
        val = getattr(obj, attr, default)
    except Exception:
        return default
    try:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return default
    except (TypeError, ValueError):
        pass
    return val


def is_missing(value: Any) -> bool:
    """True if value is None/NaN/NaT/empty string."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def safe_round(value: Any, digits: int = 3, default: str = "N/A"):
    if is_missing(value):
        return default
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------
# Error containment decorator for Streamlit sections
# --------------------------------------------------------------------------
def safe_section(section_name: str):
    """Decorator that prevents one broken section from crashing the whole app.

    Any exception raised inside the wrapped function is caught, shown to the
    user as a contextual warning, and the app keeps rendering the rest of the
    page.
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001 - intentional broad catch
                st.warning(
                    f"⚠️ '{section_name}' could not be rendered: {exc}"
                )
                with st.expander("Show technical details"):
                    st.code(traceback.format_exc())
                return None

        return wrapper

    return decorator


def guard(condition: bool, message: str) -> bool:
    """If condition is False, show an info box and return False so callers
    can early-return cleanly."""
    if not condition:
        st.info(message)
        return False
    return True


def df_has_rows(df: Optional[pd.DataFrame]) -> bool:
    return df is not None and isinstance(df, pd.DataFrame) and not df.empty


# --------------------------------------------------------------------------
# Misc
# --------------------------------------------------------------------------
def team_color_hex(color_value: Any, fallback: str) -> str:
    """FastF1 team colours sometimes come back without a leading '#'."""
    if is_missing(color_value):
        return fallback
    color_value = str(color_value)
    if not color_value.startswith("#"):
        color_value = f"#{color_value}"
    if len(color_value) not in (4, 7):
        return fallback
    return color_value
