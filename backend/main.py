"""
Will It Rain on My Parade? - Backend API (Hybrid NASA Data Version)
FastAPI application with 3-layer architecture:
- Layer 1: Earthdata Cloud S3 + Parallel xarray Point-Slicing (PRIMARY)
- Layer 2: NASA POWER API (FALLBACK)
- Layer 3: Response Logic & Mode Handling
"""
import asyncio
import logging
import os
import re
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Any, Tuple

# External Libraries
import aiohttp
import numpy as np
import netCDF4 as nc
from dateutil import parser as dateparser
import earthaccess

# FastAPI Framework
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(
    title="Will It Rain on My Parade? (Hybrid NASA Data)",
    description="Weather probability calculator with 3-layer hybrid architecture",
    version="3.0.0"
)

# ----------------------------------------------------------------------
# MIDDLEWARE
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# ENUMS
# ----------------------------------------------------------------------
class FetchMode(str, Enum):
    """User-selectable fetch modes."""
    PRECISE = "precise"  # Wait up to 30s for Layer 1 (real satellite data)
    FAST = "fast"        # Return Layer 2 only (<1s)
    HYBRID = "hybrid"    # Run both in parallel, return both with comparison

# ----------------------------------------------------------------------
# DATA STRUCTURES
# ----------------------------------------------------------------------
@dataclass
class WeatherData:
    """Weather data structure for a single day."""
    date: str
    temp_max: float
    temp_min: float
    precip: float
    windspeed: float

@dataclass
class LayerResponse:
    """Response structure from a data layer."""
    data: List[WeatherData]
    source: str
    timing_ms: float
    success: bool
    error: Optional[str] = None

# ----------------------------------------------------------------------
# UTILITY FUNCTIONS (add more as you build out)
# ----------------------------------------------------------------------
def now_ms() -> int:
    """Helper to get current time in milliseconds."""
    return int(time.time() * 1000)

# Example utility for timing async tasks
async def timed_task(coro, label: str) -> Tuple[Any, float]:
    start = time.perf_counter()
    try:
        result = await coro
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(f"[{label}] completed in {elapsed_ms:.2f} ms (success={success})")
    return LayerResponse(
        data=result or [],
        source=label,
        timing_ms=elapsed_ms,
        success=success,
        error=error
    )

