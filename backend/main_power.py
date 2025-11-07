"""
Will It Rain on My Parade? - Backend API (NASA POWER Version)
FastAPI application for weather probability calculations using NASA POWER API
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional, List
import logging
import asyncio
import httpx
from dataclasses import dataclass
import numpy as np

# ----------------------------------------------------------------------------
# Logging Configuration
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# FastAPI App Initialization
# ----------------------------------------------------------------------------
app = FastAPI(
    title="Will It Rain on My Parade? (NASA POWER API)",
    description="Weather probability calculator API using NASA POWER Dataset",
    version="3.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://weatherscope.up.railway.app",
        "https://weatherscope-frontend-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------
# Dataclass: WeatherData
# ----------------------------------------------------------------------------
@dataclass
class WeatherData:
    date: str
    temp_max: float
    temp_min: float
    precip: float
    windspeed: float

# ----------------------------------------------------------------------------
# NASA POWER API Service
# ----------------------------------------------------------------------------
class NASAPowerService:
    """
    Service class to fetch and process NASA POWER API weather data.
    Entirely cloud-based (no downloads required).
    """

    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    def __init__(self):
        logger.info("NASA POWER API service initialized (no authentication needed).")

    async def fetch_historical_data(
        self, lat: float, lon: float, month: int, day: int, years_back: int = 10
    ) -> List[WeatherData]:
        """
        Fetch historical data for a given date (month/day) for the past N years.
        """
        current_year = datetime.now().year
        weather_data = []

        for year in range(current_year - years_back, current_year):
            try:
                daily = await self._fetch_single_day(lat, lon, year, month, day)
                if daily:
                    weather_data.append(daily)
            except Exception as e:
                logger.error(f"Error fetching data for {year}-{month}-{day}: {e}")
                continue

        return weather_data

    async def _fetch_single_day(
        self, lat: float, lon: float, year: int, month: int, day: int
    ) -> Optional[WeatherData]:
        """
        Fetch single-day weather data from NASA POWER API.
        Parameters used:
          - PRECTOTCORR (Precipitation, mm/day)
          - T2M_MAX (Max temperature, °C)
          - T2M_MIN (Min temperature, °C)
          - WS10M (Wind speed, m/s)
        """
        date = datetime(year, month, day)
        start = date.strftime("%Y%m%d")
        end = start

        params = {
            "parameters": "PRECTOTCORR,T2M_MAX,T2M_MIN,WS10M",
            "community": "RE",  # Renewable Energy community
            "longitude": lon,
            "latitude": lat,
            "start": start,
            "end": end,
            "format": "JSON"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()

            params_data = data["properties"]["parameter"]
            precip = float(list(params_data["PRECTOTCORR"].values())[0])
            tmax = float(list(params_data["T2M_MAX"].values())[0])
            tmin = float(list(params_data["T2M_MIN"].values())[0])
            wind = float(list(params_data["WS10M"].values())[0])

            return WeatherData(
                date=date.strftime("%Y-%m-%d"),
                temp_max=tmax,
                temp_min=tmin,
                precip=precip,
                windspeed=wind
            )

        except Exception as e:
            logger.error(f"POWER API fetch failed for {year}-{month}-{day}: {e}")
            return None

# ----------------------------------------------------------------------------
# Helper Functions
# ----------------------------------------------------------------------------
def calculate_probability(data: List[WeatherData], condition_func) -> float:
    """Calculate the probability based on a condition."""
    if not data:
        return 0.0
    matching_count = sum(1 for item in data if condition_func(item))
    return matching_count / len(data)

# ----------------------------------------------------------------------------
# Initialize the NASA POWER Service
# ----------------------------------------------------------------------------
weather_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize the NASA POWER weather service"""
    global weather_service
    try:
        weather_service = NASAPowerService()
        logger.info("NASA POWER Weather Service initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize NASA POWER Service: {e}")
        weather_service = None

# ----------------------------------------------------------------------------
# API Endpoints
# ----------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "Will It Rain on My Parade? API (NASA POWER)", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# -------------------- RAIN PROBABILITY --------------------
@app.get("/probability/rain")
async def get_rain_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1–12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1–31)"),
    threshold: float = Query(0.1, ge=0, description="Rain threshold (mm/day)")
):
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service unavailable.")
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(data, lambda x: x.precip > threshold)
        return {
            "probability": round(probability, 3),
            "source": "NASA POWER (PRECTOTCORR)",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Rain probability error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# -------------------- HEAT PROBABILITY --------------------
@app.get("/probability/heat")
async def get_heat_probability(
    lat: float,
    lon: float,
    month: int,
    day: int,
    threshold: float = Query(35.0, description="Heat threshold (°C)")
):
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service unavailable.")
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(data, lambda x: x.temp_max > threshold)
        return {
            "probability": round(probability, 3),
            "source": "NASA POWER (T2M_MAX)",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Heat probability error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# -------------------- COLD PROBABILITY --------------------
@app.get("/probability/cold")
async def get_cold_probability(
    lat: float,
    lon: float,
    month: int,
    day: int,
    threshold: float = Query(5.0, description="Cold threshold (°C)")
):
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service unavailable.")
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(data, lambda x: x.temp_min < threshold)
        return {
            "probability": round(probability, 3),
            "source": "NASA POWER (T2M_MIN)",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Cold probability error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# -------------------- WIND PROBABILITY --------------------
@app.get("/probability/wind")
async def get_wind_probability(
    lat: float,
    lon: float,
    month: int,
    day: int,
    threshold: float = Query(15.0, description="Wind threshold (m/s)")
):
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service unavailable.")
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(data, lambda x: x.windspeed > threshold)
        return {
            "probability": round(probability, 3),
            "source": "NASA POWER (WS10M)",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Wind probability error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# -------------------- ALL PROBABILITIES --------------------
@app.get("/probability/all")
async def get_all_probabilities(
    lat: float,
    lon: float,
    month: int,
    day: int,
    rain_threshold: float = 0.1,
    heat_threshold: float = 35.0,
    cold_threshold: float = 5.0,
    wind_threshold: float = 15.0
):
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service unavailable.")
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        rain_prob = calculate_probability(data, lambda x: x.precip > rain_threshold)
        heat_prob = calculate_probability(data, lambda x: x.temp_max > heat_threshold)
        cold_prob = calculate_probability(data, lambda x: x.temp_min < cold_threshold)
        wind_prob = calculate_probability(data, lambda x: x.windspeed > wind_threshold)

        return {
            "rain": {"probability": round(rain_prob, 3), "threshold": rain_threshold},
            "heat": {"probability": round(heat_prob, 3), "threshold": heat_threshold},
            "cold": {"probability": round(cold_prob, 3), "threshold": cold_threshold},
            "wind": {"probability": round(wind_prob, 3), "threshold": wind_threshold},
            "source": "NASA POWER API (PRECTOTCORR, T2M_MAX, T2M_MIN, WS10M)",
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "historical_data": [
                {
                    "date": item.date,
                    "temp_max": item.temp_max,
                    "temp_min": item.temp_min,
                    "precip": item.precip,
                    "windspeed": item.windspeed,
                }
                for item in data
            ],
        }
    except Exception as e:
        logger.error(f"All probability error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ----------------------------------------------------------------------------
# Run Server
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
