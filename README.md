# 🏎️ F1 Race Data Dashboard

### 🏁 Explore. Compare. Analyze. Understand Formula 1.

An interactive **Formula 1 analytics platform** built with **Streamlit, FastF1, Pandas, NumPy, and Plotly**.

Turn real F1 timing data into beautiful, interactive visualizations — from **lap-time battles and tyre degradation** to **telemetry, weather, track evolution, and driver comparisons**.

> **Select a season → choose a Grand Prix → select a session → compare drivers → explore the data.**

---

## ✨ Why This Project?

Formula 1 generates an enormous amount of data every race weekend.

This project transforms that raw timing and telemetry data into an **easy-to-use analytics dashboard** designed for anyone who wants to understand what happened on track.

Instead of looking at thousands of raw data points, you can answer questions like:

* 🏎️ Who was faster?
* ⏱️ Where did a driver gain or lose time?
* 🛞 How did the tyres degrade?
* 🌡️ How did weather conditions change?
* 📈 Did the track become faster throughout the session?
* 📡 What did the car telemetry look like?
* 🗺️ Where on the circuit did drivers differ?
* 🏁 Which driver had the stronger overall session?

---

# 🚀 Features

## 📊 Interactive Dashboard

A high-level overview of the selected session with key performance metrics.

**Includes:**

* Grand Prix & circuit information
* Session date
* Number of drivers
* Number of laps
* Fastest lap
* Track temperature
* Air temperature
* Session statistics

---

## 🥊 Driver vs Driver

Put two drivers head-to-head and discover who had the advantage.

**Compare:**

* Fastest lap
* Average lap
* Lap-time delta
* Sector performance
* Valid-lap count
* Tyre compounds
* Stint performance

### Example questions

> Was Verstappen faster overall?

> Which sector gave Leclerc the advantage?

> How large was the average lap-time difference?

---

## ⏱️ Lap Time Analysis

Visualize lap-by-lap performance across the session.

**Features:**

* Multi-driver lap-time comparison
* Fastest-lap highlighting
* Average pace lines
* Lap-by-lap performance
* Invalid/deleted lap handling
* Pit-lap filtering
* Safety-car awareness

The analysis automatically handles missing and incomplete timing data.

---

## 🛞 Tyre Strategy

Understand how teams managed their tyres throughout the session.

Visualize:

* Compound used
* Stint number
* Stint duration
* Start lap
* End lap
* Tyre life
* Fresh vs used tyres

This makes it easy to see the strategic story of a race.

---

## 📉 Tyre Degradation

Analyze how lap pace changes as tyres age.

Visualizations show:

**Lap Time ↔ Tyre Life**

broken down by:

* Driver
* Stint
* Compound

> ⚠️ Tyre degradation is not treated as a single causal measurement. Fuel burn-off, traffic, track evolution, safety cars, and driver behaviour can all influence lap time.

---

## 🧩 Stint Analysis

A detailed table containing every tyre stint.

| Driver | Stint | Compound | Laps | Best Pace | Avg Pace | Tyre Life |
| ------ | ----: | -------- | ---: | --------: | -------: | --------: |
| VER    |     1 | MEDIUM   |   20 |         — |        — |         — |
| LEC    |     1 | HARD     |   32 |         — |        — |         — |

Filter and investigate individual stints to understand race strategy and tyre management.

---

## 🌦️ Weather Analysis

Explore session conditions through interactive charts.

Track:

* 🌡️ Air temperature
* 🛣️ Track temperature
* 💧 Humidity
* 🎈 Pressure
* 💨 Wind speed
* 🌧️ Rainfall

Useful for understanding how changing conditions may have influenced performance.

---

## 📈 Track Evolution

Track how overall session pace changes over time.

The dashboard calculates:

> **Median lap time per lap number + rolling average**

This provides a simple view of whether the track was generally getting faster or slower.

It is intentionally presented as a **pace proxy**, rather than a direct measurement of track grip.

---

# 📡 Telemetry Analysis

Dive deeper into the car's performance.

Analyze:

* 🚀 Speed
* 🦶 Throttle
* 🛑 Brake
* ⚙️ Gear
* 📶 DRS
* 📏 Distance

