"""
Layered Weather Probabilities API
Layer 1 (FAST): NASA Earthdata Cloud (S3) + xarray/dask, optimized for single-point, single-day-per-year queries
Layer 2 (FALLBACK): NASA POWER API (kept intact)

Goal: Make Layer 1 truly fast by:
  - Searching ONLY the needed day and a tiny spatial bbox (per year) to avoid thousands of granules
  - Using cloud-hosted results only, signing JUST the chosen granule (no bulk open)
  - Reading a SINGLE grid point slice with xarray BEFORE .load()
  - Running both datasets (IMERG/MERRA) per-year in parallel with an overall concurrency cap
  - Timeboxing Layer 1 so the API stays snappy and falls back to POWER if needed
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from dataclasses import dataclass
import os
import logging
import re
import time
import json

# --- Scientific/IO deps ---
import numpy as np
import xarray as xr
import dask
import earthaccess
import httpx

# =========================
# Global config / knobs
# =========================

# Dask: thread scheduler is sufficient for IO + small CPU ops
dask.config.set(scheduler="threads")

# Earthdata Cloud lives in us-west-2 (helps some libs pick region)
os.environ.setdefault("AWS_REGION", "us-west-2")

# Concurrency for per-year work (safe 6–10)
CONCURRENCY = int(os.getenv("NASA_IO_CONCURRENCY", "8"))

# Search radius (degrees) for tiny bounding box around the point
SEARCH_RADIUS_DEG = float(os.getenv("NASA_SEARCH_RADIUS_DEG", "0.2"))

# Time limit for Layer 1 before we return POWER fallback (seconds)
L1_TIMEOUT_S = float(os.getenv("L1_TIMEOUT_S", "8.0"))

# POWER fallback settings
POWER_DAILY_POINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMS = ["T2M_MAX", "T2M_MIN", "PRECTOTCORR", "WS10M"]
POWER_TIMEOUT_S = float(os.getenv("POWER_TIMEOUT_S", "5.0"))

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-api")


# =========================
# FastAPI app
# =========================

app = FastAPI(
    title="Will It Rain on My Parade? (Optimized Layered API)",
    description="Layer 1: NASA Earthdata Cloud (IMERG/MERRA-2). Layer 2: NASA POWER fallback.",
    version="3.0.0",
)


from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




# =========================
# Data model
# =========================

@dataclass
class WeatherData:
    date: str
    temp_max: float
    temp_min: float
    precip: float
    windspeed: float


# =========================
# Helpers (general)
# =========================

def calculate_probability(data: List[WeatherData], predicate) -> float:
    if not data:
        return 0.0
    return sum(1 for d in data if predicate(d)) / len(data)


def to_iso_date(y: int, m: int, d: int) -> str:
    return f"{y:04d}-{m:02d}-{d:02d}"


def tiny_bbox(lon: float, lat: float, radius: float) -> str:
    """
    Return a tiny bounding box string "W,S,E,N" for CMR search to avoid thousands of matches.
    """
    w = max(-180.0, lon - radius)
    e = min(180.0, lon + radius)
    s = max(-90.0,  lat - radius)
    n = min(90.0,   lat + radius)
    return f"{w},{s},{e},{n}"


# =========================
# Layer 1: Earthdata Cloud (IMERG + MERRA-2)
# =========================

class Layer1Service:
    """
    Optimized Earthdata Cloud access:
      * Per-year search with 24h temporal window + tiny spatial bbox (point +- radius)
      * Only sign ONE matching granule per dataset per day (no bulk open)
      * Read a single grid point slice BEFORE .load()
      * Parallelize years with semaphore to avoid throttling
      * Timebox entire run so API remains responsive
    """

    def __init__(self, concurrency: int = CONCURRENCY):
        # Reuse session; auth via ~/.netrc recommended
        earthaccess.login()
        logger.info("Layer 1: Authenticated with NASA Earthdata")
        self._sem = asyncio.Semaphore(concurrency)

    async def fetch_historical_data(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int = 10,
    ) -> List[WeatherData]:
        """
        Fetch one day-per-year for the last N years, combining IMERG daily precip + MERRA-2 hourly T/WS.
        """
        t0 = time.monotonic()
        now_year = datetime.now(tz=timezone.utc).year
        years = list(range(now_year - years_back, now_year))

        tasks = [
            self._fetch_single_day_both_datasets(lat, lon, y, month, day)
            for y in years
        ]
        # gather while respecting semaphore inside each task
        results = await asyncio.gather(*tasks, return_exceptions=True)

        out: List[WeatherData] = []
        for r in results:
            if isinstance(r, WeatherData):
                out.append(r)
            elif isinstance(r, Exception):
                logger.warning(f"Layer 1: year task failed: {r}")

        logger.info(f"Layer 1: got {len(out)}/{len(years)} points in {time.monotonic()-t0:.2f}s")
        return out

    async def _fetch_single_day_both_datasets(
        self, lat: float, lon: float, year: int, month: int, day: int
    ) -> Optional[WeatherData]:
        """
        For one specific YYYY-MM-DD:
          * Find one IMERG daily granule for that day near (lon,lat)
          * Find one MERRA-2 hourly single-level granule for that day near (lon,lat)
          * Read the point slice for precip (IMERG) and T/U/V (MERRA), compute stats
        """
        date_iso = to_iso_date(year, month, day)
        start_dt = datetime(year, month, day, tzinfo=timezone.utc)
        end_dt = start_dt + timedelta(days=1)

        # Build search params
        temporal = (start_dt.isoformat().replace("+00:00", "Z"),
                    end_dt.isoformat().replace("+00:00", "Z"))
        bbox = tiny_bbox(lon, lat, SEARCH_RADIUS_DEG)

        async with self._sem:
            # Search (cloud only), pick 1 granule per dataset
            imerg_url = await asyncio.to_thread(
                self._find_one_signed_granule,
                "GPM_3IMERGDF", temporal, bbox
            )
            merra_url = await asyncio.to_thread(
                self._find_one_signed_granule,
                "M2T1NXSLV", temporal, bbox
            )

        if not imerg_url or not merra_url:
            return None

        # Read the point slices concurrently (CPU/IO)
        async with self._sem:
            precip_task = asyncio.to_thread(self._read_imerg_precip_point, imerg_url, lat, lon)
            thermo_task = asyncio.to_thread(self._read_merra_point, merra_url, lat, lon)
            precip = await precip_task
            tmax, tmin, wind = await thermo_task

        if precip is None or tmax is None:
            return None

        return WeatherData(
            date=date_iso,
            temp_max=tmax,
            temp_min=tmin,
            precip=precip,
            windspeed=wind,
        )

    def _find_one_signed_granule(
        self,
        short_name: str,
        temporal: tuple,
        bbox_str: str,
    ) -> Optional[str]:
        """
        Do a *narrow* CMR search (24h window + tiny bbox) and return a single signed URL
        for a cloud-hosted granule. Avoids opening thousands of results.
        """
        try:
            results = earthaccess.search_data(
                short_name=short_name,
                temporal=temporal,
                bounding_box=bbox_str,
                cloud_hosted=True,
                count=10,           # keep it tiny
                page_size=10,
            )
            if not results:
                return None

            # Prefer the first result with a valid signable link
            for r in results:
                signed = earthaccess.sign(r)  # returns list of URLs
                if signed:
                    return signed[0]
            return None
        except Exception as e:
            logger.warning(f"Layer 1: search/sign failed for {short_name} @ {temporal}: {e}")
            return None

    # ---- xarray readers (slice BEFORE .load()) ----

    def _read_imerg_precip_point(self, url: str, lat: float, lon: float) -> Optional[float]:
        try:
            ds = xr.open_dataset(url, chunks={})
            # daily precip variable
            v = ds["precipitation"].sel(lat=lat, lon=lon, method="nearest")
            val = float(v.load().values.item())  # only the tiny slice is fetched
            ds.close()
            return val
        except Exception as e:
            logger.warning(f"Layer 1: IMERG read failed for {url}: {e}")
            return None

    def _read_merra_point(self, url: str, lat: float, lon: float):
        try:
            ds = xr.open_dataset(url, chunks={})
            t = ds["T2M"].sel(lat=lat, lon=lon, method="nearest").load().values  # K, hourly
            u = ds["U10M"].sel(lat=lat, lon=lon, method="nearest").load().values
            v = ds["V10M"].sel(lat=lat, lon=lon, method="nearest").load().values
            ds.close()

            tmax_c = float(np.max(t) - 273.15)
            tmin_c = float(np.min(t) - 273.15)
            wind   = float(np.sqrt(u**2 + v**2).mean())
            return tmax_c, tmin_c, wind
        except Exception as e:
            logger.warning(f"Layer 1: MERRA read failed for {url}: {e}")
            return None, None, None


# =========================
# Layer 2: NASA POWER (fallback intact)
# =========================

class Layer2Power:
    def __init__(self, timeout_s: float = POWER_TIMEOUT_S):
        self.timeout = timeout_s

    async def fetch_historical_data(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int = 10,
    ) -> List[WeatherData]:
        """
        Pull the exact YYYYMMDD for each year via POWER (fast but coarser 0.5° grid).
        """
        now_year = datetime.now(tz=timezone.utc).year
        years = list(range(now_year - years_back, now_year))
        out: List[WeatherData] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            tasks = [self._fetch_one(client, lat, lon, y, month, day) for y in years]
            done = await asyncio.gather(*tasks, return_exceptions=True)

        for r in done:
            if isinstance(r, WeatherData):
                out.append(r)
        return out

    async def _fetch_one(
        self, client: httpx.AsyncClient, lat: float, lon: float, year: int, month: int, day: int
    ) -> Optional[WeatherData]:
        ds = f"{year}{month:02d}{day:02d}"
        params = {
            "parameters": ",".join(POWER_PARAMS),
            "community": "RE",
            "longitude": lon,
            "latitude": lat,
            "start": ds,
            "end": ds,
            "format": "JSON",
        }
        try:
            r = await client.get(POWER_DAILY_POINT, params=params)
            if r.status_code == 204:
                return None
            r.raise_for_status()
            j = r.json()
            p = j.get("properties", {}).get("parameter", {})
            tmax = p.get("T2M_MAX", {}).get(ds)
            tmin = p.get("T2M_MIN", {}).get(ds)
            prec = p.get("PRECTOTCORR", {}).get(ds)
            ws10 = p.get("WS10M", {}).get(ds)
            if None in (tmax, tmin, prec, ws10):
                return None
            return WeatherData(
                date=f"{year}-{month:02d}-{day:02d}",
                temp_max=float(tmax),
                temp_min=float(tmin),
                precip=float(prec),
                windspeed=float(ws10),
            )
        except Exception as e:
            logger.warning(f"Layer 2: POWER fetch failed for {ds}: {e}")
            return None


# =========================
# Service singletons
# =========================

layer1: Optional[Layer1Service] = None
layer2: Optional[Layer2Power] = None

@app.on_event("startup")
async def _startup():
    global layer1, layer2
    layer1 = Layer1Service(CONCURRENCY)
    layer2 = Layer2Power(POWER_TIMEOUT_S)
    logger.info("Services started (Layer1=Earthdata, Layer2=POWER)")

@app.on_event("shutdown")
async def _shutdown():
    # nothing special to close; httpx client is created per-call in Layer2
    pass


# =========================
# Endpoints (Layer 1 with timebox, Layer 2 fallback)
# =========================

async def _get_data_with_timebox(lat, lon, month, day, years_back=10):
    """
    Try Layer 1 (Earthdata) with timeout; if it times out or fails, fall back to POWER.
    Returns (data, source_label)
    """
    assert layer1 and layer2
    try:
        data = await asyncio.wait_for(
            layer1.fetch_historical_data(lat, lon, month, day, years_back=years_back),
            timeout=L1_TIMEOUT_S
        )
        if data:
            return data, "NASA GPM IMERG + MERRA-2 (Earthdata Cloud)"
    except asyncio.TimeoutError:
        logger.warning("Layer 1: timed out; falling back to POWER")
    except Exception as e:
        logger.warning(f"Layer 1: error '{e}'; falling back to POWER")

    data2 = await layer2.fetch_historical_data(lat, lon, month, day, years_back=years_back)
    return data2, "NASA POWER (fallback)"


@app.get("/")
async def root():
    return {"message": "Weather Probabilities API (Layered, optimized)", "status": "healthy"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/probability/rain")
async def probability_rain(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    threshold: float = Query(0.1, ge=0, description="Rain threshold in mm"),
    years_back: int = Query(10, ge=1, le=30),
):
    try:
        data, source = await _get_data_with_timebox(lat, lon, month, day, years_back)
        prob = calculate_probability(data, lambda x: x.precip > threshold)
        return {
            "probability": round(prob, 3),
            "threshold": threshold,
            "data_points": len(data),
            "source": source,
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
        }
    except Exception as e:
        logger.error(f"/probability/rain error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/probability/heat")
async def probability_heat(
    lat: float = Query(...),
    lon: float = Query(...),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    threshold: float = Query(35.0),
    years_back: int = Query(10, ge=1, le=30),
):
    try:
        data, source = await _get_data_with_timebox(lat, lon, month, day, years_back)
        prob = calculate_probability(data, lambda x: x.temp_max > threshold)
        return {
            "probability": round(prob, 3),
            "threshold": threshold,
            "data_points": len(data),
            "source": source,
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
        }
    except Exception as e:
        logger.error(f"/probability/heat error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/probability/cold")
async def probability_cold(
    lat: float = Query(...),
    lon: float = Query(...),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    threshold: float = Query(5.0),
    years_back: int = Query(10, ge=1, le=30),
):
    try:
        data, source = await _get_data_with_timebox(lat, lon, month, day, years_back)
        prob = calculate_probability(data, lambda x: x.temp_min < threshold)
        return {
            "probability": round(prob, 3),
            "threshold": threshold,
            "data_points": len(data),
            "source": source,
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
        }
    except Exception as e:
        logger.error(f"/probability/cold error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/probability/wind")
async def probability_wind(
    lat: float = Query(...),
    lon: float = Query(...),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    threshold: float = Query(15.0),
    years_back: int = Query(10, ge=1, le=30),
):
    try:
        data, source = await _get_data_with_timebox(lat, lon, month, day, years_back)
        prob = calculate_probability(data, lambda x: x.windspeed > threshold)
        return {
            "probability": round(prob, 3),
            "threshold": threshold,
            "data_points": len(data),
            "source": source,
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
        }
    except Exception as e:
        logger.error(f"/probability/wind error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/probability/all")
async def probability_all(
    lat: float = Query(...),
    lon: float = Query(...),
    month: int = Query(..., ge=1, le=12),
    day: int = Query(..., ge=1, le=31),
    rain_threshold: float = Query(0.1, ge=0),
    heat_threshold: float = Query(35.0),
    cold_threshold: float = Query(5.0),
    wind_threshold: float = Query(15.0),
    years_back: int = Query(10, ge=1, le=30),
):
    try:
        data, source = await _get_data_with_timebox(lat, lon, month, day, years_back)

        rain_prob = calculate_probability(data, lambda x: x.precip > rain_threshold)
        heat_prob = calculate_probability(data, lambda x: x.temp_max > heat_threshold)
        cold_prob = calculate_probability(data, lambda x: x.temp_min < cold_threshold)
        wind_prob = calculate_probability(data, lambda x: x.windspeed > wind_threshold)

        return {
            "rain": {"probability": round(rain_prob, 3), "threshold": rain_threshold},
            "heat": {"probability": round(heat_prob, 3), "threshold": heat_threshold},
            "cold": {"probability": round(cold_prob, 3), "threshold": cold_threshold},
            "wind": {"probability": round(wind_prob, 3), "threshold": wind_threshold},
            "source": source,
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
        logger.error(f"/probability/all error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# =========================
# Local run
# =========================

if __name__ == "__main__":
    import uvicorn
    # Run WITHOUT --reload to keep a single process (cleaner for signed URL auth)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))