# ----------------------------------------------------------------------
# ENDPOINTS (example placeholder)
# ----------------------------------------------------------------------
@app.get("/status")
async def status():
    """Simple health check endpoint."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ============================================================================
# LAYER 1: Earthdata Cloud S3 + Parallel xarray Point-Slicing
# ============================================================================

class EarthdataService:
    def __init__(
        self,
        max_concurrency: int = 6,
        early_return_count: int = 7,
        search_radius_deg: float = 0.12,
        per_year_search_first: bool = True,
        cache_ttl_seconds: int = 600,
    ):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(self.max_concurrency)
        self.early_return_count = early_return_count
        self.search_radius_deg = float(search_radius_deg)
        self.per_year_search_first = per_year_search_first
        self._search_cache: Dict[str, Tuple[Dict[int, object], Dict[int, object], float]] = {}
        # cache coordinates per granule URL to avoid re-reading lat/lon for repeated opens
        self._coords_cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self.session_initialized = False

    def initialize_session(self):
        """Try environment login first, then interactive/other method."""
        try:
            earthaccess.login(strategy="environment")
            self.session_initialized = True
            logger.info("Earthdata session initialized (environment)")
            return
        except Exception as e:
            logger.debug(f"env login failed: {e}")
        try:
            earthaccess.login()
            self.session_initialized = True
            logger.info("Earthdata session initialized (default)")
            return
        except Exception as e:
            self.session_initialized = False
            logger.error(f"Earthdata authentication failed: {e}")

    async def fetch_with_timeout(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int = 10,
        timeout: float = 10.0,
    ) -> LayerResponse:
        start = time.time()
        try:
            data = await asyncio.wait_for(
                self._fetch_point_history(lat, lon, month, day, years_back), timeout=timeout
            )
            elapsed_ms = (time.time() - start) * 1000.0
            success = len(data) >= max(3, min(self.early_return_count, years_back))
            if success:
                return LayerResponse(data=data, source="NASA GPM IMERG + MERRA-2 (S3 OPENDAP)", timing_ms=elapsed_ms, success=True)
            else:
                return LayerResponse(data=data, source="NASA GPM IMERG + MERRA-2 (S3 OPENDAP)", timing_ms=elapsed_ms, success=False, error=f"Insufficient data ({len(data)} points)")
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start) * 1000.0
            logger.warning(f"Layer1 fetch timeout after {elapsed_ms:.0f}ms")
            return LayerResponse(data=[], source="NASA GPM IMERG + MERRA-2 (S3 OPENDAP)", timing_ms=elapsed_ms, success=False, error="Timeout")
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000.0
            logger.error(f"Layer1 fetch failed: {e}")
            return LayerResponse(data=[], source="NASA GPM IMERG + MERRA-2 (S3 OPENDAP)", timing_ms=elapsed_ms, success=False, error=str(e))

    # ---------------------
    # Main orchestration
    # ---------------------
    async def _fetch_point_history(self, lat: float, lon: float, month: int, day: int, years_back: int) -> List[WeatherData]:
        current_year = datetime.now().year
        start_year = current_year - years_back
        cache_key = f"yr_{start_year}_{current_year}_{month:02d}{day:02d}_{round(lat,4)}_{round(lon,4)}"
        cached = self._search_cache.get(cache_key)
        if cached:
            imerg_map, merra_map, ts = cached
            if time.time() - ts < 600:
                logger.debug("Using cached granule mapping.")
            else:
                imerg_map, merra_map = await self._search_for_years(lat, lon, month, day, start_year, current_year)
                self._search_cache[cache_key] = (imerg_map, merra_map, time.time())
        else:
            imerg_map, merra_map = await self._search_for_years(lat, lon, month, day, start_year, current_year)
            self._search_cache[cache_key] = (imerg_map, merra_map, time.time())

        years = list(range(start_year, current_year))
        years.reverse()  # prefer recent years first

        tasks = []
        for y in years:
            imerg_file = imerg_map.get(y)
            merra_file = merra_map.get(y)
            if imerg_file or merra_file:
                # schedule extract for this year; controlled concurrency handled by semaphore inside
                tasks.append(asyncio.create_task(self._extract_for_year(lat, lon, y, month, day, imerg_file, merra_file)))

        if not tasks:
            logger.warning("No granules found for requested date")
            return []

        results: List[WeatherData] = []
        try:
            for fut in asyncio.as_completed(tasks):
                try:
                    res = await fut
                    if res:
                        results.append(res)
                        logger.debug(f"Collected {res.date}; total={len(results)}")
                        if len(results) >= self.early_return_count:
                            # cancel remaining
                            for t in tasks:
                                if not t.done():
                                    t.cancel()
                            logger.info(f"✅ Early return with {len(results)} points")
                            return results
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.debug(f"Extract task error: {e}")
                    continue
        except asyncio.TimeoutError:
            logger.warning("Batch extraction timed out (outer)")

        # cancel leftovers
        for t in tasks:
            if not t.done():
                t.cancel()
        return results

    # ---------------------
    # Search logic
    # ---------------------
    async def _search_for_years(self, lat, lon, month, day, start_year, end_year) -> Tuple[Dict[int, object], Dict[int, object]]:
        """Per-year search via earthaccess.search_data (fast predictable)."""
        if self.per_year_search_first:
            years = list(range(start_year, end_year))
            imerg_map: Dict[int, object] = {}
            merra_map: Dict[int, object] = {}

            async def search_year(year, short_name):
                s = f"{year}-{month:02d}-{day:02d}"
                try:
                    return await asyncio.to_thread(
                        earthaccess.search_data,
                        short_name=short_name,
                        temporal=(s, s),
                        bounding_box=(lon - self.search_radius_deg, lat - self.search_radius_deg, lon + self.search_radius_deg, lat + self.search_radius_deg),
                        count=1,
                        cloud_hosted=True,
                    )
                except Exception as e:
                    logger.debug(f"search_data thread error for {short_name} {year}: {e}")
                    return []

            sem = asyncio.Semaphore(min(12, max(4, self.max_concurrency * 2)))

            async def guarded_search(year, short_name):
                async with sem:
                    return await search_year(year, short_name)

            tasks = []
            for y in years:
                tasks.append(asyncio.create_task(guarded_search(y, 'GPM_3IMERGDF')))
                tasks.append(asyncio.create_task(guarded_search(y, 'M2T1NXSLV')))

            gathered = await asyncio.gather(*tasks, return_exceptions=True)

            # interpret results pairwise
            for i, y in enumerate(years):
                try:
                    imerg_res = gathered[2 * i]
                    merra_res = gathered[2 * i + 1]
                except Exception:
                    imerg_res = []
                    merra_res = []
                if imerg_res:
                    try:
                        imerg_map[y] = imerg_res[0]
                    except Exception:
                        imerg_map[y] = imerg_res
                if merra_res:
                    try:
                        merra_map[y] = merra_res[0]
                    except Exception:
                        merra_map[y] = merra_res

            logger.info(f"Found {len(imerg_map)} IMERG + {len(merra_map)} MERRA-2 files (per-year search)")
            return imerg_map, merra_map

        # fallback: batch search (less preferred)
        try:
            start_date = datetime(start_year, month, day)
            end_date = datetime(end_year - 1, month, day)
            imerg_results = await asyncio.to_thread(earthaccess.search_data, short_name='GPM_3IMERGDF', temporal=(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            merra_results = await asyncio.to_thread(earthaccess.search_data, short_name='M2T1NXSLV', temporal=(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

            def make_map(results):
                m = {}
                if not results:
                    return m
                for r in results:
                    try:
                        temporal = getattr(r, 'temporal', None)
                        if temporal:
                            dt = dateparser.parse(str(temporal[0]))
                            y = dt.year
                            # keep the latest found for that year
                            m[y] = r
                    except Exception:
                        continue
                return m

            imerg_map = make_map(imerg_results)
            merra_map = make_map(merra_results)
            logger.info(f"Found {len(imerg_map)} IMERG + {len(merra_map)} MERRA-2 files (batch search)")
            return imerg_map, merra_map
        except Exception as e:
            logger.error(f"Batch search failed: {e}")
            return {}, {}

    # ---------------------
    # Per-year extraction: one point reads using netCDF4 (OPeNDAP) in threads
    # ---------------------
    async def _extract_for_year(self, lat, lon, year, month, day, imerg_file, merra_file) -> Optional[WeatherData]:
        """Fetch precip (IMERG) and MERRA-2 T2M/U10/V10 for the single date-year.
           Runs within asyncio.to_thread via this wrapper below.
        """
        # Use semaphore to limit concurrent opens to avoid overloading fsspec/OPeNDAP
        async with self.semaphore:
            return await asyncio.to_thread(self._extract_for_year_blocking, lat, lon, year, month, day, imerg_file, merra_file)

    def _extract_for_year_blocking(self, lat, lon, year, month, day, imerg_file, merra_file) -> Optional[WeatherData]:
        """Blocking implementation using netCDF4.Dataset remote OPeNDAP URL (fast subsetting)."""
        precip = None
        temp_max = None
        temp_min = None
        windspeed = None

        try:
            # Helper to get a usable URL from an earthaccess result element
            def _get_url_from_granule(g):
                if g is None:
                    return None
                # sometimes earthaccess returns objects; try .url or .urlpath or str(g)
                try:
                    return getattr(g, "url", None) or getattr(g, "urlpath", None) or str(g)
                except Exception:
                    return str(g)

            imerg_url = _get_url_from_granule(imerg_file)
            merra_url = _get_url_from_granule(merra_file)

            if imerg_url:
                try:
                    p = self._read_imerg_point_blocking(imerg_url, lat, lon)
                    if p is not None:
                        precip = float(p)
                except Exception as e:
                    logger.debug(f"IMERG read failed for {year}: {e}")

            if merra_url:
                try:
                    tmax, tmin, wind = self._read_merra_point_blocking(merra_url, lat, lon)
                    if tmax is not None and tmin is not None:
                        temp_max, temp_min = float(tmax), float(tmin)
                    if wind is not None:
                        windspeed = float(wind)
                except Exception as e:
                    logger.debug(f"MERRA read failed for {year}: {e}")

            if precip is None and temp_max is None:
                return None

            date_str = f"{year}-{month:02d}-{day:02d}"
            return WeatherData(date_str, temp_max or 0.0, temp_min or 0.0, precip or 0.0, windspeed or 0.0)
        except Exception as e:
            logger.debug(f"_extract_for_year({year}) failed: {e}")
            return None

    # ---------------------
    # Low-level readers (blocking). Use netCDF4 to leverage OPeNDAP server subsetting.
    # ---------------------
    def _find_coord_vars(self, ds: nc.Dataset) -> Tuple[Optional[str], Optional[str]]:
        """Try to discover lat/lon variable names in dataset."""
        names = list(ds.variables.keys())
        # common candidates
        lat_candidates = ["lat", "latitude", "y", "nav_lat"]
        lon_candidates = ["lon", "longitude", "x", "nav_lon"]
        latname = next((n for n in names if n.lower() in lat_candidates), None)
        lonname = next((n for n in names if n.lower() in lon_candidates), None)
        # fallback: find variables with 1D arrays and matching ranges
        if not latname or not lonname:
            for n in names:
                try:
                    var = ds.variables[n]
                    if getattr(var, "ndim", 0) == 1:
                        arr = np.array(var[:])
                        if latname is None and arr.min() >= -90 and arr.max() <= 90:
                            latname = n
                        if lonname is None and arr.min() >= -180 and arr.max() <= 360:
                            lonname = n
                except Exception:
                    continue
        return latname, lonname

    def _read_imerg_point_blocking(self, url: str, lat: float, lon: float) -> Optional[float]:
        """Open IMERG granule via netCDF4 (OPeNDAP URL) and read nearest precip value."""
        ds = None
        try:
            # If cached coords exist for url, use them
            coords = self._coords_cache.get(url)
            if coords:
                latv, lonv = coords
            else:
                ds = nc.Dataset(url)  # remote OPeNDAP open (lightweight)
                latname, lonname = self._find_coord_vars(ds)
                if latname is None or lonname is None:
                    raise RuntimeError("lat/lon not found in IMERG dataset")
                latv = np.array(ds.variables[latname][:])
                lonv = np.array(ds.variables[lonname][:])
                # cache coordinate arrays (small)
                self._coords_cache[url] = (latv, lonv)
                ds.close()
                ds = None

            # compute nearest indices
            i = int(np.abs(latv - lat).argmin())
            j = int(np.abs(lonv - lon).argmin())

            # reopen dataset and read precip variable at the nearest index
            ds = nc.Dataset(url)
            # find precip variable candidates
            varnames = [v for v in ds.variables.keys() if "precip" in v.lower() or "precipitation" in v.lower()]
            if not varnames:
                # fallback: pick first 1- or 3-d var with reasonable range
                varnames = [v for v in ds.variables.keys() if ds.variables[v].ndim >= 2]
            if not varnames:
                return None
            var = ds.variables[varnames[0]]
            # determine index order
            dims = var.dimensions  # e.g. ('time','lat','lon') or ('lat','lon')
            # build index tuple: pick first time index (0) if present
            idx = []
            for d in dims:
                if d.lower().startswith("time"):
                    idx.append(0)
                elif d.lower() in ("lat", "latitude", "y", "nav_lat"):
                    idx.append(i)
                elif d.lower() in ("lon", "longitude", "x", "nav_lon"):
                    idx.append(j)
                else:
                    # unknown dimension: pick 0 or nearest
                    try:
                        size = ds.variables[d].size
                        idx.append(0)
                    except Exception:
                        idx.append(0)
            val = var[tuple(idx)]
            v = np.array(val).astype(float)
            if np.isnan(v):
                return None
            return float(np.asarray(v).flat[0])
        except Exception as e:
            logger.debug(f"_read_imerg_point error for {url}: {e}")
            return None
        finally:
            try:
                if ds is not None:
                    ds.close()
            except Exception:
                pass

    def _read_merra_point_blocking(self, url: str, lat: float, lon: float) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Open MERRA-2 granule and read tmax (K)->C, tmin (K)->C, and mean wind speed (m/s)."""
        ds = None
        try:
            coords = self._coords_cache.get(url)
            if coords:
                latv, lonv = coords
            else:
                ds = nc.Dataset(url)
                latname, lonname = self._find_coord_vars(ds)
                if latname is None or lonname is None:
                    raise RuntimeError("lat/lon not found in MERRA dataset")
                latv = np.array(ds.variables[latname][:])
                lonv = np.array(ds.variables[lonname][:])
                self._coords_cache[url] = (latv, lonv)
                ds.close()
                ds = None

            i = int(np.abs(latv - lat).argmin())
            j = int(np.abs(lonv - lon).argmin())

            ds = nc.Dataset(url)

            # Heuristics to find temperature and wind variables
            var_names = list(ds.variables.keys())
            t_candidates = [n for n in var_names if 'T2' in n.upper() or 'T2M' in n.upper() or 'T2M_MAX' in n.upper() or 'air_temperature' in n.lower()]
            u_candidates = [n for n in var_names if 'U10' in n.upper() or 'U_10' in n.upper() or 'UGRD' in n.upper()]
            v_candidates = [n for n in var_names if 'V10' in n.upper() or 'V_10' in n.upper() or 'VGRD' in n.upper()]

            # Pick sensible defaults
            tvar_name = t_candidates[0] if t_candidates else None

            # If dataset doesn't provide direct T2M max/min, we may only have instantaneous temperature; fallback: compute max/min across available time slices
            tmax_c = None
            tmin_c = None
            if tvar_name:
                tvar = ds.variables[tvar_name]
                dims = tvar.dimensions
                # build slice that selects all time indices but nearest lat/lon
                idx = []
                for d in dims:
                    if d.lower().startswith("time"):
                        idx.append(slice(None))
                    elif d.lower() in ("lat", "latitude", "y", "nav_lat"):
                        idx.append(i)
                    elif d.lower() in ("lon", "longitude", "x", "nav_lon"):
                        idx.append(j)
                    else:
                        idx.append(0)
                arr = np.array(tvar[tuple(idx)]).astype(float)
                if arr.size:
                    tmax_k = float(np.nanmax(arr))
                    tmin_k = float(np.nanmin(arr))
                    tmax_c = tmax_k - 273.15
                    tmin_c = tmin_k - 273.15

            # wind: average of magnitude of U and V if available
            wind_ms = None
            if u_candidates and v_candidates:
                uvar = ds.variables[u_candidates[0]]
                vvar = ds.variables[v_candidates[0]]
                dims_u = uvar.dimensions
                dims_v = vvar.dimensions

                def build_idx_for_var(var_dims):
                    idx = []
                    for d in var_dims:
                        if d.lower().startswith("time"):
                            idx.append(slice(None))
                        elif d.lower() in ("lat", "latitude", "y", "nav_lat"):
                            idx.append(i)
                        elif d.lower() in ("lon", "longitude", "x", "nav_lon"):
                            idx.append(j)
                        else:
                            idx.append(0)
                    return tuple(idx)

                u_arr = np.array(uvar[build_idx_for_var(dims_u)]).astype(float)
                v_arr = np.array(vvar[build_idx_for_var(dims_v)]).astype(float)
                if u_arr.size and v_arr.size:
                    mag = np.sqrt(u_arr**2 + v_arr**2)
                    wind_ms = float(np.nanmean(mag))

            return tmax_c, tmin_c, wind_ms
        except Exception as e:
            logger.debug(f"_read_merra_point error for {url}: {e}")
            return None, None, None
        finally:
            try:
                if ds is not None:
                    ds.close()
            except Exception:
                pass

    # ---------------------
    # Backwards-compat shims used by tests (if they reference older method names)
    # ---------------------
    async def _fetch_single_day(self, lat, lon, year, month, day):
        return await self._extract_for_year(lat, lon, year, month, day, None, None)

    async def _fetch_single_day_controlled(self, lat, lon, year, month, day):
        async with self.semaphore:
            return await self._fetch_single_day(lat, lon, year, month, day)

    async def _fetch_parallel(self, lat, lon, month, day, years_back=10):
        return await self._fetch_point_history(lat, lon, month, day, years_back)

