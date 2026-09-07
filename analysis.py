"""
analysis.py
-----------
Pure computation layer: turns raw FastF1 laps/weather/telemetry DataFrames
into the aggregated tables and metrics the dashboard displays. No
Streamlit or Plotly imports here on purpose - this module is UI-agnostic.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from utils.helpers import is_missing, timedelta_to_seconds


# --------------------------------------------------------------------------
# Lap cleaning
# --------------------------------------------------------------------------
def get_valid_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Laps with a real LapTime, not deleted, not an in/out (pit) lap.

    This is the baseline "clean pace" set used for averages/fastest-lap
    comparisons. Safety-car / red-flag laps are excluded via TrackStatus
    when that column is present and unusually slow laps are left in (the
    caller decides whether to filter further using pick_quicklaps-style
    logic) so we don't silently hide real pace variation.
    """
    if laps is None or laps.empty:
        return pd.DataFrame()

    df = laps.copy()

    if "LapTime" in df.columns:
        df = df[df["LapTime"].notna()]

    if "Deleted" in df.columns:
        df = df[df["Deleted"] != True]  # noqa: E712

    if "PitInTime" in df.columns and "PitOutTime" in df.columns:
        df = df[df["PitInTime"].isna() & df["PitOutTime"].isna()]

    if "IsAccurate" in df.columns:
        # Keep accurate laps when the flag exists, but don't drop everything
        # if for some reason nothing is flagged accurate.
        accurate = df[df["IsAccurate"] == True]  # noqa: E712
        if not accurate.empty:
            df = accurate

    return df.reset_index(drop=True)


def laps_excluding_safety_car(laps: pd.DataFrame) -> pd.DataFrame:
    """Best-effort removal of laps run behind Safety Car / VSC / Red Flag,
    using the TrackStatus column when FastF1 provides it.

    TrackStatus codes (FastF1 / F1 timing): 1 clear, 2 yellow, 4 safety car,
    5 red flag, 6 VSC deployed, 7 VSC ending.
    """
    if laps is None or laps.empty or "TrackStatus" not in laps.columns:
        return laps
    disruptive_codes = {"4", "5", "6", "7"}

    def _is_clean(status):
        if is_missing(status):
            return True
        status_str = str(status)
        return not any(code in status_str for code in disruptive_codes)

    mask = laps["TrackStatus"].apply(_is_clean)
    return laps[mask].reset_index(drop=True)


def add_lap_seconds(laps: pd.DataFrame) -> pd.DataFrame:
    """Add a float `LapTimeSeconds` column for easy plotting/aggregation."""
    if laps is None or laps.empty:
        return laps
    df = laps.copy()
    if "LapTime" in df.columns:
        df["LapTimeSeconds"] = timedelta_to_seconds(df["LapTime"])
    for col in ("Sector1Time", "Sector2Time", "Sector3Time"):
        if col in df.columns:
            df[f"{col}Seconds"] = timedelta_to_seconds(df[col])
    return df


# --------------------------------------------------------------------------
# Session overview
# --------------------------------------------------------------------------
def session_overview(session, all_laps: pd.DataFrame, weather: pd.DataFrame) -> dict:
    overview = {
        "event_name": getattr(session.event, "EventName", "N/A") if hasattr(session, "event") else "N/A",
        "circuit": getattr(session.event, "Location", "N/A") if hasattr(session, "event") else "N/A",
        "country": getattr(session.event, "Country", "N/A") if hasattr(session, "event") else "N/A",
        "date": None,
        "session_name": getattr(session, "name", "N/A"),
        "num_drivers": 0,
        "num_laps": 0,
        "fastest_driver": "N/A",
        "fastest_lap_time": None,
        "track_temp": None,
        "air_temp": None,
    }

    try:
        overview["date"] = session.date
    except Exception:
        pass

    clean = add_lap_seconds(get_valid_laps(all_laps))

    if not all_laps.empty and "Driver" in all_laps.columns:
        overview["num_drivers"] = all_laps["Driver"].nunique()
        overview["num_laps"] = int(all_laps["LapNumber"].max()) if "LapNumber" in all_laps.columns and all_laps["LapNumber"].notna().any() else len(all_laps)

    if not clean.empty and "LapTimeSeconds" in clean.columns and clean["LapTimeSeconds"].notna().any():
        idx = clean["LapTimeSeconds"].idxmin()
        overview["fastest_driver"] = clean.loc[idx, "Driver"]
        overview["fastest_lap_time"] = clean.loc[idx, "LapTime"]

    if weather is not None and not weather.empty:
        if "TrackTemp" in weather.columns:
            overview["track_temp"] = weather["TrackTemp"].mean()
        if "AirTemp" in weather.columns:
            overview["air_temp"] = weather["AirTemp"].mean()

    return overview


