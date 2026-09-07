"""
charts.py
---------
All Plotly figure construction lives here. Every function takes already
computed / cleaned data (from analysis.py or data.py) and returns a
go.Figure - no data loading or heavy computation happens in this module.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import (
    COMPOUND_COLORS,
    DRIVER_1_FALLBACK_COLOR,
    DRIVER_2_FALLBACK_COLOR,
    FONT_COLOR,
    GRID_COLOR,
    PAPER_BG,
    PLOT_BG,
    PLOTLY_TEMPLATE,
)


def _base_layout(fig: go.Figure, title: str = "", height: int = 450, x_title: str = "", y_title: str = ""):
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=dict(text=title, font=dict(size=16, color=FONT_COLOR, family="Titillium Web, sans-serif")),
        paper_bgcolor=PAPER_BG,
        plot_bgcolor=PLOT_BG,
        font=dict(color=FONT_COLOR, family="Inter, sans-serif"),
        height=height,
        margin=dict(l=50, r=30, t=60, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    fig.update_xaxes(title=x_title, gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_yaxes(title=y_title, gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    return fig


def empty_figure(message: str = "No data available") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message, showarrow=False, font=dict(size=15, color=FONT_COLOR),
        xref="paper", yref="paper", x=0.5, y=0.5,
    )
    return _base_layout(fig, height=300)


# --------------------------------------------------------------------------
# Lap time analysis
# --------------------------------------------------------------------------
def lap_times_chart(laps_by_driver: dict, colors: dict) -> go.Figure:
    """laps_by_driver: {code: DataFrame with LapNumber, LapTimeSeconds}"""
    fig = go.Figure()
    any_data = False
    for code, df in laps_by_driver.items():
        if df is None or df.empty or "LapTimeSeconds" not in df.columns:
            continue
        plot_df = df.dropna(subset=["LapTimeSeconds"])
        if plot_df.empty:
            continue
        any_data = True
        color = colors.get(code, DRIVER_1_FALLBACK_COLOR)
        fig.add_trace(go.Scatter(
            x=plot_df["LapNumber"], y=plot_df["LapTimeSeconds"],
            mode="lines+markers", name=code,
            line=dict(color=color, width=2),
            marker=dict(size=6),
            hovertemplate=f"{code}<br>Lap %{{x}}<br>%{{y:.3f}}s<extra></extra>",
        ))
        fastest_idx = plot_df["LapTimeSeconds"].idxmin()
        fig.add_trace(go.Scatter(
            x=[plot_df.loc[fastest_idx, "LapNumber"]], y=[plot_df.loc[fastest_idx, "LapTimeSeconds"]],
            mode="markers", name=f"{code} fastest",
            marker=dict(size=13, color=color, symbol="star", line=dict(width=1, color="white")),
            hovertemplate=f"{code} fastest lap<br>Lap %{{x}}<br>%{{y:.3f}}s<extra></extra>",
        ))
        avg = plot_df["LapTimeSeconds"].mean()
        fig.add_hline(y=avg, line_dash="dot", line_color=color, opacity=0.5,
                       annotation_text=f"{code} avg", annotation_font_color=color)
    if not any_data:
        return empty_figure("No valid lap times to display")
    return _base_layout(fig, title="Lap Times by Driver", x_title="Lap Number", y_title="Lap Time (s)", height=480)


def lap_delta_chart(delta_df: pd.DataFrame, code1: str, code2: str) -> go.Figure:
    if delta_df is None or delta_df.empty:
        return empty_figure("No overlapping laps between the two drivers")
    fig = go.Figure()
    colors = np.where(delta_df["DeltaSeconds"] < 0, DRIVER_1_FALLBACK_COLOR, DRIVER_2_FALLBACK_COLOR)
    fig.add_trace(go.Bar(
        x=delta_df["LapNumber"], y=delta_df["DeltaSeconds"],
        marker_color=list(colors),
        hovertemplate="Lap %{x}<br>Δ %{y:.3f}s<extra></extra>",
        name="Delta",
    ))
    fig.add_hline(y=0, line_color=FONT_COLOR, opacity=0.4)
    faster1 = (delta_df["DeltaSeconds"] < 0).mean() * 100 if len(delta_df) else 0
    fig = _base_layout(
        fig,
        title=f"Lap Time Delta ({code1} − {code2}) — negative bars = {code1} faster",
        x_title="Lap Number", y_title="Delta (s)", height=420,
    )
    fig.add_annotation(
        text=f"{code1} faster on {faster1:.0f}% of common laps",
        xref="paper", yref="paper", x=0.01, y=1.12, showarrow=False,
        font=dict(size=12, color=FONT_COLOR),
    )
    return fig


def sector_comparison_chart(sector_df: pd.DataFrame, code1: str, code2: str, color1: str, color2: str) -> go.Figure:
    if sector_df is None or sector_df.empty:
        return empty_figure("No sector data available")
    d1_vals = sector_df[code1].apply(lambda t: t.total_seconds() if pd.notna(t) else None)
    d2_vals = sector_df[code2].apply(lambda t: t.total_seconds() if pd.notna(t) else None)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=sector_df["Sector"], y=d1_vals, name=code1, marker_color=color1))
    fig.add_trace(go.Bar(x=sector_df["Sector"], y=d2_vals, name=code2, marker_color=color2))
    fig.update_layout(barmode="group")
    return _base_layout(fig, title="Best Sector Times", x_title="Sector", y_title="Time (s)", height=400)


# --------------------------------------------------------------------------
# Tyre strategy
# --------------------------------------------------------------------------
def tyre_strategy_chart(stints_df: pd.DataFrame) -> go.Figure:
    if stints_df is None or stints_df.empty:
        return empty_figure("No stint data available")

    drivers = stints_df["Driver"].unique().tolist()
    fig = go.Figure()
    for i, drv in enumerate(drivers):
        drv_stints = stints_df[stints_df["Driver"] == drv]
        for _, row in drv_stints.iterrows():
            compound = str(row["Compound"]).upper() if pd.notna(row["Compound"]) else "UNKNOWN"
            color = COMPOUND_COLORS.get(compound, COMPOUND_COLORS["UNKNOWN"])
            fig.add_trace(go.Bar(
                y=[drv],
                x=[row["StintLength"]],
                base=[row["StartLap"] - 1],
                orientation="h",
                marker=dict(color=color, line=dict(color="#0a0a0f", width=1.5)),
                name=compound,
                legendgroup=compound,
                showlegend=compound not in [t.name for t in fig.data],
                hovertemplate=(
                    f"{drv}<br>{compound}<br>Laps {int(row['StartLap'])}-{int(row['EndLap'])}"
                    f"<br>Length: {int(row['StintLength'])} laps<extra></extra>"
                ),
                text=compound,
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="#0a0a0f", size=11, family="Titillium Web, sans-serif"),
            ))
    fig.update_layout(barmode="stack")
    fig = _base_layout(fig, title="Tyre Strategy by Stint", x_title="Lap Number", y_title="Driver", height=120 + 90 * len(drivers))
    fig.update_layout(showlegend=True)
    return fig


# --------------------------------------------------------------------------
# Tyre degradation
# --------------------------------------------------------------------------
def tyre_degradation_chart(deg_df: pd.DataFrame, colors: dict) -> go.Figure:
    if deg_df is None or deg_df.empty:
        return empty_figure("No tyre degradation data available")
    fig = go.Figure()
    for (driver, stint), group in deg_df.groupby(["Driver", "Stint"]):
        group = group.sort_values("TyreLife")
        compound = str(group["Compound"].iloc[0]).upper() if "Compound" in group.columns else "UNKNOWN"
        base_color = colors.get(driver, DRIVER_1_FALLBACK_COLOR)
        fig.add_trace(go.Scatter(
            x=group["TyreLife"], y=group["LapTimeSeconds"],
            mode="markers+lines",
            name=f"{driver} · Stint {int(stint)} · {compound}",
            line=dict(color=base_color, width=1.5, dash="dot"),
            marker=dict(size=7, color=COMPOUND_COLORS.get(compound, base_color), line=dict(width=1, color=base_color)),
            hovertemplate=f"{driver} ({compound})<br>Tyre life %{{x}}<br>%{{y:.3f}}s<extra></extra>",
        ))
    return _base_layout(fig, title="Tyre Degradation — Lap Time vs Tyre Life", x_title="Tyre Life (laps)", y_title="Lap Time (s)", height=480)


# --------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------
def weather_chart(weather_df: pd.DataFrame) -> go.Figure:
    if weather_df is None or weather_df.empty:
        return empty_figure("No weather data available for this session")
    x = weather_df["Time"].dt.total_seconds() / 60 if "Time" in weather_df.columns else weather_df.index

    fig = go.Figure()
    if "AirTemp" in weather_df.columns:
        fig.add_trace(go.Scatter(x=x, y=weather_df["AirTemp"], name="Air Temp (°C)", line=dict(color="#4FC3F7")))
    if "TrackTemp" in weather_df.columns:
        fig.add_trace(go.Scatter(x=x, y=weather_df["TrackTemp"], name="Track Temp (°C)", line=dict(color="#E10600")))
    if "Humidity" in weather_df.columns:
        fig.add_trace(go.Scatter(x=x, y=weather_df["Humidity"], name="Humidity (%)", line=dict(color="#81C784", dash="dash"), yaxis="y2"))

    fig.update_layout(
        yaxis2=dict(overlaying="y", side="right", title="Humidity (%)", showgrid=False),
    )
    return _base_layout(fig, title="Weather Over the Session", x_title="Session Time (minutes)", y_title="Temperature (°C)", height=420)


def weather_extra_chart(weather_df: pd.DataFrame) -> go.Figure:
    """Wind speed/direction + pressure + rainfall on a secondary chart."""
    if weather_df is None or weather_df.empty:
        return empty_figure("No weather data available")
    x = weather_df["Time"].dt.total_seconds() / 60 if "Time" in weather_df.columns else weather_df.index
    fig = go.Figure()
    if "WindSpeed" in weather_df.columns:
        fig.add_trace(go.Scatter(x=x, y=weather_df["WindSpeed"], name="Wind Speed (m/s)", line=dict(color="#FFB800")))
    if "Pressure" in weather_df.columns:
        fig.add_trace(go.Scatter(x=x, y=weather_df["Pressure"], name="Pressure (mbar)", line=dict(color="#BA68C8"), yaxis="y2"))
    if "Rainfall" in weather_df.columns:
        rain = weather_df["Rainfall"].astype(int) if weather_df["Rainfall"].dtype == bool else weather_df["Rainfall"]
        fig.add_trace(go.Bar(x=x, y=rain, name="Rainfall", marker_color="#4FC3F7", opacity=0.5))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", title="Pressure (mbar)", showgrid=False))
    return _base_layout(fig, title="Wind, Pressure & Rainfall", x_title="Session Time (minutes)", y_title="Wind Speed (m/s)", height=380)


# --------------------------------------------------------------------------
# Track evolution
# --------------------------------------------------------------------------
def track_evolution_chart(evo_df: pd.DataFrame) -> go.Figure:
    if evo_df is None or evo_df.empty:
        return empty_figure("Not enough clean laps to estimate track evolution")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=evo_df["LapNumber"], y=evo_df["LapTimeSeconds"], mode="markers",
        name="Median lap time", marker=dict(size=6, color="#4FC3F7", opacity=0.6),
    ))
    fig.add_trace(go.Scatter(
        x=evo_df["LapNumber"], y=evo_df["RollingAvgSeconds"], mode="lines",
        name="Rolling average", line=dict(color="#FFB800", width=3),
    ))
    return _base_layout(fig, title="Track Evolution — Session Pace Trend", x_title="Lap Number", y_title="Lap Time (s)", height=440)


# --------------------------------------------------------------------------
# Telemetry
# --------------------------------------------------------------------------
_TELEMETRY_CHANNELS = {
    "Speed": ("Speed (km/h)", "#E10600"),
    "Throttle": ("Throttle (%)", "#43B02A"),
    "Brake": ("Brake", "#4FC3F7"),
    "nGear": ("Gear", "#FFB800"),
    "DRS": ("DRS", "#BA68C8"),
}


def telemetry_channel_chart(tel: pd.DataFrame, channel: str, driver_code: str, color: str) -> go.Figure:
    if tel is None or tel.empty or channel not in tel.columns or "Distance" not in tel.columns:
        return empty_figure(f"No {channel} telemetry available")
    label, default_color = _TELEMETRY_CHANNELS.get(channel, (channel, color))
    fig = go.Figure()
    y = tel[channel]
    if channel == "Brake" and y.dtype == bool:
        y = y.astype(int)
    fig.add_trace(go.Scatter(
        x=tel["Distance"], y=y, mode="lines", name=driver_code,
        line=dict(color=color, width=2), fill="tozeroy" if channel in ("Throttle", "Brake", "DRS") else None,
    ))
    return _base_layout(fig, title=f"{label} vs Distance — {driver_code}", x_title="Distance (m)", y_title=label, height=320)


def telemetry_comparison_chart(tel1: pd.DataFrame, aligned_tel2: pd.DataFrame, channel: str,
                                code1: str, code2: str, color1: str, color2: str) -> go.Figure:
    if tel1 is None or tel1.empty or channel not in tel1.columns:
        return empty_figure(f"No {channel} telemetry available")
    label, _ = _TELEMETRY_CHANNELS.get(channel, (channel, color1))
    fig = go.Figure()
    y1 = tel1[channel]
    if channel == "Brake" and y1.dtype == bool:
        y1 = y1.astype(int)
    fig.add_trace(go.Scatter(x=tel1["Distance"], y=y1, mode="lines", name=code1, line=dict(color=color1, width=2)))
    if aligned_tel2 is not None and not aligned_tel2.empty and channel in aligned_tel2.columns:
        y2 = aligned_tel2[channel]
        fig.add_trace(go.Scatter(x=aligned_tel2["Distance"], y=y2, mode="lines", name=code2, line=dict(color=color2, width=2)))
    return _base_layout(fig, title=f"{label} vs Distance — {code1} vs {code2}", x_title="Distance (m)", y_title=label, height=360)


# --------------------------------------------------------------------------
# Track map
# --------------------------------------------------------------------------
def track_map_chart(tel_by_driver: dict, colors: dict) -> go.Figure:
    fig = go.Figure()
    any_data = False
    for code, tel in tel_by_driver.items():
        if tel is None or tel.empty or "X" not in tel.columns or "Y" not in tel.columns:
            continue
        any_data = True
        color = colors.get(code, DRIVER_1_FALLBACK_COLOR)
        hover_dist = tel["Distance"] if "Distance" in tel.columns else np.arange(len(tel))
        fig.add_trace(go.Scatter(
            x=tel["X"], y=tel["Y"], mode="lines", name=code,
            line=dict(color=color, width=3),
            customdata=hover_dist,
            hovertemplate=f"{code}<br>Distance: %{{customdata:.0f}}m<extra></extra>",
        ))
    if not any_data:
        return empty_figure("No position telemetry available for the selected driver(s)")
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    fig.update_xaxes(showticklabels=False, gridcolor=PLOT_BG)
    fig.update_yaxes(showticklabels=False, gridcolor=PLOT_BG)
    return _base_layout(fig, title="Circuit Map — Driver Trace", height=560)