# class EarthdataService:
#     """
#     Optimized Layer 1 with realistic timeouts and early return strategy
#     Target: 5-10s response time for 80%+ of requests
#     """
    
#     def __init__(self):
#         self.auth = None
#         self.semaphore = asyncio.Semaphore(10)  # Increased from 8 to 10 for better throughput
#         self.session_initialized = False
    
#     def initialize_session(self):
#         """Initialize Earthdata session"""
#         try:
#             self.auth = earthaccess.login(strategy="environment")
#             self.session_initialized = True
#             logger.info("✓ Earthdata session initialized (environment)")
#             return
#         except Exception as e:
#             logger.debug(f"Environment strategy failed: {e}")
        
#         try:
#             self.auth = earthaccess.login()
#             self.session_initialized = True
#             logger.info("✓ Earthdata session initialized (default)")
#             return
#         except Exception as e:
#             logger.warning(f"⚠ Earthdata authentication failed: {e}")
#             self.session_initialized = False
    
#     async def fetch_with_timeout(
#         self,
#         lat: float,
#         lon: float,
#         month: int,
#         day: int,
#         years_back: int = 10,
#         timeout: float = 45.0
#     ) -> 'LayerResponse':
#         """
#         Smart fetch with early return strategy
#         Returns as soon as we have good data (5+ points) or timeout
#         """
#         start_time = time.time()
        