All telemetry is plotted against circuit distance, allowing detailed analysis of how drivers attack the track.

---

# 🆚 Telemetry Comparison

Compare two drivers on the same distance axis.

The dashboard aligns telemetry using interpolation so that both drivers can be compared across:

**Speed → Throttle → Brake → Gear → DRS**

This makes it possible to identify exactly where one driver gains or loses performance.

---

# 🗺️ Interactive Track Map

Generate the circuit layout directly from car-position telemetry.

Explore:

* Driver racing lines
* Circuit shape
* Position data
* Driver-specific traces

No manually drawn circuit maps are required.

---

# 🏁 Session Summary

A complete head-to-head performance recap.

Includes:

### Driver 1

* Fastest lap
* Average lap
* Best sectors
* Compounds
* Stints

### Driver 2

* Fastest lap
* Average lap
* Best sectors
* Compounds
* Stints

### Final comparison

* Lap-time delta
* Sector advantage
* Pace difference
* Strategy comparison

---

# 🧠 Built to Handle Real-World F1 Data

Real motorsport data isn't always perfect.

Sessions can contain:

* Missing telemetry
* Deleted laps
* Invalid laps
* Pit laps
* Red flags
* Safety-car periods
* Missing weather data
* Partial sessions
* Network/API failures

The application is designed to **fail gracefully**.

Instead of crashing the dashboard, individual sections display appropriate warnings when data isn't available.

---

# 🏗️ Architecture

```text
                    ┌─────────────────────┐
                    │      Streamlit      │
                    │       app.py        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Analysis       │
                    │    analysis.py      │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       FastF1        │
                    │      data.py        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   F1 Timing Data    │
                    │   Telemetry/Weather │
                    └─────────────────────┘

             ┌─────────────────────────────┐
             │          charts.py         │
             │      Plotly Visualizations │
             └─────────────────────────────┘
```

### Project Structure

```text
F1-RACE-DATA-DASHBOARD/
│
├── app.py
├── data.py
├── analysis.py
├── charts.py
├── config.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── utils/
│   ├── __init__.py
│   └── helpers.py
│
└── data/
    └── cache/
```

### Separation of Responsibilities

| File          | Responsibility                  |
| ------------- | ------------------------------- |
| `app.py`      | Streamlit UI & navigation       |
| `data.py`     | FastF1 data retrieval & caching |
| `analysis.py` | Data processing & calculations  |
| `charts.py`   | Plotly visualizations           |
| `config.py`   | Application configuration       |
| `helpers.py`  | Formatting & error handling     |

The architecture keeps **data retrieval, analysis, visualization, and UI logic separated**, making the project easier to test and extend.

---

# 🛠️ Technology Stack

| Technology   | Purpose                      |
| ------------ | ---------------------------- |
| 🐍 Python    | Core programming language    |
| 🎨 Streamlit | Interactive web dashboard    |
| 🏎️ FastF1   | Formula 1 timing & telemetry |
| 🐼 Pandas    | Data manipulation            |
| 🔢 NumPy     | Numerical analysis           |
| 📊 Plotly    | Interactive visualizations   |

---

# ⚡ Getting Started

## 1️⃣ Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/F1-RACE-DATA-DASHBOARD.git
cd F1-RACE-DATA-DASHBOARD
```

## 2️⃣ Create a virtual environment

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### macOS / Linux

```bash
source venv/bin/activate
```

---

## 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Launch the dashboard

```bash
streamlit run app.py
```

The application will open at:

```text
http://localhost:8501
```

---

# 💾 Data & Caching

The dashboard uses **FastF1** to retrieve Formula 1 timing, telemetry, weather, and session information.

The first time a session is loaded, FastF1 may need to download a significant amount of data.

Subsequent requests are faster because the data is stored in the local cache:

```text
data/cache/
```

The cache directory is excluded from Git using `.gitignore`.

---

# 🔬 Analysis Methodology

### Valid Lap Filtering

Lap calculations exclude:

* Missing lap times
* Deleted laps
* In-laps
* Out-laps
* Invalid timing records

Where available, timing-accuracy information is also considered.

### Driver Comparison

Driver lap deltas are calculated by matching drivers on common lap numbers.

```text
Driver A Lap N
       ↓
    Compare
       ↓