# --------------------------------------------------------------------------
# Driver comparison
# --------------------------------------------------------------------------
def driver_lap_summary(laps: pd.DataFrame) -> dict:
    """Summary stats for a single driver's laps."""
    clean = add_lap_seconds(get_valid_laps(laps))
    summary = {
        "num_laps_total": int(laps["LapNumber"].max()) if laps is not None and not laps.empty and "LapNumber" in laps.columns and laps["LapNumber"].notna().any() else (0 if laps is None else len(laps)),
        "num_valid_laps": len(clean),
        "avg_lap_time": None,
        "fastest_lap_time": None,
        "fastest_lap_number": None,
        "best_s1": None,
        "best_s2": None,
        "best_s3": None,
    }
    if clean.empty:
        return summary

    if "LapTimeSeconds" in clean.columns and clean["LapTimeSeconds"].notna().any():
        summary["avg_lap_time"] = pd.to_timedelta(clean["LapTimeSeconds"].mean(), unit="s")
        best_idx = clean["LapTimeSeconds"].idxmin()
        summary["fastest_lap_time"] = clean.loc[best_idx, "LapTime"]
        summary["fastest_lap_number"] = clean.loc[best_idx, "LapNumber"] if "LapNumber" in clean.columns else None

    for sec, key in (("Sector1TimeSeconds", "best_s1"), ("Sector2TimeSeconds", "best_s2"), ("Sector3TimeSeconds", "best_s3")):
        if sec in clean.columns and clean[sec].notna().any():
            summary[key] = pd.to_timedelta(clean[sec].min(), unit="s")

    return summary


def compare_drivers(laps_d1: pd.DataFrame, laps_d2: pd.DataFrame, code1: str, code2: str) -> dict:
    s1 = driver_lap_summary(laps_d1)
    s2 = driver_lap_summary(laps_d2)

    def _to_seconds(td):
        if td is None or pd.isna(td):
            return None
        return td.total_seconds()

    fastest_diff = None
    f1s, f2s = _to_seconds(s1["fastest_lap_time"]), _to_seconds(s2["fastest_lap_time"])
    if f1s is not None and f2s is not None:
        fastest_diff = f1s - f2s

    avg_diff = None
    a1s, a2s = _to_seconds(s1["avg_lap_time"]), _to_seconds(s2["avg_lap_time"])
    if a1s is not None and a2s is not None:
        avg_diff = a1s - a2s

    return {
        code1: s1,
        code2: s2,
        "fastest_diff_seconds": fastest_diff,  # positive => driver1 slower
        "avg_diff_seconds": avg_diff,
    }


def lap_delta_by_lap_number(laps_d1: pd.DataFrame, laps_d2: pd.DataFrame) -> pd.DataFrame:
    """Merge two drivers' lap times on LapNumber and compute the delta
    (driver1 - driver2) in seconds, for the classic delta-per-lap chart."""
    c1 = add_lap_seconds(get_valid_laps(laps_d1))[["LapNumber", "LapTimeSeconds"]].rename(
        columns={"LapTimeSeconds": "Driver1Seconds"}
    )
    c2 = add_lap_seconds(get_valid_laps(laps_d2))[["LapNumber", "LapTimeSeconds"]].rename(
        columns={"LapTimeSeconds": "Driver2Seconds"}
    )
    merged = pd.merge(c1, c2, on="LapNumber", how="inner").sort_values("LapNumber")
    merged["DeltaSeconds"] = merged["Driver1Seconds"] - merged["Driver2Seconds"]
    return merged.reset_index(drop=True)