#         try:
#             # Use realistic 25s timeout (not 30s to leave buffer)
#             data = await asyncio.wait_for(
#                 self._fetch_parallel_smart(lat, lon, month, day, years_back),
#                 timeout=25.0
#             )
            
#             elapsed_ms = (time.time() - start_time) * 1000
            
#             if len(data) >= 5:  # Success if we got meaningful data
#                 logger.info(f"✓ Layer 1 succeeded: {len(data)} points in {elapsed_ms:.0f}ms")
#                 return LayerResponse(
#                     data=data,
#                     source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
#                     timing_ms=elapsed_ms,
#                     success=True
#                 )
#             else:
#                 logger.warning(f"⚠ Layer 1: Only {len(data)} data points retrieved")
#                 return LayerResponse(
#                     data=data,
#                     source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
#                     timing_ms=elapsed_ms,
#                     success=False,
#                     error=f"Insufficient data: {len(data)} points"
#                 )
            
#         except asyncio.TimeoutError:
#             elapsed_ms = (time.time() - start_time) * 1000
#             logger.warning(f"⚠ Layer 1 timeout after {elapsed_ms:.0f}ms")
#             return LayerResponse(
#                 data=[],
#                 source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
#                 timing_ms=elapsed_ms,
#                 success=False,
#                 error="Timeout exceeded"
#             )
            
#         except Exception as e:
#             elapsed_ms = (time.time() - start_time) * 1000
#             logger.error(f"✗ Layer 1 error: {e}")
#             return LayerResponse(
#                 data=[],
#                 source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
#                 timing_ms=elapsed_ms,
#                 success=False,
#                 error=str(e)
#             )
    
#     async def _fetch_parallel_smart(
#         self,
#         lat: float,
#         lon: float,
#         month: int,
#         day: int,
#         years_back: int
#     ) -> List['WeatherData']:
#         """
#         Smart parallel fetch with early return
#         Strategy: Process years in reverse order (most recent first)
#         Return early once we have 5+ successful data points
#         """
#         current_year = datetime.now().year
#         years = list(range(current_year - years_back, current_year))
#         years.reverse()  # Most recent first (better data quality)
        
#         # Track results as they complete
#         completed_data = []
#         pending_tasks = []
        
#         # Create all tasks
#         for year in years:
#             task = asyncio.create_task(
#                 self._fetch_single_day_controlled(lat, lon, year, month, day)
#             )
#             pending_tasks.append(task)
        
#         # Process tasks as they complete
#         try:
#             # Use as_completed to get results as soon as they're ready
#             for completed_task in asyncio.as_completed(pending_tasks, timeout=20.0):
#                 try:
#                     result = await asyncio.wait_for(completed_task, timeout=0.1)
#                     if result and isinstance(result, WeatherData):
#                         completed_data.append(result)
                        
#                         # EARLY RETURN: If we have 7+ points and 8+ seconds have passed, return
#                         # This ensures we don't wait unnecessarily
#                         if len(completed_data) >= 7:
#                             logger.info(f"✓ Early return with {len(completed_data)} data points")
#                             # Cancel remaining tasks
#                             for task in pending_tasks:
#                                 if not task.done():
#                                     task.cancel()
#                             return completed_data
                            
#                 except Exception:
#                     continue
                    
#         except asyncio.TimeoutError:
#             logger.info(f"Parallel fetch completed with {len(completed_data)} points")
        
#         # Cancel any remaining tasks
#         for task in pending_tasks:
#             if not task.done():
#                 task.cancel()
        
#         return completed_data
    
#     async def _fetch_single_day_controlled(
#         self,
#         lat: float,
#         lon: float,
#         year: int,
#         month: int,
#         day: int
#     ) -> Optional['WeatherData']:
#         """Fetch with semaphore control"""
#         async with self.semaphore:
#             return await self._fetch_single_day(lat, lon, year, month, day)
    
#     async def _fetch_single_day(
#         self,
#         lat: float,
#         lon: float,
#         year: int,
#         month: int,
#         day: int
#     ) -> Optional['WeatherData']:
#         """
#         Fetch single day with REALISTIC timeouts
#         Each dataset gets 8 seconds (not 3)
#         """
#         try:
#             # Run both datasets in parallel with 8s timeout each
#             results = await asyncio.gather(
#                 asyncio.wait_for(
#                     self._fetch_imerg_precipitation(lat, lon, year, month, day),
#                     timeout=8.0
#                 ),
#                 asyncio.wait_for(
#                     self._fetch_merra2_data(lat, lon, year, month, day),
#                     timeout=8.0
#                 ),
#                 return_exceptions=True
#             )
            
#             precip = results[0] if not isinstance(results[0], Exception) else None
#             temp_data = results[1] if not isinstance(results[1], Exception) else (None, None, None)
            
#             # Unpack temp data
#             if isinstance(temp_data, tuple) and len(temp_data) == 3:
#                 temp_max, temp_min, windspeed = temp_data
#             else:
#                 temp_max, temp_min, windspeed = None, None, None
            
#             # Return if we have at least precip OR temp data
#             if precip is not None or temp_max is not None:
#                 return WeatherData(
#                     date=f"{year}-{month:02d}-{day:02d}",
#                     temp_max=temp_max or 0.0,
#                     temp_min=temp_min or 0.0,
#                     precip=precip or 0.0,
#                     windspeed=windspeed or 0.0
#                 )
            
#             return None
            
#         except Exception as e:
#             logger.debug(f"Failed {year}-{month:02d}-{day:02d}: {e}")
#             return None
    
#     async def _fetch_imerg_precipitation(
#         self,
#         lat: float,
#         lon: float,
#         year: int,
#         month: int,
#         day: int
#     ) -> Optional[float]:
#         """
#         Fetch precipitation with 6s timeout (realistic for S3 download)
#         Removed redundant nested timeouts
#         """
#         ds = None
#         try:
#             start_date = datetime(year, month, day)
#             end_date = start_date + timedelta(days=1)
            
#             # Search and open (2-3 seconds typical)
#             results = await asyncio.to_thread(
#                 earthaccess.search_data,
#                 short_name='GPM_3IMERGDF',
#                 temporal=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
#             )
            
#             if not results:
#                 return None
            
#             files = await asyncio.to_thread(earthaccess.open, results)
#             if not files:
#                 return None
            
#             # Open dataset with minimal overhead
#             ds = xr.open_dataset(
#                 files[0],
#                 chunks={'time': 1},
#                 decode_cf=False,
#                 cache=False
#             )
            
#             # Quick point extraction (1-2 seconds)
#             precip_data = ds['precipitation']
#             point_data = precip_data.sel(lat=lat, lon=lon, method='nearest')
#             precip_mm = float(point_data.compute().values)
            
#             return precip_mm
            
#         except Exception as e:
#             logger.debug(f"IMERG fetch failed: {e}")
#             return None
            
#         finally:
#             if ds is not None:
#                 try:
#                     ds.close()
#                 except:
#                     pass
    
#     async def _fetch_merra2_data(
#         self,
#         lat: float,
#         lon: float,
#         year: int,
#         month: int,
#         day: int
#     ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
#         """
#         Fetch MERRA-2 with 6s timeout (realistic for S3 download)
#         """
#         ds = None
#         try:
#             start_date = datetime(year, month, day)
#             end_date = start_date + timedelta(days=1)
            