Driver B Lap N
       ↓
    Delta
```

### Tyre Stints

Stints are reconstructed from FastF1's recorded:

* `Stint`
* `Compound`
* `TyreLife`
* `FreshTyre`

No artificial stint boundaries are created.

### Telemetry Alignment

When comparing telemetry, the second driver's data is aligned to the first driver's distance grid using:

```python
numpy.interp()
```

This allows both drivers to share the same distance axis.

---

# 📌 Important Notes

This project is designed for **analytics and educational purposes**.

Lap time is affected by many factors:

```text
Tyres
  +
Fuel
  +
Traffic
  +
Track Evolution
  +
Weather
  +
Safety Cars
  +
Driver Performance
  +
Car Performance
  ↓
Observed Lap Time
```

Therefore, charts such as tyre degradation and track evolution should be interpreted as **performance indicators**, not isolated causal measurements.

---

# 🔮 Future Roadmap

### 🏎️ Race Analytics

* [ ] Race position charts
* [ ] Gap-to-leader analysis
* [ ] Position changes
* [ ] Pit-stop analysis
* [ ] Race pace comparison

### 📊 Advanced Performance

* [ ] 3+ driver comparison
* [ ] Ideal lap calculation
* [ ] Mini-sector analysis
* [ ] Speed-trap comparison
* [ ] Corner-by-corner analysis

### 📤 Export

* [ ] CSV exports
* [ ] PDF reports
* [ ] Downloadable charts
* [ ] Automated race reports

### 🎨 UX

* [ ] Light/Dark theme
* [ ] Driver presets
* [ ] Saved sessions
* [ ] Custom dashboard layouts

---

# 🎯 What This Project Demonstrates

This project combines several real-world engineering skills:

**Python Development**
→ Modular application architecture

**Data Engineering**
→ API data retrieval, caching, cleaning

**Data Analysis**
→ Statistical calculations and performance metrics

**Data Visualization**
→ Interactive Plotly dashboards

**Domain Analytics**
→ Motorsport, tyre strategy, telemetry

**Software Engineering**
→ Separation of concerns and error handling

**Product Thinking**
→ Turning complex raw data into an intuitive user experience

---

# 🏆 Project Highlights

> 🏎️ **Real F1 Data**
> Powered by FastF1 timing and telemetry data.

> 📊 **Interactive Analytics**
> Explore sessions dynamically instead of relying on static charts.

> 🧠 **Robust Data Processing**
> Designed to handle incomplete and imperfect motorsport data.

> ⚡ **Cached Performance**
> FastF1 caching reduces repeated download times.

> 🎨 **Modern Visualization**
> Interactive Plotly charts make complex performance data easier to understand.

> 🧩 **Modular Architecture**
> Data, analysis, visualization, and UI are separated into independent layers.

---

# 📸 Dashboard Preview

> Add screenshots/GIFs of your dashboard here.

Recommended screenshots:

```text
01 → Main Dashboard
02 → Driver Comparison
03 → Tyre Strategy
04 → Telemetry
05 → Track Map
06 → Weather Analysis
```

A short GIF showing **selecting a Grand Prix → choosing drivers → exploring charts** would make the repository even more impressive.

---

# 🌐 Data Source

Data is retrieved using the open-source **FastF1** Python package.

FastF1 provides access to Formula 1 timing, telemetry, weather, and session information.

---

# ⚖️ Disclaimer

This project is **not affiliated with Formula 1, FIA, or any Formula 1 team**.

Built for **portfolio, educational, analytical, and experimental purposes** using the open-source FastF1 ecosystem.

---

# 👨‍💻 Author

### **Vinay**

Computer Science & Engineering
Python • Data Analytics • AI/ML • Full-Stack Development

---

## ⭐ If you found this project interesting

Give the repository a ⭐ and feel free to explore, fork, or build upon it.

### 🏎️ Turn raw race data into racing insights.