def sector_comparison_table(laps_d1: pd.DataFrame, laps_d2: pd.DataFrame, code1: str, code2: str) -> pd.DataFrame:
    s1 = driver_lap_summary(laps_d1)
    s2 = driver_lap_summary(laps_d2)
    rows = []
    for label, key in (("Sector 1", "best_s1"), ("Sector 2", "best_s2"), ("Sector 3", "best_s3")):
        rows.append({
            "Sector": label,
            code1: s1[key],
            code2: s2[key],
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Tyre stints
# --------------------------------------------------------------------------
def build_stints(laps: pd.DataFrame, driver_code: str) -> pd.DataFrame:
    """Reconstruct stint-by-stint tyre usage for a driver."""
    if laps is None or laps.empty or "Stint" not in laps.columns:
        return pd.DataFrame()

    df = laps.copy()
    df = df[df["LapNumber"].notna()]
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby("Stint")
    rows = []
    for stint_no, g in grouped:
        g = g.sort_values("LapNumber")
        start_lap = int(g["LapNumber"].min())
        end_lap = int(g["LapNumber"].max())
        compound = g["Compound"].mode().iloc[0] if "Compound" in g.columns and not g["Compound"].mode().empty else "UNKNOWN"
        tyre_life = g["TyreLife"].max() if "TyreLife" in g.columns and g["TyreLife"].notna().any() else np.nan
        fresh = g["FreshTyre"].iloc[0] if "FreshTyre" in g.columns and g["FreshTyre"].notna().any() else None
        clean_g = add_lap_seconds(get_valid_laps(g))
        avg_pace = clean_g["LapTimeSeconds"].mean() if not clean_g.empty and clean_g["LapTimeSeconds"].notna().any() else np.nan
        best_pace = clean_g["LapTimeSeconds"].min() if not clean_g.empty and clean_g["LapTimeSeconds"].notna().any() else np.nan
        rows.append({
            "Driver": driver_code,
            "Stint": int(stint_no) if not pd.isna(stint_no) else None,
            "Compound": compound,
            "StartLap": start_lap,
            "EndLap": end_lap,
            "StintLength": end_lap - start_lap + 1,
            "TyreLife": tyre_life,
            "FreshTyre": fresh,
            "AvgLapTimeSeconds": avg_pace,
            "BestLapTimeSeconds": best_pace,
            "NumLaps": len(g),
        })
    result = pd.DataFrame(rows).sort_values("Stint").reset_index(drop=True)
    return result


def stint_table_multi(laps_by_driver: dict) -> pd.DataFrame:
    """Combine build_stints() output across multiple drivers into one table."""
    frames = []
    for code, laps in laps_by_driver.items():
        stints = build_stints(laps, code)
        if not stints.empty:
            frames.append(stints)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------
# Tyre degradation
# --------------------------------------------------------------------------
def tyre_degradation_data(laps: pd.DataFrame, driver_code: str) -> pd.DataFrame:
    """Per-lap pace vs tyre life, tagged by stint/compound, for scatter plots.

    Deliberately keeps fuel/traffic/track-evolution as caveats in the UI
    layer rather than trying to "correct" for them numerically here - doing
    that correctly needs a physical fuel model this dashboard doesn't claim
    to have.
    """
    if laps is None or laps.empty:
        return pd.DataFrame()
    df = add_lap_seconds(get_valid_laps(laps))
    if df.empty:
        return pd.DataFrame()
    keep_cols = [c for c in ["LapNumber", "LapTimeSeconds", "TyreLife", "Compound", "Stint", "FreshTyre"] if c in df.columns]
    df = df[keep_cols].copy()
    df["Driver"] = driver_code
    return df.dropna(subset=["LapTimeSeconds"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Track evolution
# --------------------------------------------------------------------------
def track_evolution_data(all_laps: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Session-wide median lap time per lap number plus a rolling average,
    used as a simple proxy for track evolution over the session."""
    if all_laps is None or all_laps.empty:
        return pd.DataFrame()
    df = add_lap_seconds(get_valid_laps(all_laps))
    if df.empty or "LapNumber" not in df.columns:
        return pd.DataFrame()
    grouped = df.groupby("LapNumber")["LapTimeSeconds"].median().reset_index()
    grouped = grouped.sort_values("LapNumber")
    grouped["RollingAvgSeconds"] = grouped["LapTimeSeconds"].rolling(window=window, min_periods=1).mean()
    return grouped.reset_index(drop=True)


# --------------------------------------------------------------------------
# Session summary
# --------------------------------------------------------------------------
def build_session_summary(laps_d1, laps_d2, code1, code2) -> dict:
    comparison = compare_drivers(laps_d1, laps_d2, code1, code2)
    stints1 = build_stints(laps_d1, code1)
    stints2 = build_stints(laps_d2, code2)
    comparison[code1]["compounds"] = stints1["Compound"].tolist() if not stints1.empty else []
    comparison[code2]["compounds"] = stints2["Compound"].tolist() if not stints2.empty else []
    comparison[code1]["num_stints"] = len(stints1)
    comparison[code2]["num_stints"] = len(stints2)
    return comparison


# --------------------------------------------------------------------------
# Telemetry alignment
# --------------------------------------------------------------------------
def align_telemetry_on_distance(tel1: pd.DataFrame, tel2: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Interpolate driver 2's telemetry onto driver 1's distance grid so the
    two can be compared/plotted on a shared X axis."""
    if tel1 is None or tel1.empty or tel2 is None or tel2.empty:
        return None
    if "Distance" not in tel1.columns or "Distance" not in tel2.columns:
        return None

    base = tel1[["Distance"]].dropna().sort_values("Distance").reset_index(drop=True)
    t2 = tel2.dropna(subset=["Distance"]).sort_values("Distance").reset_index(drop=True)

    aligned = pd.DataFrame({"Distance": base["Distance"]})
    numeric_channels = [c for c in ["Speed", "Throttle", "Brake", "nGear", "RPM", "DRS"] if c in t2.columns]
    for ch in numeric_channels:
        aligned[ch] = np.interp(base["Distance"], t2["Distance"], pd.to_numeric(t2[ch], errors="coerce"))
    return aligned