#             # Search and open
#             results = await asyncio.to_thread(
#                 earthaccess.search_data,
#                 short_name='M2T1NXSLV',
#                 temporal=(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")),
#             )
            
#             if not results:
#                 return None, None, None
            
#             files = await asyncio.to_thread(earthaccess.open, results)
#             if not files:
#                 return None, None, None
            
#             # Open with minimal overhead
#             ds = xr.open_dataset(
#                 files[0],
#                 chunks={'time': 1},
#                 decode_cf=False,
#                 cache=False
#             )
            
#             # Quick point extraction
#             data = ds[['T2M', 'U10M', 'V10M']].sel(
#                 lat=lat,
#                 lon=lon,
#                 method='nearest',
#                 drop=True
#             )
            
#             computed = await asyncio.to_thread(data.compute)
            
#             temp_kelvin = computed['T2M'].values
#             u_values = computed['U10M'].values
#             v_values = computed['V10M'].values
            
#             temp_max_c = float(np.max(temp_kelvin)) - 273.15
#             temp_min_c = float(np.min(temp_kelvin)) - 273.15
#             wind_speeds = np.sqrt(u_values**2 + v_values**2)
#             windspeed_ms = float(np.mean(wind_speeds))
            
#             return temp_max_c, temp_min_c, windspeed_ms
            
#         except Exception as e:
#             logger.debug(f"MERRA-2 fetch failed: {e}")
#             return None, None, None
            
#         finally:
#             if ds is not None:
#                 try:
#                     ds.close()
#                 except:
#                     pass


# ============================================================================
# LAYER 2: NASA POWER API (FALLBACK)
# ============================================================================

