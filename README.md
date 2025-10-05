# 🌦️ WeatherScope — Your NASA-Powered Weather Risk Dashboard

A sleek, interactive web application providing **data-driven probabilities of extreme weather events** (heat, rain, wind, etc.) for any location and time — powered by **NASA Earth Observation Datasets**.

---

## 🌐 Live Application

- **[Live Application]:** [weatherscope-production.up.railway.app](https://weatherscope-frontend-production.up.railway.app)  

- **[Video Demo]:** 

![Demo Video (1)](https://github.com/user-attachments/assets/5acb329a-eca5-4001-832c-c49bf61c98aa)

---

## 🎯 Problem We’re Solving

Planning an outdoor activity — a hike, event, or picnic — is often uncertain due to unpredictable weather.  
While most weather apps forecast only a few days ahead, **WeatherScope** analyzes **multi-decade NASA climate records** to compute how likely “very hot,” “very cold,” “very wet,” “very windy,” or “very uncomfortable” conditions are for any place and date of the year.

This empowers users to plan trips or events with **data-driven climate insight**, not just short-term forecasts.

---

## 🛰️ Data Sources & Methodology

WeatherScope integrates public **NASA Earth Observation Data Systems** for long-term historical weather patterns:

| NASA Source | Purpose / Use | Access Protocol |
|--------------|----------------|----------------|
| **GES DISC / OPeNDAP (Hyrax)** | Provides long-term daily and monthly datasets for temperature, precipitation, windspeed, and humidity. | OPeNDAP endpoints used for subsetting by coordinates and time period. |
| **Giovanni** | For spatially averaged and climatological statistics over user-selected regions. | Accessed programmatically to compute time-series and climatology statistics. |
| **NASA Earthdata Search** | Enables retrieval of metadata, dataset identifiers, and global product access. | Used for linking datasets, metadata, and variable definitions. |

The backend processes these datasets to:
- Retrieve multi-year observations for a selected lat/lon and date.
- Calculate the probability that chosen variables exceed defined thresholds.
- Return summarized results and historical distributions for visualization.
- Provide metadata (units, dataset source, retrieval timestamp) with each result.

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
- **FastAPI (Python)** for asynchronous, high-performance API services
- **NASA OPeNDAP / Giovanni / Earthdata APIs** for dataset access
- **Asyncio** for concurrent multi-variable data processing
- **Pandas / NumPy** for climatological analysis

### Infrastructure
- **Docker & Docker Compose** for containerization  
- **Railway** for cloud deployment and orchestration  
- **Nginx** for reverse proxy and static file serving  
- **Multi-Stage Builds** for optimized production images

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

Each file includes:
- Dataset and variable names  
- Units (°C, mm, m/s, etc.)  
- Retrieval timestamp  
- Geographic and temporal context  

---

## 📊 Example Insight

> “For **Rishikesh, India** on **March 15**, NASA data shows:  
> 🌡️ Probability of temperature > 35 °C: **38 %**  
> 🌧️ Probability of rainfall > 20 mm: **15 %**  
> 🌬️ Probability of windspeed > 20 km/h: **22 %**  
> — Based on 20+ years of historical records.”

---

## 🌐 NASA Data References

- [GES DISC OPeNDAP Server (Hyrax)](https://disc.gsfc.nasa.gov/services/opendap/)  
- [NASA Giovanni Visualization Tool](https://giovanni.gsfc.nasa.gov/)  
- [NASA Earthdata Search Portal](https://search.earthdata.nasa.gov/)  
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
