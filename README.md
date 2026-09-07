# 🏎️ F1 Race Data Dashboard

A production-quality, interactive Formula 1 analytics dashboard built with **Streamlit**, **FastF1**, **Pandas**, **NumPy**, and **Plotly**. Load any season/Grand Prix/session combination FastF1 supports and explore lap times, tyre strategy, degradation, weather, telemetry, and head-to-head driver comparisons — all from real timing data.

## Overview

This dashboard is a self-serve F1 data-analysis tool: pick a season, event and session in the sidebar, pick two drivers to compare, and every page updates from real FastF1 data. It's built to survive missing/partial data (common with older seasons, practice sessions, or sessions affected by red flags) without crashing.

## Features

- **Dashboard Overview** — event, circuit, date, driver/lap counts, fastest lap, track & air temperature as metric cards
- **Driver Comparison** — fastest/average lap, lap-time delta per lap, sector time comparison, valid-lap counts
- **Lap Time Analysis** — multi-driver lap-time chart with fastest-lap markers and average lines; robust to NaT/NaN, deleted laps, pit laps, and safety-car periods
- **Tyre Strategy** — horizontal stint visualization (compound, stint length, start/end lap) per driver
- **Tyre Degradation** — lap time vs. tyre life scatter/line charts by stint and compound, with explicit caveats about fuel load, traffic, and track evolution
- **Stint Analysis** — filterable table of every stint: compound, laps, average/best pace, tyre life
- **Weather Analysis** — air/track temperature, humidity, pressure, wind speed, rainfall over the session
- **Track Evolution** — session-wide median pace trend with rolling average, kept distinct from tyre/fuel effects
- **Telemetry** — Speed / Throttle / Brake / Gear / DRS vs. distance for the fastest lap of a selected driver
- **Telemetry Comparison** — Driver 1 vs Driver 2 telemetry aligned on distance
- **Track Map** — circuit map traced from position telemetry, per driver
- **Session Summary** — head-to-head recap: fastest/average lap, best sectors, compounds, stints, and the deltas between two drivers

## Architecture

```
F1 RACE DATA DASHBOARD/
│
├── app.py            # Streamlit UI: sidebar, navigation, page renderers
├── data.py            # FastF1 access layer (cache setup, session/lap/telemetry/weather loading)
├── analysis.py         # Pandas/NumPy computation layer (stats, stints, deltas, degradation)
├── charts.py           # Plotly figure builders (UI-agnostic, takes clean data in)
├── config.py           # Page config, theme/CSS, constants, defaults
├── requirements.txt
├── README.md
├── .gitignore
│
├── utils/
│   ├── __init__.py
│   └── helpers.py       # Formatting, safe-access and error-containment helpers
│
└── data/
    └── cache/           # FastF1 disk cache (git-ignored, created automatically)
```

Each layer only depends on the layer(s) below it: `charts.py` and `analysis.py` never import Streamlit, and `data.py` never builds figures. This keeps the FastF1 integration, the analysis, and the UI independently testable and easy to extend.

## Tech Stack

| Layer | Technology |
|---|---|
| UI framework | Streamlit |
| F1 data source | [FastF1](https://docs.fastf1.dev/) |
| Data wrangling | Pandas, NumPy |
| Visualization | Plotly (graph_objects) |
| Language | Python 3.10+ |

## Installation

```bash
pip install -r requirements.txt
```

## Running Instructions

```bash
streamlit run app.py
```

The app opens in your browser (default `http://localhost:8501`). On first load it defaults to **2024 Monaco Grand Prix — Race — LEC vs VER** (falling back gracefully if that data isn't available). Use the sidebar to change season, Grand Prix, session, and the two drivers being compared, then click **Load Session**.

> First load of any session downloads data via the FastF1 API and can take a while depending on session type (telemetry-heavy sessions like Race take longer than Qualifying). Subsequent loads of the same session are served from FastF1's local disk cache (`data/cache/`) and from Streamlit's in-memory cache.

## Data Source

All data is retrieved live from the **FastF1** Python package, which sources official F1 timing data (lap times, sectors, tyre stints, car telemetry, weather) from the F1 live timing feed and the Ergast API for historical schedule metadata. No data in this dashboard is hardcoded, mocked, or fabricated — every chart and metric is computed directly from what FastF1 returns for the selected session.

## Analysis Methodology

- **Valid laps** exclude laps with no recorded lap time, deleted laps, and in/out (pit) laps; where FastF1 flags a lap as timing-accurate, only accurate laps are used for averages and fastest-lap calculations.
- **Lap-time delta** charts compare two drivers only on laps both completed (inner join on lap number).
- **Tyre stints** are reconstructed directly from FastF1's `Stint`/`Compound`/`TyreLife`/`FreshTyre` lap columns — no stint boundaries are inferred or guessed.
- **Tyre degradation** views intentionally avoid claiming causation: pace changes across a stint can come from tyre wear, fuel burn-off, traffic, track evolution, or safety-car/VSC periods, and the dashboard says so next to the chart.
- **Track evolution** is approximated as the session-wide median lap time per lap number with a rolling average — a pace proxy, not an isolated grip measurement.
- **Telemetry comparison** aligns the second driver's channels onto the first driver's distance grid via linear interpolation (`numpy.interp`) so both cars can be plotted on a shared X-axis.

## Error Handling

Every section is wrapped so that a data gap in one chart (missing telemetry, no weather data for older seasons, an unsupported session, etc.) shows a clear warning/info message in that section instead of crashing the whole app. FastF1/network failures during session loading are caught and reported in the sidebar without stopping you from picking a different session.

## Future Improvements

- Multi-driver (3+) comparison mode across all sections
- Race-position and gap-to-leader charts using timing data
- Qualifying-specific ideal-lap and mini-sector analysis
- Downloadable PDF/CSV exports of tables and charts
- Persistent user session presets (favorite driver pairs, default season)
- Optional light theme toggle

---

*Not affiliated with Formula 1, the FIA, or any F1 team. Built for portfolio/educational use with the open-source FastF1 package.*
