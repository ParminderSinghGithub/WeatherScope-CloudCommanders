"""
Will It Rain on My Parade? - Backend API (NASA Data Version)
FastAPI application for weather probability calculations using NASA GPM IMERG and MERRA-2
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os
from dataclasses import dataclass
import logging
import numpy as np

# NASA Data Libraries
import earthaccess
import xarray as xr

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Will It Rain on My Parade? (NASA Data)",
    description="Weather probability calculator API using NASA GPM IMERG and MERRA-2",
    version="2.0.0"
)

# CORS middleware - same as before
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

@dataclass
class WeatherData:
    """Same structure as before to maintain compatibility"""
    date: str
    temp_max: float
    temp_min: float
    precip: float
    windspeed: float

class NASAWeatherService:
    """
    Service class to fetch and process NASA GPM IMERG and MERRA-2 data
    """
    
    def __init__(self):
        """
        Initialize the NASA data service
        Authenticates with NASA Earthdata using credentials from .netrc file
        """
        try:
            # Authenticate with NASA Earthdata
            # This reads your .netrc file automatically
            earthaccess.login()
            logger.info("Successfully authenticated with NASA Earthdata")
        except Exception as e:
            logger.error(f"Failed to authenticate with NASA Earthdata: {e}")
            raise
    
    async def fetch_historical_data(
        self, 
        lat: float, 
        lon: float, 
        month: int, 
        day: int, 
        years_back: int = 10
    ) -> List[WeatherData]:
        """
        Fetch historical weather data for a specific date across multiple years
        
        This combines:
        - GPM IMERG for precipitation data
        - MERRA-2 for temperature and wind data
        """
        weather_data = []
        current_year = datetime.now().year
        
        # Process each year
        for year in range(current_year - years_back, current_year):
            try:
                date_str = f"{year}-{month:02d}-{day:02d}"
                
                # Fetch data for this specific date
                daily_data = await self._fetch_single_day(lat, lon, year, month, day)
                
                if daily_data:
                    daily_data.date = date_str
                    weather_data.append(daily_data)
                    
            except Exception as e:
                logger.error(f"Error fetching data for {date_str}: {e}")
                continue
        
        return weather_data
    
    async def _fetch_single_day(
        self, 
        lat: float, 
        lon: float, 
        year: int,
        month: int,
        day: int
    ) -> Optional[WeatherData]:
        """
        Fetch weather data for a single day from NASA datasets
        
        This method:
        1. Fetches precipitation from GPM IMERG
        2. Fetches temperature and wind from MERRA-2
        3. Combines them into a single WeatherData object
        """
        
        # Get precipitation data from GPM IMERG
        precip = await self._fetch_imerg_precipitation(lat, lon, year, month, day)
        
        # Get temperature and wind from MERRA-2
        temp_max, temp_min, windspeed = await self._fetch_merra2_data(lat, lon, year, month, day)
        
        # Only return data if we successfully got all components
        if precip is not None and temp_max is not None:
            return WeatherData(
                date=f"{year}-{month:02d}-{day:02d}",
                temp_max=temp_max,
                temp_min=temp_min,
                precip=precip,
                windspeed=windspeed
            )
        
        return None
    
    async def _fetch_imerg_precipitation(
        self,
        lat: float,
        lon: float,
        year: int,
        month: int,
        day: int
    ) -> Optional[float]:
        """
        Fetch daily precipitation from GPM IMERG dataset
        
        Dataset: GPM_3IMERGDF (IMERG Final Daily)
        Variable: precipitation (mm/day)
        """
        try:
            # Create date for search
            start_date = datetime(year, month, day)
            end_date = start_date + timedelta(days=1)
            
            # Search for IMERG data
            results = earthaccess.search_data(
                short_name='GPM_3IMERGDF',  # Daily IMERG Final Run
                temporal=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )
            
            if not results:
                logger.warning(f"No IMERG data found for {year}-{month:02d}-{day:02d}")
                return None
            
            # Open the data file directly in memory (no download needed!)
            # This uses OPeNDAP protocol to stream only the data we need
            files = earthaccess.open(results)
            
            if not files:
                return None
            
            # Open with xarray
            ds = xr.open_dataset(files[0])
            
            # Extract precipitation at the specific location
            # IMERG uses 'precipitation' variable
            precip_data = ds['precipitation']
            
            # Select nearest point to our lat/lon
            # .sel with method='nearest' finds the closest grid point
            point_data = precip_data.sel(lat=lat, lon=lon, method='nearest')
            
            # Calculate daily total precipitation in mm
            # IMERG Final is already in mm/day, so we just need the value
            precip_mm = float(point_data.values)
            
            # Close the dataset
            ds.close()
            
            return precip_mm
            
        except Exception as e:
            logger.error(f"Error fetching IMERG data: {e}")
            return None
    
    async def _fetch_merra2_data(
        self,
        lat: float,
        lon: float,
        year: int,
        month: int,
        day: int
    ) -> tuple:
        """
        Fetch temperature and wind data from MERRA-2 M2T1NXSLV dataset
        
        Dataset: M2T1NXSLV (Single-Level Diagnostics, Hourly)
        Variables: T2M (temperature), U10M, V10M (wind components)
        
        Returns: (temp_max_celsius, temp_min_celsius, windspeed_ms)
        """
        try:
            # MERRA-2 requires specific date format
            start_date = datetime(year, month, day)
            end_date = start_date + timedelta(days=1)
            
            # Search for MERRA-2 data
            results = earthaccess.search_data(
                short_name='M2T1NXSLV',  # Single-Level Diagnostics
                temporal=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
            )
            
            if not results:
                logger.warning(f"No MERRA-2 data found for {year}-{month:02d}-{day:02d}")
                return None, None, None
            
            # Open the data file in memory
            files = earthaccess.open(results)
            
            if not files:
                return None, None, None
            
            # Open with xarray
            ds = xr.open_dataset(files[0])
            
            # MERRA-2 uses different coordinate names
            # lon is 'lon', lat is 'lat', time is 'time'
            
            # Extract variables at specific location
            # T2M: 2-meter air temperature (in Kelvin)
            temp_data = ds['T2M'].sel(lat=lat, lon=lon, method='nearest')
            
            # U10M and V10M: 10-meter wind components (m/s)
            u_wind = ds['U10M'].sel(lat=lat, lon=lon, method='nearest')
            v_wind = ds['V10M'].sel(lat=lat, lon=lon, method='nearest')
            
            # Calculate daily statistics
            # MERRA-2 is hourly, so we get 24 values for the day
            temp_kelvin = temp_data.values
            temp_max_k = float(np.max(temp_kelvin))
            temp_min_k = float(np.min(temp_kelvin))
            
            # Convert Kelvin to Celsius
            temp_max_c = temp_max_k - 273.15
            temp_min_c = temp_min_k - 273.15
            
            # Calculate wind speed from U and V components
            # Wind speed = sqrt(u^2 + v^2)
            u_values = u_wind.values
            v_values = v_wind.values
            wind_speeds = np.sqrt(u_values**2 + v_values**2)
            windspeed_ms = float(np.mean(wind_speeds))  # Average daily wind speed
            
            # Close the dataset
            ds.close()
            
            return temp_max_c, temp_min_c, windspeed_ms
            
        except Exception as e:
            logger.error(f"Error fetching MERRA-2 data: {e}")
            return None, None, None

# Global weather service instance
weather_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize the NASA weather service on app startup"""
    global weather_service
    try:
        weather_service = NASAWeatherService()
        logger.info("NASA Weather Service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize NASA Weather Service: {e}")
        weather_service = None

def calculate_probability(data: List[WeatherData], condition_func) -> float:
    """Calculate probability based on condition function (same as before)"""
    if not data:
        return 0.0
    
    matching_count = sum(1 for item in data if condition_func(item))
    return matching_count / len(data)

# ============================================================================
# API ENDPOINTS (Same as before, no changes needed!)
# ============================================================================

@app.get("/")
async def root():
    return {"message": "Will It Rain on My Parade? API (NASA Data)", "status": "healthy"}

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
            "source": "NASA GPM IMERG",
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
            "source": "NASA MERRA-2",
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
            "source": "NASA MERRA-2",
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
            "source": "NASA MERRA-2",
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
            "source": "NASA GPM IMERG + MERRA-2",
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
