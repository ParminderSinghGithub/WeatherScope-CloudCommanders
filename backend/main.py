"""
Will It Rain on My Parade? - Backend API
FastAPI application for weather probability calculations
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Will It Rain on My Parade?",
    description="Weather probability calculator API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
VC_API_KEY = os.getenv("VC_API_KEY")
if not VC_API_KEY:
    logger.warning("VC_API_KEY environment variable not set")

BASE_URL = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"

@dataclass
class WeatherData:
    date: str
    temp_max: float
    temp_min: float
    precip: float
    windspeed: float

class WeatherService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_historical_data(
        self, 
        lat: float, 
        lon: float, 
        month: int, 
        day: int, 
        years_back: int = 10
    ) -> List[WeatherData]:
        """Fetch historical weather data for specific date across multiple years"""
        weather_data = []
        current_year = datetime.now().year
        
        # Create tasks for concurrent API calls
        tasks = []
        for year in range(current_year - years_back, current_year):
            date_str = f"{year}-{month:02d}-{day:02d}"
            task = self._fetch_single_day(lat, lon, date_str)
            tasks.append(task)
        
        # Execute all requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error fetching data: {result}")
                continue
            if result:
                weather_data.append(result)
        
        return weather_data
    
    async def _fetch_single_day(
        self, 
        lat: float, 
        lon: float, 
        date: str
    ) -> Optional[WeatherData]:
        """Fetch weather data for a single day"""
        url = f"{BASE_URL}/{lat},{lon}/{date}"
        params = {
            "key": self.api_key,
            "elements": "datetime,tempmax,tempmin,precip,windspeed",
            "include": "days",
            "unitGroup": "metric"
        }
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "days" in data and len(data["days"]) > 0:
                day_data = data["days"][0]
                return WeatherData(
                    date=day_data.get("datetime", date),
                    temp_max=float(day_data.get("tempmax", 0)),
                    temp_min=float(day_data.get("tempmin", 0)),
                    precip=float(day_data.get("precip", 0) or 0),
                    windspeed=float(day_data.get("windspeed", 0) or 0)
                )
        except Exception as e:
            logger.error(f"Error fetching data for {date}: {e}")
            return None
    
    async def close(self):
        await self.client.aclose()

# Global weather service instance
weather_service = None

@app.on_event("startup")
async def startup_event():
    global weather_service
    if VC_API_KEY:
        weather_service = WeatherService(VC_API_KEY)
    else:
        logger.warning("Weather service not initialized - missing API key")

@app.on_event("shutdown")
async def shutdown_event():
    if weather_service:
        await weather_service.close()

def calculate_probability(data: List[WeatherData], condition_func) -> float:
    """Calculate probability based on condition function"""
    if not data:
        return 0.0
    
    matching_count = sum(1 for item in data if condition_func(item))
    return matching_count / len(data)

@app.get("/")
async def root():
    return {"message": "Will It Rain on My Parade? API", "status": "healthy"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/probability/rain")
async def get_rain_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(0.1, ge=0, description="Rain threshold in mm")
):
    """Calculate probability of rain for given location and date"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")
    
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(
            data, 
            lambda x: x.precip > threshold
        )
        
        return {
            "probability": round(probability, 3),
            "source": "VisualCrossing",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Error calculating rain probability: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/probability/heat")
async def get_heat_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(35.0, description="Heat threshold in Celsius")
):
    """Calculate probability of very hot weather"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")
    
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(
            data, 
            lambda x: x.temp_max > threshold
        )
        
        return {
            "probability": round(probability, 3),
            "source": "VisualCrossing",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Error calculating heat probability: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/probability/cold")
async def get_cold_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(5.0, description="Cold threshold in Celsius")
):
    """Calculate probability of very cold weather"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")
    
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(
            data, 
            lambda x: x.temp_min < threshold
        )
        
        return {
            "probability": round(probability, 3),
            "source": "VisualCrossing",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Error calculating cold probability: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/probability/wind")
async def get_wind_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(15.0, description="Wind threshold in m/s")
):
    """Calculate probability of very windy weather"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")
    
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        probability = calculate_probability(
            data, 
            lambda x: x.windspeed > threshold
        )
        
        return {
            "probability": round(probability, 3),
            "source": "VisualCrossing",
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day}
        }
    except Exception as e:
        logger.error(f"Error calculating wind probability: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/probability/all")
async def get_all_probabilities(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    rain_threshold: float = Query(0.1, ge=0, description="Rain threshold in mm"),
    heat_threshold: float = Query(35.0, description="Heat threshold in Celsius"),
    cold_threshold: float = Query(5.0, description="Cold threshold in Celsius"),
    wind_threshold: float = Query(15.0, description="Wind threshold in m/s")
):
    """Calculate all weather probabilities at once"""
    if not weather_service:
        raise HTTPException(status_code=503, detail="Weather service not available")
    
    try:
        data = await weather_service.fetch_historical_data(lat, lon, month, day)
        
        rain_prob = calculate_probability(data, lambda x: x.precip > rain_threshold)
        heat_prob = calculate_probability(data, lambda x: x.temp_max > heat_threshold)
        cold_prob = calculate_probability(data, lambda x: x.temp_min < cold_threshold)
        wind_prob = calculate_probability(data, lambda x: x.windspeed > wind_threshold)
        
        return {
            "rain": {
                "probability": round(rain_prob, 3),
                "threshold": rain_threshold
            },
            "heat": {
                "probability": round(heat_prob, 3),
                "threshold": heat_threshold
            },
            "cold": {
                "probability": round(cold_prob, 3),
                "threshold": cold_threshold
            },
            "wind": {
                "probability": round(wind_prob, 3),
                "threshold": wind_threshold
            },
            "source": "VisualCrossing",
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "historical_data": [
                {
                    "date": item.date,
                    "temp_max": item.temp_max,
                    "temp_min": item.temp_min,
                    "precip": item.precip,
                    "windspeed": item.windspeed
                } for item in data
            ]
        }
    except Exception as e:
        logger.error(f"Error calculating all probabilities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
