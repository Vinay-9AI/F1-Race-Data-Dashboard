"""
app.py
------
F1 Race Data Dashboard - Streamlit entry point.

Run with:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

import analysis
import charts
import data
from config import (
    ALL_SESSION_LABELS,
    APP_ICON,
    APP_TITLE,
    DEFAULT_DRIVER_1,
    DEFAULT_DRIVER_2,
    DEFAULT_GP,
    DEFAULT_SEASON,
    DEFAULT_SESSION,
    DRIVER_1_FALLBACK_COLOR,
    DRIVER_2_FALLBACK_COLOR,
    MAX_SEASON,
    MIN_SEASON,
    configure_page,
    inject_custom_css,
    section_title,
)
from data import DataLoadError
from utils.helpers import (
    df_has_rows,
    format_timedelta,
    guard,
    safe_get,
    safe_round,
    safe_section,
    seconds_to_laptime_str,
    team_color_hex,
)

configure_page()
inject_custom_css()
data.setup_cache()

NAV_SECTIONS = [
    "Dashboard",
    "Driver Comparison",
    "Lap Analysis",
    "Tyre Strategy",
    "Tyre Degradation",
    "Stint Analysis",
    "Weather",
    "Track Evolution",
    "Telemetry",
    "Telemetry Comparison",
    "Track Map",
    "Session Summary",
]

NAV_ICONS = {
    "Dashboard": "🏁",
    "Driver Comparison": "⚔️",
    "Lap Analysis": "⏱️",
    "Tyre Strategy": "🛞",
    "Tyre Degradation": "📉",
    "Stint Analysis": "📋",
    "Weather": "🌦️",
    "Track Evolution": "📈",
    "Telemetry": "📡",
    "Telemetry Comparison": "🔀",
    "Track Map": "🗺️",
    "Session Summary": "🧾",
}


# ==========================================================================
# Sidebar - session selection & navigation
# ==========================================================================
def render_sidebar():
    st.sidebar.markdown(
        f'<div class="f1-brand">{APP_ICON} F1 RACE <span>DATA</span> DASHBOARD</div>',
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("#### Session Selection")

    season = st.sidebar.selectbox(
        "Season",
        options=list(range(MAX_SEASON, MIN_SEASON - 1, -1)),
        index=list(range(MAX_SEASON, MIN_SEASON - 1, -1)).index(DEFAULT_SEASON)
        if DEFAULT_SEASON in range(MIN_SEASON, MAX_SEASON + 1) else 0,
        key="season",
    )

    try:
        event_names = data.get_event_names(season)
    except DataLoadError as exc:
        st.sidebar.error(str(exc))
        event_names = []

    if not event_names:
        st.sidebar.warning("No events found for this season.")
        return None

    default_gp_index = event_names.index(DEFAULT_GP) if DEFAULT_GP in event_names else 0
    # try a partial match (e.g. "Monaco" vs "Monaco Grand Prix")
    if DEFAULT_GP not in event_names:
        matches = [e for e in event_names if DEFAULT_GP.lower() in e.lower()]
        if matches:
            default_gp_index = event_names.index(matches[0])

    grand_prix = st.sidebar.selectbox("Grand Prix", options=event_names, index=default_gp_index, key="grand_prix")

    try:
        available_sessions = data.get_available_sessions(season, grand_prix)
    except DataLoadError as exc:
        st.sidebar.error(str(exc))
        available_sessions = ALL_SESSION_LABELS
    if not available_sessions:
        available_sessions = ALL_SESSION_LABELS

    default_session_index = (
        available_sessions.index(DEFAULT_SESSION) if DEFAULT_SESSION in available_sessions else 0
    )
    session_label = st.sidebar.selectbox(
        "Session", options=available_sessions, index=default_session_index, key="session_label"
    )

    load_clicked = st.sidebar.button("🔄 Load Session", use_container_width=True)

    state_key = data.session_cache_key(season, grand_prix, session_label)
    is_first_run = "_loaded_key" not in st.session_state
    selection_changed = st.session_state.get("_loaded_key") != state_key

    # Auto-load once on first run (gives the default 2024 Monaco Race demo
    # for free) or whenever the user explicitly clicks Load Session.
    if load_clicked or (is_first_run and selection_changed):
        with st.spinner(f"Loading {grand_prix} {season} — {session_label}..."):
            try:
                session_obj = data.load_session(season, grand_prix, session_label)
                st.session_state["_session_obj"] = session_obj
                st.session_state["_loaded_key"] = state_key
                st.session_state["_loaded_meta"] = (season, grand_prix, session_label)
            except DataLoadError as exc:
                st.sidebar.error(str(exc))

    session_obj = st.session_state.get("_session_obj")
    if session_obj is None:
        st.sidebar.info("Select a session and click **Load Session**.")
        st.stop()

    if st.session_state.get("_loaded_key") != state_key:
        st.sidebar.warning("Selections changed — click **Load Session** to load the new session.")

    # Use the metadata of the session that is actually loaded (not
    # necessarily the current dropdown values, if the user hasn't clicked
    # Load Session yet after changing them) so the UI stays consistent
    # with the data actually being displayed.
    season, grand_prix, session_label = st.session_state.get(
        "_loaded_meta", (season, grand_prix, session_label)
    )

    driver_codes = data.get_session_driver_codes(session_obj)
    if not driver_codes:
        st.sidebar.error("No driver data available for this session.")
        st.stop()

    st.sidebar.markdown("#### Driver Selection")
    d1_index = driver_codes.index(DEFAULT_DRIVER_1) if DEFAULT_DRIVER_1 in driver_codes else 0
    driver1 = st.sidebar.selectbox("Driver 1", options=driver_codes, index=d1_index, key="driver1")

    remaining = [d for d in driver_codes if d != driver1]
    d2_index = remaining.index(DEFAULT_DRIVER_2) if DEFAULT_DRIVER_2 in remaining else 0
    driver2 = st.sidebar.selectbox("Driver 2", options=remaining, index=d2_index, key="driver2")

    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Navigation")
    nav = st.sidebar.radio(
        "Go to",
        options=NAV_SECTIONS,
        format_func=lambda x: f"{NAV_ICONS.get(x, '')}  {x}",
        label_visibility="collapsed",
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("Data © Formula 1 via the FastF1 Python package. Not affiliated with F1.")

    return {
        "season": season,
        "grand_prix": grand_prix,
        "session_label": session_label,
        "session_obj": session_obj,
        "driver_codes": driver_codes,
        "driver1": driver1,
        "driver2": driver2,
        "nav": nav,
    }


# ==========================================================================
# Cached, derived data for the current selection
# ==========================================================================
def get_context(ctx: dict) -> dict:
    session_obj = ctx["session_obj"]
    d1, d2 = ctx["driver1"], ctx["driver2"]

    all_laps = data.get_all_laps(session_obj)
    weather = data.get_weather_data(session_obj)
    laps_d1 = data.get_driver_laps(session_obj, d1)
    laps_d2 = data.get_driver_laps(session_obj, d2)

    color1 = team_color_hex(data.get_driver_team_color(session_obj, d1), DRIVER_1_FALLBACK_COLOR)
    color2 = team_color_hex(data.get_driver_team_color(session_obj, d2), DRIVER_2_FALLBACK_COLOR)
    if color1 == color2:
        color2 = DRIVER_2_FALLBACK_COLOR if color1 != DRIVER_2_FALLBACK_COLOR else DRIVER_1_FALLBACK_COLOR

    return {
        **ctx,
        "all_laps": all_laps,
        "weather": weather,
        "laps_d1": laps_d1,
        "laps_d2": laps_d2,
        "color1": color1,
        "color2": color2,
        "colors": {d1: color1, d2: color2},
    }


# ==========================================================================
# Sections
# ==========================================================================
@safe_section("Dashboard Overview")
def render_dashboard(c: dict):
    st.title(f"{APP_ICON} F1 Race Data Dashboard")
    overview = analysis.session_overview(c["session_obj"], c["all_laps"], c["weather"])

    section_title(
        f"{overview['event_name']} — {overview['session_name']}",
        f"{overview['circuit']}, {overview['country']}"
        + (f" · {pd.Timestamp(overview['date']).strftime('%d %b %Y')}" if overview["date"] is not None else ""),
    )

    row1 = st.columns(4)
    row1[0].metric("Session", overview["session_name"] or "N/A")
    row1[1].metric("Circuit", overview["circuit"] or "N/A")
    row1[2].metric("Number of Drivers", overview["num_drivers"] or "N/A")
    row1[3].metric("Number of Laps", overview["num_laps"] or "N/A")

    row2 = st.columns(4)
    row2[0].metric("Fastest Driver", overview["fastest_driver"] or "N/A")
    row2[1].metric("Fastest Lap", format_timedelta(overview["fastest_lap_time"]))
    row2[2].metric("Track Temp", f"{safe_round(overview['track_temp'], 1)} °C" if overview["track_temp"] is not None else "N/A")
    row2[3].metric("Air Temp", f"{safe_round(overview['air_temp'], 1)} °C" if overview["air_temp"] is not None else "N/A")

    st.markdown("")
    with st.expander("ℹ️ About this dashboard"):
        st.write(
            "This dashboard loads real session data via FastF1 for the selected season, "
            "Grand Prix and session, then derives every chart and table below from that "
            "data. Use the sidebar to change the session or the two drivers being compared."
        )


@safe_section("Driver Comparison")
def render_driver_comparison(c: dict):
    st.title("⚔️ Driver Comparison")
    d1, d2 = c["driver1"], c["driver2"]
    if not guard(df_has_rows(c["laps_d1"]) or df_has_rows(c["laps_d2"]), "No lap data available for the selected drivers."):
        return

    comparison = analysis.compare_drivers(c["laps_d1"], c["laps_d2"], d1, d2)
    s1, s2 = comparison[d1], comparison[d2]

    cols = st.columns(4)
    cols[0].metric(f"{d1} Fastest Lap", format_timedelta(s1["fastest_lap_time"]))
    cols[1].metric(f"{d2} Fastest Lap", format_timedelta(s2["fastest_lap_time"]))
    diff = comparison["fastest_diff_seconds"]
    faster = d1 if (diff is not None and diff < 0) else d2 if diff is not None else "N/A"
    cols[2].metric("Fastest Lap Δ", f"{abs(diff):.3f}s" if diff is not None else "N/A", delta=f"{faster} faster" if diff is not None else None)
    avg_diff = comparison["avg_diff_seconds"]
    avg_faster = d1 if (avg_diff is not None and avg_diff < 0) else d2 if avg_diff is not None else "N/A"
    cols[3].metric("Average Lap Δ", f"{abs(avg_diff):.3f}s" if avg_diff is not None else "N/A", delta=f"{avg_faster} faster" if avg_diff is not None else None)

    cols2 = st.columns(4)
    cols2[0].metric(f"{d1} Avg Lap", format_timedelta(s1["avg_lap_time"]))
    cols2[1].metric(f"{d2} Avg Lap", format_timedelta(s2["avg_lap_time"]))
    cols2[2].metric(f"{d1} Valid Laps", s1["num_valid_laps"])
    cols2[3].metric(f"{d2} Valid Laps", s2["num_valid_laps"])

    section_title("Lap Time Delta (Lap by Lap)", f"Negative bars mean {d1} was faster on that lap.")
    delta_df = analysis.lap_delta_by_lap_number(c["laps_d1"], c["laps_d2"])
    st.plotly_chart(charts.lap_delta_chart(delta_df, d1, d2), use_container_width=True)

    section_title("Best Sector Times")
    sector_df = analysis.sector_comparison_table(c["laps_d1"], c["laps_d2"], d1, d2)
    st.plotly_chart(charts.sector_comparison_chart(sector_df, d1, d2, c["color1"], c["color2"]), use_container_width=True)


@safe_section("Lap Time Analysis")
def render_lap_analysis(c: dict):
    st.title("⏱️ Lap Time Analysis")
    all_codes = c["driver_codes"]
    default_selection = [c["driver1"], c["driver2"]]
    selected = st.multiselect("Filter drivers", options=all_codes, default=default_selection)
    if not guard(bool(selected), "Select at least one driver."):
        return

    laps_by_driver = {}
    for code in selected:
        laps = data.get_driver_laps(c["session_obj"], code)
        laps_by_driver[code] = analysis.add_lap_seconds(analysis.get_valid_laps(laps))

    palette_colors = {c["driver1"]: c["color1"], c["driver2"]: c["color2"]}
    colors = {code: palette_colors.get(code, DRIVER_1_FALLBACK_COLOR if i % 2 == 0 else DRIVER_2_FALLBACK_COLOR)
              for i, code in enumerate(selected)}

    st.plotly_chart(charts.lap_times_chart(laps_by_driver, colors), use_container_width=True)

    with st.expander("Data quality notes"):
        st.write(
            "Deleted laps, pit in/out laps, and laps without a recorded time are excluded "
            "from this view. Where FastF1 flags accurate laps, only those are shown."
        )


@safe_section("Tyre Strategy")
def render_tyre_strategy(c: dict):
    st.title("🛞 Tyre Strategy")
    stints1 = analysis.build_stints(c["laps_d1"], c["driver1"])
    stints2 = analysis.build_stints(c["laps_d2"], c["driver2"])
    combined = pd.concat([df for df in (stints1, stints2) if not df.empty], ignore_index=True) if (not stints1.empty or not stints2.empty) else pd.DataFrame()
    if not guard(df_has_rows(combined), "No stint/tyre data available for this session."):
        return
    st.plotly_chart(charts.tyre_strategy_chart(combined), use_container_width=True)

    section_title("Stint Details")
    display_cols = ["Driver", "Stint", "Compound", "StartLap", "EndLap", "StintLength", "TyreLife", "FreshTyre"]
    st.dataframe(combined[display_cols], use_container_width=True, hide_index=True)


@safe_section("Tyre Degradation")
def render_tyre_degradation(c: dict):
    st.title("📉 Tyre Degradation")
    deg1 = analysis.tyre_degradation_data(c["laps_d1"], c["driver1"])
    deg2 = analysis.tyre_degradation_data(c["laps_d2"], c["driver2"])
    combined = pd.concat([df for df in (deg1, deg2) if not df.empty], ignore_index=True) if (not deg1.empty or not deg2.empty) else pd.DataFrame()
    if not guard(df_has_rows(combined), "No tyre-life data available for this session."):
        return
    st.plotly_chart(charts.tyre_degradation_chart(combined, c["colors"]), use_container_width=True)
    st.caption(
        "⚠️ Lap-time trends across a stint reflect a mix of tyre wear, fuel burn-off, "
        "traffic, track evolution, and safety-car / VSC periods — this chart does not "
        "isolate tyre degradation as the sole cause of pace changes."
    )


@safe_section("Stint Analysis")
def render_stint_analysis(c: dict):
    st.title("📋 Stint Analysis")
    laps_by_driver = {c["driver1"]: c["laps_d1"], c["driver2"]: c["laps_d2"]}
    table = analysis.stint_table_multi(laps_by_driver)
    if not guard(df_has_rows(table), "No stint data available."):
        return

    driver_filter = st.selectbox("Filter by driver", options=["All"] + list(laps_by_driver.keys()))
    if driver_filter != "All":
        table = table[table["Driver"] == driver_filter]

    display = table.copy()
    display["AvgLapTime"] = display["AvgLapTimeSeconds"].apply(seconds_to_laptime_str)
    display["BestLapTime"] = display["BestLapTimeSeconds"].apply(seconds_to_laptime_str)
    display = display[[
        "Driver", "Stint", "Compound", "StartLap", "EndLap", "NumLaps",
        "AvgLapTime", "BestLapTime", "TyreLife",
    ]].rename(columns={"NumLaps": "Laps", "TyreLife": "Tyre Life (end)"})
    st.dataframe(display, use_container_width=True, hide_index=True)


@safe_section("Weather Analysis")
def render_weather(c: dict):
    st.title("🌦️ Weather Analysis")
    weather = c["weather"]
    if not guard(df_has_rows(weather), "No weather data available for this session."):
        return

    latest = weather.iloc[-1]
    cols = st.columns(4)
    cols[0].metric("Air Temp", f"{safe_round(safe_get(latest, 'AirTemp'), 1)} °C" if "AirTemp" in weather.columns else "N/A")
    cols[1].metric("Track Temp", f"{safe_round(safe_get(latest, 'TrackTemp'), 1)} °C" if "TrackTemp" in weather.columns else "N/A")
    cols[2].metric("Humidity", f"{safe_round(safe_get(latest, 'Humidity'), 1)}%" if "Humidity" in weather.columns else "N/A")
    rain_val = safe_get(latest, "Rainfall")
    cols[3].metric("Rainfall", "Yes" if rain_val else "No")

    st.plotly_chart(charts.weather_chart(weather), use_container_width=True)
    st.plotly_chart(charts.weather_extra_chart(weather), use_container_width=True)


@safe_section("Track Evolution")
def render_track_evolution(c: dict):
    st.title("📈 Track Evolution")
    evo = analysis.track_evolution_data(c["all_laps"])
    if not guard(df_has_rows(evo), "Not enough clean lap data to estimate track evolution."):
        return
    st.plotly_chart(charts.track_evolution_chart(evo), use_container_width=True)
    st.caption(
        "This trend combines track evolution (more rubber down, improving grip) with "
        "fuel load changes and traffic across the field — it is a session-wide pace "
        "proxy, not an isolated grip measurement."
    )


@safe_section("Telemetry")
def render_telemetry(c: dict):
    st.title("📡 Telemetry")
    driver = st.selectbox("Driver", options=[c["driver1"], c["driver2"]], key="telemetry_driver")
    color = c["color1"] if driver == c["driver1"] else c["color2"]

    with st.spinner(f"Loading telemetry for {driver}'s fastest lap..."):
        tel = data.get_driver_fastest_telemetry(c["session_obj"], driver)

    if not guard(df_has_rows(tel), f"No telemetry available for {driver}."):
        return

    channels = [ch for ch in ["Speed", "Throttle", "Brake", "nGear", "DRS"] if ch in tel.columns]
    tabs = st.tabs([f"{ch}" for ch in channels]) if channels else []
    for tab, ch in zip(tabs, channels):
        with tab:
            st.plotly_chart(charts.telemetry_channel_chart(tel, ch, driver, color), use_container_width=True)


@safe_section("Telemetry Comparison")
def render_telemetry_comparison(c: dict):
    st.title("🔀 Telemetry Comparison")
    d1, d2 = c["driver1"], c["driver2"]
    with st.spinner("Loading and aligning telemetry..."):
        tel1 = data.get_driver_fastest_telemetry(c["session_obj"], d1)
        tel2 = data.get_driver_fastest_telemetry(c["session_obj"], d2)
        aligned2 = analysis.align_telemetry_on_distance(tel1, tel2)

    if not guard(df_has_rows(tel1) and df_has_rows(tel2), "Telemetry not available for one or both drivers."):
        return

    channels = [ch for ch in ["Speed", "Throttle", "Brake", "nGear"] if ch in tel1.columns]
    tabs = st.tabs(channels) if channels else []
    for tab, ch in zip(tabs, channels):
        with tab:
            st.plotly_chart(
                charts.telemetry_comparison_chart(tel1, aligned2, ch, d1, d2, c["color1"], c["color2"]),
                use_container_width=True,
            )


@safe_section("Track Map")
def render_track_map(c: dict):
    st.title("🗺️ Track Map")
    d1, d2 = c["driver1"], c["driver2"]
    with st.spinner("Loading position telemetry..."):
        tel1 = data.get_driver_fastest_telemetry(c["session_obj"], d1)
        tel2 = data.get_driver_fastest_telemetry(c["session_obj"], d2)

    tel_by_driver = {d1: tel1, d2: tel2}
    st.plotly_chart(charts.track_map_chart(tel_by_driver, c["colors"]), use_container_width=True)


@safe_section("Session Summary")
def render_session_summary(c: dict):
    st.title("🧾 Session Summary")
    d1, d2 = c["driver1"], c["driver2"]
    summary = analysis.build_session_summary(c["laps_d1"], c["laps_d2"], d1, d2)
    s1, s2 = summary[d1], summary[d2]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(d1)
        st.metric("Fastest Lap", format_timedelta(s1["fastest_lap_time"]))
        st.metric("Average Lap", format_timedelta(s1["avg_lap_time"]))
        st.metric("Number of Laps", s1["num_laps_total"])
        st.metric("Number of Stints", s1["num_stints"])
        st.write("**Compounds used:**", ", ".join(sorted(set(s1["compounds"]))) if s1["compounds"] else "N/A")
        st.write("**Best Sectors:**", f"S1 {format_timedelta(s1['best_s1'])} · S2 {format_timedelta(s1['best_s2'])} · S3 {format_timedelta(s1['best_s3'])}")
    with col2:
        st.subheader(d2)
        st.metric("Fastest Lap", format_timedelta(s2["fastest_lap_time"]))
        st.metric("Average Lap", format_timedelta(s2["avg_lap_time"]))
        st.metric("Number of Laps", s2["num_laps_total"])
        st.metric("Number of Stints", s2["num_stints"])
        st.write("**Compounds used:**", ", ".join(sorted(set(s2["compounds"]))) if s2["compounds"] else "N/A")
        st.write("**Best Sectors:**", f"S1 {format_timedelta(s2['best_s1'])} · S2 {format_timedelta(s2['best_s2'])} · S3 {format_timedelta(s2['best_s3'])}")

    section_title("Head-to-Head")
    diff = summary["fastest_diff_seconds"]
    avg_diff = summary["avg_diff_seconds"]
    cols = st.columns(2)
    if diff is not None:
        faster = d1 if diff < 0 else d2
        cols[0].metric("Fastest Lap Difference", f"{abs(diff):.3f}s", delta=f"{faster} faster")
    else:
        cols[0].metric("Fastest Lap Difference", "N/A")
    if avg_diff is not None:
        faster_avg = d1 if avg_diff < 0 else d2
        cols[1].metric("Average Lap Difference", f"{abs(avg_diff):.3f}s", delta=f"{faster_avg} faster")
    else:
        cols[1].metric("Average Lap Difference", "N/A")


# ==========================================================================
# Main
# ==========================================================================
RENDERERS = {
    "Dashboard": render_dashboard,
    "Driver Comparison": render_driver_comparison,
    "Lap Analysis": render_lap_analysis,
    "Tyre Strategy": render_tyre_strategy,
    "Tyre Degradation": render_tyre_degradation,
    "Stint Analysis": render_stint_analysis,
    "Weather": render_weather,
    "Track Evolution": render_track_evolution,
    "Telemetry": render_telemetry,
    "Telemetry Comparison": render_telemetry_comparison,
    "Track Map": render_track_map,
    "Session Summary": render_session_summary,
}


def main():
    ctx = render_sidebar()
    if ctx is None:
        st.title(f"{APP_ICON} F1 Race Data Dashboard")
        st.info("Select a season and Grand Prix in the sidebar to begin.")
        return

    full_context = get_context(ctx)
    renderer = RENDERERS.get(ctx["nav"], render_dashboard)
    renderer(full_context)


if __name__ == "__main__":
    main()