class POWERService:
    """
    Layer 2: Instant, reliable pre-aggregated climatology
    Single API call returns all data in <1 second
    """
    
    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
    
    async def fetch(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int = 10
    ) -> LayerResponse:
        """
        Fetch from POWER API with timing
        Returns instant climatology data
        FIX: Use time.time() for accurate timing measurement
        """
        start_time = time.time()
        
        try:
            data = await self._fetch_power_data(lat, lon, month, day, years_back)
            elapsed_ms = (time.time() - start_time) * 1000
            
            return LayerResponse(
                data=data,
                source="NASA POWER API (Climatology)",
                timing_ms=elapsed_ms,
                success=True
            )
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Layer 2 error: {e}")
            return LayerResponse(
                data=[],
                source="NASA POWER API (Climatology)",
                timing_ms=elapsed_ms,
                success=False,
                error=str(e)
            )
    
    async def _fetch_power_data(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int = 10  # FIX: Add default value for tests
    ) -> List[WeatherData]:
        """
        Fetch from POWER API and filter by month/day
        Single API call for all years, then filter locally
        FIX 2: Handle both POWER API response structures
        """
        current_year = datetime.now().year
        start_year = current_year - years_back
        
        # Build API request
        params = {
            'latitude': lat,
            'longitude': lon,
            'start': f"{start_year}0101",
            'end': f"{current_year - 1}1231",
            'parameters': 'T2M_MAX,T2M_MIN,PRECTOTCORR,WS10M',
            'community': 'RE',
            'format': 'JSON'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as response:
                if response.status != 200:
                    raise Exception(f"POWER API returned {response.status}")
                
                data = await response.json()
        
        # FIX 2: Handle both possible POWER API response structures
        properties = data.get('properties', {})
        
        # Try both structures - some POWER API versions use 'parameter' nesting
        if 'parameter' in properties:
            # Structure 1: properties -> parameter -> variables
            parameters = properties.get('parameter', {})
            t2m_max = parameters.get('T2M_MAX', {})
            t2m_min = parameters.get('T2M_MIN', {})
            precip = parameters.get('PRECTOTCORR', {})
            windspeed = parameters.get('WS10M', {})
        else:
            # Structure 2: properties -> variables directly  
            t2m_max = properties.get('T2M_MAX', {})
            t2m_min = properties.get('T2M_MIN', {})
            precip = properties.get('PRECTOTCORR', {})
            windspeed = properties.get('WS10M', {})
        
        # Filter by month/day and create WeatherData objects
        weather_data = []
        for year in range(start_year, current_year):
            date_key = f"{year}{month:02d}{day:02d}"
            
            # FIX: Check if any data exists for this date
            if date_key in t2m_max or date_key in precip or date_key in windspeed:
                # Handle missing data gracefully by using available fields
                temp_max_val = float(t2m_max.get(date_key, 0.0))
                temp_min_val = float(t2m_min.get(date_key, 0.0))
                precip_val = float(precip.get(date_key, 0.0))
                windspeed_val = float(windspeed.get(date_key, 0.0))
                
                # Only add if we have at least some data
                if any([temp_max_val, temp_min_val, precip_val, windspeed_val]):
                    weather_data.append(WeatherData(
                        date=f"{year}-{month:02d}-{day:02d}",
                        temp_max=temp_max_val,
                        temp_min=temp_min_val,
                        precip=precip_val,
                        windspeed=windspeed_val
                    ))
        
        return weather_data

# ============================================================================
# LAYER 3: Response Logic & Mode Handling
# ============================================================================

class HybridOrchestrator:
    """
    Orchestrates the 3-layer hybrid architecture with smart timeouts
    """
    
    def __init__(self, earthdata_service: EarthdataService, power_service: POWERService):
        self.earthdata = earthdata_service
        self.power = power_service

    async def fetch(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        mode: FetchMode,
        years_back: int = 10
    ) -> Dict[str, Any]:
        """Main orchestration logic based on mode"""
        if mode == FetchMode.FAST:
            return await self._fetch_fast_mode(lat, lon, month, day, years_back)
        elif mode == FetchMode.PRECISE:
            return await self._fetch_precise_mode(lat, lon, month, day, years_back)
        else:  # HYBRID
            return await self._fetch_hybrid_mode(lat, lon, month, day, years_back)
    
    async def _fetch_fast_mode(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int
    ) -> Dict[str, Any]:
        """Fast mode: Layer 2 only (<1 second)"""
        logger.info("🚀 FAST mode: Using Layer 2 only")
        response = await self.power.fetch(lat, lon, month, day, years_back)
        return self._build_response(FetchMode.FAST, None, response)
    
    async def _fetch_precise_mode(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int
    ) -> Dict[str, Any]:
        """
        Precise mode: Try Layer 1 for up to 45s, then fallback to Layer 2
        User ALWAYS gets a response within 46 seconds
        """
        logger.info("🎯 PRECISE mode: Attempting Layer 1 (45s max)")
        
        # Create Layer 1 task
        layer1_task = asyncio.create_task(
            self.earthdata.fetch_with_timeout(
                lat, lon, month, day, years_back, timeout=25.0
            )
        )
        
        try:
            # Wait up to 45 seconds for Layer 1
            layer1_response = await asyncio.wait_for(layer1_task, timeout=45.0)
            
            if layer1_response.success and len(layer1_response.data) > 0:
                logger.info(f"✅ PRECISE: Layer 1 success with {len(layer1_response.data)} points in {layer1_response.timing_ms:.0f}ms")
                return self._build_response(FetchMode.PRECISE, layer1_response, None)
            else:
                logger.warning(f"⚠️ PRECISE: Layer 1 failed - {layer1_response.error}")
                layer1_failed_response = layer1_response
                
        except asyncio.TimeoutError:
            logger.warning("⏱️ PRECISE: Layer 1 timeout (45s) - using fallback")
            # Cancel the task
            layer1_task.cancel()
            try:
                await layer1_task
            except asyncio.CancelledError:
                pass
            
            layer1_failed_response = LayerResponse(
                data=[],
                source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
                timing_ms=45000,
                success=False,
                error="Timeout after 45 seconds"
            )
        
        # Fallback to Layer 2
        logger.info("🔄 PRECISE: Fetching Layer 2 fallback")
        layer2_response = await self.power.fetch(lat, lon, month, day, years_back)
        logger.info(f"✅ PRECISE: Using Layer 2 fallback ({layer2_response.timing_ms:.0f}ms)")
        
        return self._build_response(
            FetchMode.PRECISE,
            layer1_failed_response,
            layer2_response,
            fallback_used=True,
            fallback_reason=layer1_failed_response.error or "No data"
        )
    
    async def _fetch_hybrid_mode(
        self,
        lat: float,
        lon: float,
        month: int,
        day: int,
        years_back: int
    ) -> Dict[str, Any]:
        """
        Hybrid mode: Race strategy with timeout
        - Starts both layers immediately
        - Returns Layer 2 after ~1s
        - Waits up to 25s MORE for Layer 1
        - If Layer 1 succeeds in time, returns both (Layer 1 as primary)
        - If Layer 1 times out, returns Layer 2 data immediately
        """
        logger.info("🔀 HYBRID mode: Starting both layers")
        
        # Start both tasks in parallel
        layer1_task = asyncio.create_task(
            self.earthdata.fetch_with_timeout(
                lat, lon, month, day, years_back, timeout=25.0
            )
        )
        layer2_task = asyncio.create_task(
            self.power.fetch(lat, lon, month, day, years_back)
        )
        
        # Wait for Layer 2 (fast, <1s)
        layer2_response = await layer2_task
        logger.info(f"✅ HYBRID: Layer 2 ready in {layer2_response.timing_ms:.0f}ms")
        
        # Now race Layer 1 with a 25s timeout
        logger.info("⏳ HYBRID: Waiting for Layer 1 (25s max)...")
        try:
            layer1_response = await asyncio.wait_for(layer1_task, timeout=25.0)
            
            if layer1_response.success and len(layer1_response.data) > 0:
                logger.info(f"✅ HYBRID: Layer 1 success! {len(layer1_response.data)} points in {layer1_response.timing_ms:.0f}ms")
                logger.info("📊 HYBRID: Returning BOTH layers (Layer 1 as primary)")
            else:
                logger.warning(f"⚠️ HYBRID: Layer 1 failed - {layer1_response.error}")
                logger.info("📊 HYBRID: Returning both layers (Layer 2 as primary)")
                
        except asyncio.TimeoutError:
            # Layer 1 took too long - cancel it and return Layer 2
            logger.warning("⏱️ HYBRID: Layer 1 timeout (25s) - returning Layer 2")
            
            # Cancel Layer 1 task
            layer1_task.cancel()
            try:
                await layer1_task
            except asyncio.CancelledError:
                pass
            
            layer1_response = LayerResponse(
                data=[],
                source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
                timing_ms=25000,
                success=False,
                error="Timeout - exceeded 25s limit"
            )
            logger.info("📊 HYBRID: Returning Layer 2 only")
        
        # Always return both layer results
        return self._build_response(FetchMode.HYBRID, layer1_response, layer2_response)
    
    def _build_response(
        self,
        mode: FetchMode,
        layer1_result: Optional[LayerResponse],
        layer2_result: Optional[LayerResponse],
        fallback_used: bool = False,
        fallback_reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Unified response builder"""
        
        # Determine primary result (Layer 1 preferred if successful)
        if layer1_result and layer1_result.success and len(layer1_result.data) > 0:
            primary_result = layer1_result
            logger.info(f"📤 PRIMARY: Layer 1 ({len(layer1_result.data)} points)")
        elif layer2_result:
            primary_result = layer2_result
            logger.info(f"📤 PRIMARY: Layer 2 ({len(layer2_result.data)} points)")
        else:
            primary_result = layer1_result or layer2_result
            logger.warning("📤 PRIMARY: No valid data")
        
        if mode == FetchMode.HYBRID:
            return {
                "mode": mode.value,
                "layer1": {
                    "data": layer1_result.data if layer1_result else [],
                    "source": layer1_result.source if layer1_result else "NASA GPM IMERG + MERRA-2",
                    "timing_ms": layer1_result.timing_ms if layer1_result else 0,
                    "success": layer1_result.success if layer1_result else False,
                    "error": layer1_result.error if layer1_result else "Not executed",
                    "data_points": len(layer1_result.data) if layer1_result else 0
                },
                "layer2": {
                    "data": layer2_result.data if layer2_result else [],
                    "source": layer2_result.source if layer2_result else "NASA POWER API",
                    "timing_ms": layer2_result.timing_ms if layer2_result else 0,
                    "success": layer2_result.success if layer2_result else False,
                    "data_points": len(layer2_result.data) if layer2_result else 0
                },
                "comparison": self._compare_layers(layer1_result, layer2_result),
                "primary": {
                    "data": primary_result.data if primary_result else [],
                    "source": primary_result.source if primary_result else "No data",
                    "timing_ms": primary_result.timing_ms if primary_result else 0,
                    "success": primary_result.success if primary_result else False
                }
            }
        else:
            return {
                "mode": mode.value,
                "primary": {
                    "data": primary_result.data if primary_result else [],
                    "source": primary_result.source if primary_result else "No data",
                    "timing_ms": primary_result.timing_ms if primary_result else 0,
                    "success": primary_result.success if primary_result else False
                },
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason
            }
    
    def _compare_layers(
        self,
        layer1: Optional[LayerResponse],
        layer2: Optional[LayerResponse]
    ) -> Dict[str, Any]:
        """Compare Layer 1 and Layer 2 results"""
        if not (layer1 and layer1.success and layer2 and layer2.success):
            return {"available": False}
        
        if len(layer1.data) == 0 or len(layer2.data) == 0:
            return {"available": False}
        
        l1_precip = np.mean([d.precip for d in layer1.data])
        l2_precip = np.mean([d.precip for d in layer2.data])
        l1_temp = np.mean([d.temp_max for d in layer1.data])
        l2_temp = np.mean([d.temp_max for d in layer2.data])
        
        return {
            "available": True,
            "avg_precip_diff_mm": round(abs(l1_precip - l2_precip), 2),
            "avg_temp_diff_c": round(abs(l1_temp - l2_temp), 2),
            "data_points_l1": len(layer1.data),
            "data_points_l2": len(layer2.data)
        }
    
# class HybridOrchestrator:
#     """
#     Orchestrates the 3-layer hybrid architecture
#     Handles mode selection, parallel execution, and fallback logic
#     FIX 4: Unified response schema across all modes
#     """
    
#     def __init__(self, earthdata_service: EarthdataService, power_service: POWERService):
#         self.earthdata = earthdata_service
#         self.power = power_service

#     def _build_response(self, mode: FetchMode, layer1_result: Optional[LayerResponse], 
#                        layer2_result: Optional[LayerResponse], fallback_used: bool = False, 
#                        fallback_reason: Optional[str] = None) -> Dict[str, Any]:
#         """
#         Unified response builder for all modes
#         FIX 4: Consistent response structure across all fetch modes
#         """
#         # Determine primary result
#         primary_result = layer1_result if (layer1_result and layer1_result.success and len(layer1_result.data) > 0) else layer2_result
        
#         if mode == FetchMode.HYBRID:
#             return {
#                 "mode": mode.value,
#                 "layer1": {
#                     "data": layer1_result.data if layer1_result else [],
#                     "source": layer1_result.source if layer1_result else "NASA GPM IMERG + MERRA-2 (S3 Cloud)",
#                     "timing_ms": layer1_result.timing_ms if layer1_result else 0,
#                     "success": layer1_result.success if layer1_result else False,
#                     "error": layer1_result.error if layer1_result else "Not executed"
#                 } if layer1_result else None,
#                 "layer2": {
#                     "data": layer2_result.data if layer2_result else [],
#                     "source": layer2_result.source if layer2_result else "NASA POWER API (Climatology)",
#                     "timing_ms": layer2_result.timing_ms if layer2_result else 0,
#                     "success": layer2_result.success if layer2_result else False
#                 } if layer2_result else None,
#                 "comparison": self._compare_layers(layer1_result, layer2_result) if (layer1_result and layer2_result) else {"available": False},
#                 "primary": {
#                     "data": primary_result.data if primary_result else [],
#                     "source": primary_result.source if primary_result else "No data available",
#                     "timing_ms": primary_result.timing_ms if primary_result else 0,
#                     "success": primary_result.success if primary_result else False
#                 },
#                 "fallback_used": fallback_used,
#                 "fallback_reason": fallback_reason
#             }
#         else:
#             return {
#                 "mode": mode.value,
#                 "primary": {
#                     "data": primary_result.data if primary_result else [],
#                     "source": primary_result.source if primary_result else "No data available",
#                     "timing_ms": primary_result.timing_ms if primary_result else 0,
#                     "success": primary_result.success if primary_result else False
#                 },
#                 "fallback_used": fallback_used,
#                 "fallback_reason": fallback_reason
#             }
    
#     async def fetch(
#         self,
#         lat: float,
#         lon: float,
#         month: int,
#         day: int,
#         mode: FetchMode,
#         years_back: int = 10
#     ) -> Dict[str, Any]:
#         """
#         Main orchestration logic based on mode
#         FIX 4: Use unified response builder
#         """
#         if mode == FetchMode.FAST:
#             return await self._fetch_fast_mode(lat, lon, month, day, years_back)
#         elif mode == FetchMode.PRECISE:
#             return await self._fetch_precise_mode(lat, lon, month, day, years_back)
#         else:  # HYBRID
#             return await self._fetch_hybrid_mode(lat, lon, month, day, years_back)
    
#     async def _fetch_fast_mode(
#         self,
#         lat: float,
#         lon: float,
#         month: int,
#         day: int,
#         years_back: int
#     ) -> Dict[str, Any]:
#         """
#         Fast mode: Layer 2 only (<1 second, instant)
#         FIX 4: Use unified response builder
#         """
#         response = await self.power.fetch(lat, lon, month, day, years_back)
#         return self._build_response(FetchMode.FAST, None, response)
    
#     async def _fetch_precise_mode(
#         self,
#         lat: float,
#         lon: float,
#         month: int,
#         day: int,
#         years_back: int
#     ) -> Dict[str, Any]:
#         """
#         Precise mode: Wait up to 45s for Layer 1, fallback to Layer 2 if timeout
#         Ensures hard timeout and proper fallback
#         """
#         # Create Layer 1 task with timeout
#         layer1_task = asyncio.create_task(
#             self.earthdata.fetch_with_timeout(lat, lon, month, day, years_back, timeout=45.0)
#         )
        
#         try:
#             # Wait for Layer 1 with strict timeout
#             layer1_response = await asyncio.wait_for(layer1_task, timeout=45.0)
            
#             if layer1_response.success and len(layer1_response.data) > 0:
#                 logger.info("Layer 1 succeeded, using NASA Earthdata")
#                 return self._build_response(FetchMode.PRECISE, layer1_response, None)
                
#         except asyncio.TimeoutError:
#             logger.warning("Layer 1 exceeded 45s timeout, falling back to Layer 2")
#             # Cancel the Layer 1 task to clean up resources
#             layer1_task.cancel()
#             layer1_response = LayerResponse(success=False, error="Timeout after 45 seconds")
#         except Exception as e:
#             logger.error(f"Layer 1 failed with error: {str(e)}")
#             layer1_response = LayerResponse(success=False, error=str(e))
        
#         # Fallback to Layer 2
#         logger.info("Using Layer 2 fallback (POWER API)")
#         layer2_response = await self.power.fetch(lat, lon, month, day, years_back)
        
#         return self._build_response(
#             FetchMode.PRECISE, 
#             layer1_response, 
#             layer2_response, 
#             fallback_used=True, 
#             fallback_reason=layer1_response.error or "No data returned"
#         )
    
#     async def _fetch_hybrid_mode(
#         self,
#         lat: float,
#         lon: float,
#         month: int,
#         day: int,
#         years_back: int
#     ) -> Dict[str, Any]:
#         """
#         Hybrid mode: Run both in parallel, return both with comparison
#         FIX 4: Use unified response builder
#         """
#         # Run both layers in parallel
#         layer1_task = self.earthdata.fetch_with_timeout(
#             lat, lon, month, day, years_back, timeout=30.0
#         )
#         layer2_task = self.power.fetch(lat, lon, month, day, years_back)
        
#         layer1_response, layer2_response = await asyncio.gather(
#             layer1_task,
#             layer2_task,
#             return_exceptions=False
#         )
        
#         return self._build_response(FetchMode.HYBRID, layer1_response, layer2_response)
    
#     def _compare_layers(
#         self,
#         layer1: LayerResponse,
#         layer2: LayerResponse
#     ) -> Dict[str, Any]:
#         """
#         Compare Layer 1 and Layer 2 results
#         """
#         if not layer1.success or not layer2.success:
#             return {"available": False}
        
#         if len(layer1.data) == 0 or len(layer2.data) == 0:
#             return {"available": False}
        
#         # Calculate average differences
#         l1_precip = np.mean([d.precip for d in layer1.data])
#         l2_precip = np.mean([d.precip for d in layer2.data])
        
#         l1_temp = np.mean([d.temp_max for d in layer1.data])
#         l2_temp = np.mean([d.temp_max for d in layer2.data])
        
#         return {
#             "available": True,
#             "avg_precip_diff_mm": round(abs(l1_precip - l2_precip), 2),
#             "avg_temp_diff_c": round(abs(l1_temp - l2_temp), 2),
#             "data_points_l1": len(layer1.data),
#             "data_points_l2": len(layer2.data)
#         }

# ============================================================================
# Global Services
# ============================================================================

earthdata_service = None
power_service = None
orchestrator = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on app startup"""
    global earthdata_service, power_service, orchestrator
    
    try:
        # Initialize Layer 1 (Earthdata) - FIX 3: Graceful initialization
        earthdata_service = EarthdataService()
        earthdata_service.initialize_session()
        
        # Initialize Layer 2 (POWER)
        power_service = POWERService()
        
        # Initialize Layer 3 (Orchestrator)
        orchestrator = HybridOrchestrator(earthdata_service, power_service)
        
        logger.info("✓ All services initialized successfully")
        
    except Exception as e:
        logger.error(f"✗ Failed to initialize services: {e}")

# ============================================================================
# Probability Calculation
# ============================================================================

def calculate_probability(data: List[WeatherData], condition_func) -> float:
    """Calculate probability based on condition function"""
    if not data:
        return 0.0
    matching_count = sum(1 for item in data if condition_func(item))
    return matching_count / len(data)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "Will It Rain on My Parade? API (Hybrid NASA Data)",
        "version": "3.0.0",
        "architecture": "3-Layer Hybrid (Earthdata S3 + POWER API)",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "earthdata": earthdata_service.session_initialized if earthdata_service else False,
            "power": power_service is not None,
            "orchestrator": orchestrator is not None
        }
    }

@app.get("/probability/rain")
async def get_rain_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(0.1, ge=0, description="Rain threshold in mm"),
    mode: FetchMode = Query(FetchMode.HYBRID, description="Fetch mode: precise/fast/hybrid")
):
    """Calculate probability of rain"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Services not available")
    
    try:
        result = await orchestrator.fetch(lat, lon, month, day, mode)
        
        # FIX 1: Unified data extraction that works for ALL modes
        if "layer1" in result:  # HYBRID mode
            data = result["layer1"]["data"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["data"]
            source = result["layer1"]["source"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["source"]
        else:  # PRECISE or FAST mode
            data = result["primary"]["data"]
            source = result["primary"]["source"]
        
        probability = calculate_probability(data, lambda x: x.precip > threshold)
        
        response = {
            "probability": round(probability, 3),
            "source": source,
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "mode": mode.value
        }
        
        # Add mode-specific metadata
        if mode == FetchMode.HYBRID:
            response["layers"] = result
        elif mode == FetchMode.PRECISE and result.get("fallback_used"):
            response["fallback_used"] = True
            response["fallback_reason"] = result.get("fallback_reason")
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating rain probability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probability/heat")
async def get_heat_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(35.0, description="Heat threshold in Celsius"),
    mode: FetchMode = Query(FetchMode.HYBRID, description="Fetch mode: precise/fast/hybrid")
):
    """Calculate probability of very hot weather"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Services not available")
    
    try:
        result = await orchestrator.fetch(lat, lon, month, day, mode)
        
        # FIX 1: Unified data extraction that works for ALL modes
        if "layer1" in result:  # HYBRID mode
            data = result["layer1"]["data"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["data"]
            source = result["layer1"]["source"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["source"]
        else:  # PRECISE or FAST mode
            data = result["primary"]["data"]
            source = result["primary"]["source"]
        
        probability = calculate_probability(data, lambda x: x.temp_max > threshold)
        
        response = {
            "probability": round(probability, 3),
            "source": source,
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "mode": mode.value
        }
        
        if mode == FetchMode.HYBRID:
            response["layers"] = result
        elif mode == FetchMode.PRECISE and result.get("fallback_used"):
            response["fallback_used"] = True
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating heat probability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probability/cold")
async def get_cold_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(5.0, description="Cold threshold in Celsius"),
    mode: FetchMode = Query(FetchMode.HYBRID, description="Fetch mode: precise/fast/hybrid")
):
    """Calculate probability of very cold weather"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Services not available")
    
    try:
        result = await orchestrator.fetch(lat, lon, month, day, mode)
        
        # FIX 1: Unified data extraction that works for ALL modes
        if "layer1" in result:  # HYBRID mode
            data = result["layer1"]["data"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["data"]
            source = result["layer1"]["source"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["source"]
        else:  # PRECISE or FAST mode
            data = result["primary"]["data"]
            source = result["primary"]["source"]
        
        probability = calculate_probability(data, lambda x: x.temp_min < threshold)
        
        response = {
            "probability": round(probability, 3),
            "source": source,
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "mode": mode.value
        }
        
        if mode == FetchMode.HYBRID:
            response["layers"] = result
        elif mode == FetchMode.PRECISE and result.get("fallback_used"):
            response["fallback_used"] = True
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating cold probability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probability/wind")
async def get_wind_probability(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    threshold: float = Query(15.0, description="Wind threshold in m/s"),
    mode: FetchMode = Query(FetchMode.HYBRID, description="Fetch mode: precise/fast/hybrid")
):
    """Calculate probability of very windy weather"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Services not available")
    
    try:
        result = await orchestrator.fetch(lat, lon, month, day, mode)
        
        # FIX 1: Unified data extraction that works for ALL modes
        if "layer1" in result:  # HYBRID mode
            data = result["layer1"]["data"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["data"]
            source = result["layer1"]["source"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["source"]
        else:  # PRECISE or FAST mode
            data = result["primary"]["data"]
            source = result["primary"]["source"]
        
        probability = calculate_probability(data, lambda x: x.windspeed > threshold)
        
        response = {
            "probability": round(probability, 3),
            "source": source,
            "threshold": threshold,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "mode": mode.value
        }
        
        if mode == FetchMode.HYBRID:
            response["layers"] = result
        elif mode == FetchMode.PRECISE and result.get("fallback_used"):
            response["fallback_used"] = True
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating wind probability: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probability/all")
async def get_all_probabilities(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    day: int = Query(..., ge=1, le=31, description="Day (1-31)"),
    rain_threshold: float = Query(0.1, ge=0, description="Rain threshold in mm"),
    heat_threshold: float = Query(35.0, description="Heat threshold in Celsius"),
    cold_threshold: float = Query(5.0, description="Cold threshold in Celsius"),
    wind_threshold: float = Query(15.0, description="Wind threshold in m/s"),
    mode: FetchMode = Query(FetchMode.HYBRID, description="Fetch mode: precise/fast/hybrid")
):
    """Calculate all weather probabilities at once"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Services not available")
    
    try:
        result = await orchestrator.fetch(lat, lon, month, day, mode)
        
        # FIX 1: Unified data extraction that works for ALL modes
        if "layer1" in result:  # HYBRID mode
            data = result["layer1"]["data"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["data"]
            source = result["layer1"]["source"] if result["layer1"]["success"] and len(result["layer1"]["data"]) > 0 else result["layer2"]["source"]
        else:  # PRECISE or FAST mode
            data = result["primary"]["data"]
            source = result["primary"]["source"]
        
        # Calculate all probabilities
        rain_prob = calculate_probability(data, lambda x: x.precip > rain_threshold)
        heat_prob = calculate_probability(data, lambda x: x.temp_max > heat_threshold)
        cold_prob = calculate_probability(data, lambda x: x.temp_min < cold_threshold)
        wind_prob = calculate_probability(data, lambda x: x.windspeed > wind_threshold)
        
        response = {
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
            "source": source,
            "data_points": len(data),
            "location": {"lat": lat, "lon": lon},
            "date": {"month": month, "day": day},
            "mode": mode.value,
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
        
        # Add mode-specific metadata
        if mode == FetchMode.HYBRID:
            response["layers"] = result
        elif mode == FetchMode.PRECISE and result.get("fallback_used"):
            response["fallback_used"] = True
            response["fallback_reason"] = result.get("fallback_reason")
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating all probabilities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)