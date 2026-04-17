# 🌦️ WeatherScope — Your NASA-Powered Weather Risk Dashboard

A sleek, interactive web application providing **data-driven probabilities of extreme weather events** (heat, rain, wind, etc.) for any location and time — powered by **NASA Earth Observation Datasets**.

---

## 🌐 Live Application

- **[Live Application]:** [weatherscope-production.up.railway.app](https://weatherscope-frontend-production.up.railway.app)  

- **[Video Demo]:** 

![Demo Video (1)](https://github.com/user-attachments/assets/5acb329a-eca5-4001-832c-c49bf61c98aa)

---

## 🎯 Problem We’re Solving

Planning outdoor activities like hikes, picnics, or events can be tricky when weather is unpredictable.
Most weather apps only look a few days ahead — but **WeatherScope** goes further by analyzing **decades of NASA climate data** to show you the probability of extreme conditions like intense heat, heavy rain, strong winds, or uncomfortable humidity for any location and time of year.

Whether you're planning a weekend trip or a large outdoor event, WeatherScope gives you **climate-backed insights** to make smarter, more confident decisions — not just guesses.

---


## 🛰️ Data Sources & Methodology

WeatherScope integrates **real NASA climate datasets**:

| NASA Source | Variable / Use | Access Method |
|--------------|----------------|----------------|
| **MERRA-2** (Modern-Era Retrospective Analysis) | Air temperature, windspeed, humidity, surface fluxes | GES DISC / OPeNDAP |
| **IMERG / GPM** (Global Precipitation Measurement) | High-resolution rainfall detection, extreme precipitation | GES DISC / OPeNDAP |
| **NASA POWER** | Temperature, precipitation, windspeed — used for fast fallback | POWER REST API (JSON) |
| **GES DISC Hyrax OPeNDAP** | Climate variable subsetting by coordinate and date | OPeNDAP endpoints |
| **Giovanni** | Time series & climatology statistics | Programmatic queries |
| **Earthdata Search** | Dataset metadata, product discovery | Earthdata APIs |

The backend processes these datasets to:
✔ Retrieve multi-year observations for a selected lat/lon and date.
✔ Calculate the probability that chosen variables exceed defined thresholds.
✔ Return summarized results and historical distributions for visualization.
✔ Provide metadata (units, dataset source, retrieval timestamp) with each result.
✔ Checks extreme thresholds:
- Heat > 35°C  
- Cold < 5°C  
- Rain > 0.1mm (or custom)  
- Wind > 15 m/s  

✔ Computes:
- % probability  
- number of years analyzed  
- raw yearly values  
✔ Returns JSON results with source metadata  
✔ If high-res dataset fails → **POWER fallback**

Everything is derived from **NASA’s long-term datasets**, not short-range forecasts.


All calculations are **derived from NASA’s public climatological archives** rather than short-term weather APIs.

---

## 🌟 Key Features

- **🗺️ Interactive 3D Globe Interface** — Click anywhere on Earth to analyze local NASA climate records.
- **📊 Probability Dashboard** — Get precise probabilities of extreme heat, rainfall, cold, or wind.
- **📈 Data Visualizations** — Bell curves, radar charts, and time-series trends for clarity.
- **🎛️ Custom Thresholds** — Define what “extreme” means to you (e.g., >35 °C, >20 mm rainfall).
- **💾 Export Results** — Download CSV or JSON data with metadata and NASA dataset links.
- **🌗 Modern UI** — Glassmorphism design, light/dark modes, and responsive layout.

---

## 🧠 Tech Stack

### Frontend
- **React 18** + **TypeScript**
- **Tailwind CSS** for modern responsive design
- **Three.js / React-Three-Fiber** for the interactive 3D globe
- **D3.js / Custom SVG Charts** for probability and trend visualization
- **Framer Motion** for smooth UI animations

### Backend
- **FastAPI (Python)** for asynchronous, high-performance API services + **Uvicorn**
- **NASA OPeNDAP / Giovanni / Earthdata APIs** for dataset access
- **Asyncio** for concurrent multi-variable data processing
- **Pandas / NumPy** for climatological analysis
- **CORS** enabled for frontend
- **POWER** fallback for reliability

### Infrastructure
- **Docker & Docker Compose** for containerization  
- **Railway** for cloud deployment and orchestration  
- **Nginx** for reverse proxy and static file serving  
- **Multi-Stage Builds** for optimized production images
- **`.env`** based config

---

## 🖥️ User Experience

- 🌍 Click anywhere on the 3D globe to choose a location.  
- 📅 Select a date or time range to analyze.  
- 🔍 View real-time calculated probabilities for heat, rainfall, wind, and cold.  
- 📈 Explore graphical insights into historical climate patterns.  
- 💾 Download data as CSV or JSON for further analysis.  

The design focuses on simplicity, interactivity, and clarity, helping users quickly understand weather likelihoods for any location and season.

---

## 📂 Output & Data Export

Users can download:
- **CSV** — Structured tabular data for selected variables.
- **JSON** — Nested data with distributions, metadata, and NASA source information.

Each export includes:
| Field | Description |
|-------|-------------|
| Dataset Source | POWER / MERRA-2 / IMERG |
| Units | (°C, mm/day, m/s) |
| Years Used | e.g., 2001-2024 |
| Probability (%) | of extreme condition |
| Historical Values | per year on that date |
| Lat/Lon | analyzed point |
| Timestamp | retrieval time |


---

## 📊 Example Insight

> “For **Washington, District of Columbia, United States** on **March 15**, NASA data shows:  
> 🌡️ Probability of temperature < 5 °C: **70%**  
> 🌧️ Probability of rainfall > 0.9 mm: **30%**  
> 🌬️ Probability of windspeed > 9 m/s: **20%**  
> — Based on 20+ years of historical records.”

---

## 🌐 NASA Data References

- [GES DISC OPeNDAP Server (Hyrax)](https://disc.gsfc.nasa.gov/services/opendap/)  
- [NASA POWER API Service](https://power.larc.nasa.gov/)  
- [NASA GES DISC MERRA-2](https://disc.gsfc.nasa.gov/datasets?keywords=MERRA-2)  
- [NASA Giovanni Visualization Tool](https://giovanni.gsfc.nasa.gov/)  
- [NASA Earthdata Search Portal](https://search.earthdata.nasa.gov/)  
- [NASA IMERG Retrievals for GPM](https://gpm.nasa.gov/data/imerg)  
- [NASA Data Access Tutorials](https://disc.gsfc.nasa.gov/information/howto)

---

## 🧑‍💻 Team — *Cloud Commanders*

*"Navigating the skies of innovation, one cloud at a time ☁️⚡"*  
Crafted with dedication and precision © 2025  

---

## 🚀 Deployment

Deployed seamlessly via **Railway** with containerized architecture, automatic scaling, and continuous delivery.

🔗 **Deployment URL:** [https://weatherscope-production.up.railway.app](https://weatherscope-frontend-production.up.railway.app)  

---

## 📜 License

This project uses publicly available NASA Earth observation data.  
NASA does not endorse or guarantee this application.  
Data and images © NASA / GES DISC / Giovanni / Earthdata (used under public access policy).

---
