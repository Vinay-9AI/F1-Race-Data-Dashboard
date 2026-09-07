"""
data.py
-------
All FastF1 interaction lives here: cache setup, schedule/session loading,
driver/lap/telemetry/weather retrieval. Every expensive call is wrapped in
Streamlit caching so the same session/data is never downloaded twice.

Nothing in this module raises FastF1's raw exceptions out to the UI layer -
callers get either real data or a clear, typed error they can display.
"""

from __future__ import annotations

import os
from typing import List, Optional

import fastf1
import pandas as pd
import streamlit as st

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cache")


class DataLoadError(Exception):
    """Raised when FastF1 cannot provide the requested data."""


def setup_cache():
    """Ensure the FastF1 disk cache directory exists and is enabled.

    Safe to call multiple times (Streamlit reruns the script on every
    interaction) - FastF1 no-ops if the cache is already enabled for the
    same path.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    try:
        fastf1.Cache.enable_cache(CACHE_DIR)
    except Exception:
        # Cache is optional - if it can't be enabled (e.g. read-only fs)
        # the app should still work, just slower.
        pass


# --------------------------------------------------------------------------
# Schedule / event metadata
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def get_season_schedule(year: int) -> pd.DataFrame:
    """Return the event schedule for a season (cached)."""
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as exc:
        raise DataLoadError(f"Could not load the {year} season schedule: {exc}") from exc
    if schedule is None or schedule.empty:
        raise DataLoadError(f"No events found for the {year} season.")
    return schedule


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def get_event_names(year: int) -> List[str]:
    """List of Grand Prix names available for a season, in calendar order."""
    schedule = get_season_schedule(year)
    schedule = schedule.sort_values("RoundNumber")
    return schedule["EventName"].dropna().tolist()


@st.cache_data(show_spinner=False, ttl=60 * 60 * 12)
def get_available_sessions(year: int, event_name: str) -> List[str]:
    """Return display labels of sessions that actually exist for this event
    (handles conventional vs sprint weekends automatically)."""
    from config import ALL_SESSION_LABELS

    schedule = get_season_schedule(year)
    row = schedule[schedule["EventName"] == event_name]
    if row.empty:
        return ALL_SESSION_LABELS
    row = row.iloc[0]

    labels = []
    for i in range(1, 6):
        col = f"Session{i}"
        if col in row and isinstance(row[col], str) and row[col].strip():
            session_name = row[col].strip()
            labels.append(_normalize_session_label(session_name))
    # De-duplicate while preserving order
    seen = set()
    ordered = []
    for label in labels:
        if label not in seen:
            seen.add(label)
            ordered.append(label)
    return ordered


def _normalize_session_label(raw_name: str) -> str:
    mapping = {
        "Practice 1": "Practice 1",
        "Practice 2": "Practice 2",
        "Practice 3": "Practice 3",
        "Qualifying": "Qualifying",
        "Sprint": "Sprint",
        "Sprint Qualifying": "Sprint Qualifying",
        "Sprint Shootout": "Sprint Shootout",
        "Race": "Race",
    }
    return mapping.get(raw_name, raw_name)


# --------------------------------------------------------------------------
# Session loading
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner=False)
def load_session(year: int, event_name: str, session_label: str):
    """Load and return a fastf1.core.Session with laps/telemetry/weather.

    Cached as a resource (not plain data) because Session objects are not
    cheaply hashable/picklable in the way st.cache_data expects.
    """
    from config import SESSION_TYPE_MAP

    session_code = SESSION_TYPE_MAP.get(session_label, session_label)
    try:
        session = fastf1.get_session(year, event_name, session_code)
        session.load(laps=True, telemetry=True, weather=True, messages=True)
    except Exception as exc:
        raise DataLoadError(
            f"Could not load {session_label} data for {event_name} {year}: {exc}"
        ) from exc
    return session


def session_cache_key(year: int, event_name: str, session_label: str) -> str:
    return f"{year}-{event_name}-{session_label}"


# --------------------------------------------------------------------------
# Drivers
# --------------------------------------------------------------------------
def get_session_driver_codes(session) -> List[str]:
    """3-letter driver abbreviations present in this session, sorted."""
    if session is None or session.laps is None or session.laps.empty:
        try:
            drivers = session.drivers
            codes = [session.get_driver(d)["Abbreviation"] for d in drivers]
            return sorted(set(codes))
        except Exception:
            return []
    codes = session.laps["Driver"].dropna().unique().tolist()
    return sorted(codes)


def get_driver_info(session, driver_code: str) -> Optional[dict]:
    try:
        info = session.get_driver(driver_code)
        return dict(info)
    except Exception:
        return None


def get_driver_team_color(session, driver_code: str) -> Optional[str]:
    """Team colour for a driver in this session, via FastF1's plotting
    helpers (falls back to None if unavailable, e.g. very old seasons)."""
    try:
        from fastf1.plotting import get_driver_color
        return get_driver_color(driver_code, session=session)
    except Exception:
        pass
    try:
        from fastf1.plotting import get_team_color
        laps = session.laps.pick_drivers(driver_code)
        if laps.empty:
            return None
        team = laps.iloc[0].get("Team")
        if team is None:
            return None
        return get_team_color(team, session=session)
    except Exception:
        return None


# --------------------------------------------------------------------------
# Laps
# --------------------------------------------------------------------------
def get_driver_laps(session, driver_code: str) -> pd.DataFrame:
    """All laps for a driver, unmodified (caller decides how to filter)."""
    if session is None or session.laps is None:
        return pd.DataFrame()
    try:
        laps = session.laps.pick_drivers(driver_code).copy()
    except Exception:
        return pd.DataFrame()
    return laps.reset_index(drop=True)


def get_all_laps(session) -> pd.DataFrame:
    if session is None or session.laps is None:
        return pd.DataFrame()
    return session.laps.copy()


# --------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------
def get_weather_data(session) -> pd.DataFrame:
    try:
        weather = session.weather_data
        if weather is None:
            return pd.DataFrame()
        return weather.copy()
    except Exception:
        return pd.DataFrame()


# --------------------------------------------------------------------------
# Telemetry
# --------------------------------------------------------------------------
def get_fastest_lap(session, driver_code: str):
    """Return the fastest valid Lap object for a driver, or None."""
    laps = get_driver_laps(session, driver_code)
    if laps.empty:
        return None
    try:
        valid = laps.pick_quicklaps() if hasattr(laps, "pick_quicklaps") else laps
        if valid.empty:
            valid = laps
        fastest = valid.pick_fastest()
        if fastest is None or (hasattr(fastest, "empty") and fastest.empty):
            return None
        return fastest
    except Exception:
        try:
            return laps.pick_fastest()
        except Exception:
            return None


def get_lap_telemetry(lap) -> pd.DataFrame:
    """Telemetry (with distance/relative-distance channels) for a single Lap."""
    if lap is None:
        return pd.DataFrame()
    try:
        tel = lap.get_telemetry()
        if tel is None or tel.empty:
            return pd.DataFrame()
        return tel
    except Exception:
        return pd.DataFrame()


def get_driver_fastest_telemetry(session, driver_code: str) -> pd.DataFrame:
    lap = get_fastest_lap(session, driver_code)
    return get_lap_telemetry(lap)


def get_circuit_info(session):
    try:
        return session.get_circuit_info()
    except Exception:
        return None
