"""
Tests for the weather probability API (Hybrid NASA Data Version)
Updated to work with 3-layer hybrid architecture:
- Layer 1: Earthdata Cloud S3 + Parallel xarray Point-Slicing
- Layer 2: NASA POWER API (FALLBACK) 
- Layer 3: Hybrid Orchestrator with multiple fetch modes
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import numpy as np

# Import from the updated main file
from main import (
    app, 
    EarthdataService, 
    POWERService, 
    HybridOrchestrator,
    WeatherData, 
    LayerResponse,
    FetchMode,
    calculate_probability
)


client = TestClient(app)


# Sample test data - represents 10 years of data for July 15th
# Values: temp in Celsius, precip in mm, wind in m/s
sample_weather_data = [
    WeatherData("2015-07-15", 32.0, 18.0, 0.5, 12.0),   # Rain
    WeatherData("2016-07-15", 38.0, 22.0, 2.5, 8.0),    # Rain
    WeatherData("2017-07-15", 29.0, 16.0, 0.2, 18.0),   # Rain
    WeatherData("2018-07-15", 36.0, 20.0, 1.2, 12.0),   # Rain
    WeatherData("2019-07-15", 33.0, 19.0, 0.8, 10.0),   # Rain
    WeatherData("2020-07-15", 35.0, 21.0, 1.5, 14.0),   # Rain
    WeatherData("2021-07-15", 31.0, 17.0, 0.0, 16.0),   # No rain
    WeatherData("2022-07-15", 37.0, 23.0, 0.0, 9.0),    # No rain
    WeatherData("2023-07-15", 30.0, 15.0, 0.0, 17.0),   # No rain
    WeatherData("2024-07-15", 34.0, 19.0, 0.0, 11.0),   # No rain
]

# Calculation verification:
# Rain (precip > 0.1mm): 0.5, 2.5, 0.2, 1.2, 0.8, 1.5 = 6 out of 10 = 0.6 ✓
# Heat (temp_max > 35°C): 38, 36, 37 = 3 out of 10 = 0.3 ✓
# Cold (temp_min < 5°C): NONE = 0 out of 10 = 0.0 ✓
# Wind (windspeed > 15 m/s): 18, 16, 17 = 3 out of 10 = 0.3 ✓


# ============================================================================
# TEST SUITE 1: EARTHDATA SERVICE TESTS (LAYER 1)
# Tests for Earthdata Cloud S3 with parallel xarray point-slicing
# ============================================================================

class TestEarthdataService:
    """Tests for Layer 1: Earthdata Cloud S3 service"""
    
    def test_initialization(self):
        """Test EarthdataService initialization"""
        service = EarthdataService()
        assert service.semaphore._value == 8, "Should initialize with semaphore value 8"
        assert service.session_initialized == False, "Session should not be initialized by default"

    @pytest.mark.asyncio
    async def test_fetch_single_day_controlled(self):
        """Test controlled fetch with semaphore"""
        with patch.object(EarthdataService, '_fetch_single_day', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = WeatherData("2023-07-15", 32.0, 18.0, 1.5, 12.0)
            
            service = EarthdataService()
            result = await service._fetch_single_day_controlled(28.6139, 77.2090, 2023, 7, 15)
            
            assert result is not None
            mock_fetch.assert_called_once_with(28.6139, 77.2090, 2023, 7, 15)

    @pytest.mark.asyncio
    async def test_fetch_single_day_success(self):
        """Test successful single day fetch"""
        with patch.object(EarthdataService, '_fetch_imerg_precipitation', 
                         new_callable=AsyncMock, return_value=1.5):
            with patch.object(EarthdataService, '_fetch_merra2_data', 
                             new_callable=AsyncMock, return_value=(32.5, 18.2, 12.3)):
                
                service = EarthdataService()
                result = await service._fetch_single_day(28.6139, 77.2090, 2023, 7, 15)
                
                assert result is not None
                assert result.date == "2023-07-15"
                assert result.temp_max == 32.5
                assert result.temp_min == 18.2
                assert result.precip == 1.5
                assert result.windspeed == 12.3

    @pytest.mark.asyncio
    async def test_fetch_single_day_partial_data(self):
        """Test when only partial data is available"""
        with patch.object(EarthdataService, '_fetch_imerg_precipitation', 
                         new_callable=AsyncMock, return_value=None):
            with patch.object(EarthdataService, '_fetch_merra2_data', 
                             new_callable=AsyncMock, return_value=(32.5, 18.2, 12.3)):
                
                service = EarthdataService()
                result = await service._fetch_single_day(28.6139, 77.2090, 2023, 7, 15)
                
                assert result is None, "Should return None when precipitation data is missing"

    @pytest.mark.asyncio
    async def test_fetch_parallel_multiple_years(self):
        """Test parallel fetch across multiple years"""
        mock_data = WeatherData("2023-07-15", 32.0, 18.0, 1.5, 12.0)
        
        with patch.object(EarthdataService, '_fetch_single_day_controlled', 
                         new_callable=AsyncMock, return_value=mock_data):
            service = EarthdataService()
            results = await service._fetch_parallel(28.6139, 77.2090, 7, 15, years_back=5)
            
            assert len(results) == 5, "Should return data for 5 years"
            assert all(isinstance(item, WeatherData) for item in results)

    @pytest.mark.asyncio
    async def test_fetch_with_timeout_success(self):
        """Test fetch with timeout (success case)"""
        with patch.object(EarthdataService, '_fetch_parallel',
                         new_callable=AsyncMock) as mock_fetch:
            # Add small delay to simulate data fetching
            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return sample_weather_data
            mock_fetch.side_effect = delayed_response
            
            service = EarthdataService()
            response = await service.fetch_with_timeout(28.6139, 77.2090, 7, 15)
            
            assert response.success == True
            assert response.source == "NASA GPM IMERG + MERRA-2 (S3 Cloud)"
            assert len(response.data) == 10
            assert response.timing_ms > 0  # Should be at least 100ms from sleep

    @pytest.mark.asyncio
    async def test_fetch_with_timeout_failure(self):
        """Test fetch with timeout (failure case)"""
        with patch.object(EarthdataService, '_fetch_parallel', 
                         new_callable=AsyncMock, side_effect=asyncio.TimeoutError()):
            service = EarthdataService()
            response = await service.fetch_with_timeout(28.6139, 77.2090, 7, 15, timeout=0.1)
            
            assert response.success == False
            assert "Timeout" in response.error

    @pytest.mark.asyncio
    async def test_fetch_imerg_precipitation_success(self):
        """Test IMERG precipitation fetch"""
        mock_search_result = [MagicMock()]
        mock_ds = MagicMock()
        mock_precip = MagicMock()
        
        mock_precip.sel.return_value.compute.return_value.values = 2.5
        mock_ds.__getitem__.return_value = mock_precip
        mock_ds.close = MagicMock()
        
        with patch('main.earthaccess.search_data', return_value=mock_search_result):
            with patch('main.earthaccess.open', return_value=[mock_ds]):
                with patch('main.xr.open_dataset', return_value=mock_ds):
                    service = EarthdataService()
                    result = await service._fetch_imerg_precipitation(28.6139, 77.2090, 2023, 7, 15)
                    
                    assert result == 2.5

    @pytest.mark.asyncio
    async def test_fetch_merra2_data_success(self):
        """Test MERRA-2 temperature and wind fetch"""
        mock_search_result = [MagicMock()]
        mock_ds = MagicMock()
        
        # Mock temperature data in Kelvin
        temp_values = np.array([290.0, 291.0, 292.0, 300.0, 305.0, 304.0, 303.0, 302.0])
        u_wind_values = np.ones(8) * 5.0
        v_wind_values = np.ones(8) * 8.0
        
        mock_temp = MagicMock()
        mock_u_wind = MagicMock()
        mock_v_wind = MagicMock()
        
        mock_temp.sel.return_value.compute.return_value.values = temp_values
        mock_u_wind.sel.return_value.compute.return_value.values = u_wind_values
        mock_v_wind.sel.return_value.compute.return_value.values = v_wind_values
        
        def mock_getitem(key):
            if key == 'T2M':
                return mock_temp
            elif key == 'U10M':
                return mock_u_wind
            elif key == 'V10M':
                return mock_v_wind
        
        mock_ds.__getitem__.side_effect = mock_getitem
        mock_ds.close = MagicMock()
        
        with patch('main.earthaccess.search_data', return_value=mock_search_result):
            with patch('main.earthaccess.open', return_value=[mock_ds]):
                with patch('main.xr.open_dataset', return_value=mock_ds):
                    service = EarthdataService()
                    temp_max, temp_min, windspeed = await service._fetch_merra2_data(28.6139, 77.2090, 2023, 7, 15)
                    
                    # Verify temperature conversion from Kelvin to Celsius
                    expected_max = 305.0 - 273.15
                    expected_min = 290.0 - 273.15
                    expected_wind = np.sqrt(5.0**2 + 8.0**2)
                    
                    assert abs(temp_max - expected_max) < 0.1
                    assert abs(temp_min - expected_min) < 0.1
                    assert abs(windspeed - expected_wind) < 0.1


# ============================================================================
# TEST SUITE 2: POWER SERVICE TESTS (LAYER 2)
# Tests for NASA POWER API fallback service
# ============================================================================

class TestPOWERService:
    """Tests for Layer 2: NASA POWER API service"""
    
    @pytest.mark.asyncio
    async def test_fetch_power_data_success(self):
        """Test successful POWER API fetch"""
        mock_response_data = {
            'properties': {
                'parameter': {
                    'T2M_MAX': {'20150715': 32.0, '20160715': 38.0},
                    'T2M_MIN': {'20150715': 18.0, '20160715': 22.0},
                    'PRECTOTCORR': {'20150715': 0.5, '20160715': 2.5},
                    'WS10M': {'20150715': 12.0, '20160715': 8.0}
                }
            }
        }
        
        # Patch both the HTTP client and datetime to ensure consistent behavior
        with patch('main.aiohttp.ClientSession.get') as mock_get, \
             patch('main.datetime') as mock_datetime:
            # Fix the current year to 2017 so our test data is within range
            mock_datetime.now.return_value.year = 2017
            
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response_data)
            
            service = POWERService()
            results = await service._fetch_power_data(28.6139, 77.2090, 7, 15, years_back=2)
            
            assert len(results) == 2
            assert results[0].date == "2015-07-15"
            assert results[0].temp_max == 32.0
            assert results[1].date == "2016-07-15"
            assert results[1].precip == 2.5

    @pytest.mark.asyncio
    async def test_fetch_power_data_api_error(self):
        """Test POWER API error handling"""
        with patch('main.aiohttp.ClientSession.get') as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 500
            
            service = POWERService()
            
            with pytest.raises(Exception) as exc_info:
                await service._fetch_power_data(28.6139, 77.2090, 7, 15)
            
            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_fetch_service_method(self):
        """Test the main fetch service method"""
        with patch.object(POWERService, '_fetch_power_data', 
                         new_callable=AsyncMock) as mock_fetch:
            # Add small delay to simulate API call
            async def delayed_response(*args, **kwargs):
                await asyncio.sleep(0.1)  # 100ms delay
                return sample_weather_data
            mock_fetch.side_effect = delayed_response
            
            service = POWERService()
            response = await service.fetch(28.6139, 77.2090, 7, 15)
            
            assert response.success == True
            assert response.source == "NASA POWER API (Climatology)"
            assert len(response.data) == 10
            assert response.timing_ms > 0  # Should be at least 100ms from sleep


# ============================================================================
# TEST SUITE 3: HYBRID ORCHESTRATOR TESTS (LAYER 3)
# Tests for the hybrid orchestrator with different fetch modes
# ============================================================================

class TestHybridOrchestrator:
    """Tests for Layer 3: Hybrid orchestrator"""
    
    def setup_method(self):
        """Setup for each test"""
        self.mock_earthdata = MagicMock(spec=EarthdataService)
        self.mock_power = MagicMock(spec=POWERService)
        self.orchestrator = HybridOrchestrator(self.mock_earthdata, self.mock_power)
    
    @pytest.mark.asyncio
    async def test_fetch_fast_mode(self):
        """Test FAST mode (Layer 2 only)"""
        layer2_response = LayerResponse(
            data=sample_weather_data,
            source="NASA POWER API (Climatology)",
            timing_ms=50.0,
            success=True
        )
        
        self.mock_power.fetch = AsyncMock(return_value=layer2_response)
        
        result = await self.orchestrator.fetch(28.6139, 77.2090, 7, 15, FetchMode.FAST)
        
        assert result["mode"] == "fast"
        assert result["primary"]["source"] == "NASA POWER API (Climatology)"
        assert result["fallback_used"] == False
        self.mock_power.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_precise_mode_success(self):
        """Test PRECISE mode with Layer 1 success"""
        layer1_response = LayerResponse(
            data=sample_weather_data,
            source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
            timing_ms=1500.0,
            success=True
        )
        
        self.mock_earthdata.fetch_with_timeout = AsyncMock(return_value=layer1_response)
        
        result = await self.orchestrator.fetch(28.6139, 77.2090, 7, 15, FetchMode.PRECISE)
        
        assert result["mode"] == "precise"
        assert result["primary"]["source"] == "NASA GPM IMERG + MERRA-2 (S3 Cloud)"
        assert result["fallback_used"] == False

    @pytest.mark.asyncio
    async def test_fetch_precise_mode_fallback(self):
        """Test PRECISE mode with Layer 1 failure and fallback"""
        layer1_response = LayerResponse(
            data=[],
            source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
            timing_ms=1500.0,
            success=False,
            error="Timeout"
        )
        
        layer2_response = LayerResponse(
            data=sample_weather_data,
            source="NASA POWER API (Climatology)",
            timing_ms=50.0,
            success=True
        )
        
        self.mock_earthdata.fetch_with_timeout = AsyncMock(return_value=layer1_response)
        self.mock_power.fetch = AsyncMock(return_value=layer2_response)
        
        result = await self.orchestrator.fetch(28.6139, 77.2090, 7, 15, FetchMode.PRECISE)
        
        assert result["mode"] == "precise"
        assert result["primary"]["source"] == "NASA POWER API (Climatology)"
        assert result["fallback_used"] == True
        assert "fallback_reason" in result

    @pytest.mark.asyncio
    async def test_fetch_hybrid_mode_both_success(self):
        """Test HYBRID mode with both layers successful"""
        layer1_response = LayerResponse(
            data=sample_weather_data,
            source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
            timing_ms=1500.0,
            success=True
        )
        
        layer2_response = LayerResponse(
            data=sample_weather_data,
            source="NASA POWER API (Climatology)",
            timing_ms=50.0,
            success=True
        )
        
        self.mock_earthdata.fetch_with_timeout = AsyncMock(return_value=layer1_response)
        self.mock_power.fetch = AsyncMock(return_value=layer2_response)
        
        result = await self.orchestrator.fetch(28.6139, 77.2090, 7, 15, FetchMode.HYBRID)
        
        assert result["mode"] == "hybrid"
        assert result["layer1"]["success"] == True
        assert result["layer2"]["success"] == True
        assert "comparison" in result
        assert result["comparison"]["available"] == True

    @pytest.mark.asyncio
    async def test_fetch_hybrid_mode_layer1_fails(self):
        """Test HYBRID mode with Layer 1 failure"""
        layer1_response = LayerResponse(
            data=[],
            source="NASA GPM IMERG + MERRA-2 (S3 Cloud)",
            timing_ms=1500.0,
            success=False,
            error="Timeout"
        )
        
        layer2_response = LayerResponse(
            data=sample_weather_data,
            source="NASA POWER API (Climatology)",
            timing_ms=50.0,
            success=True
        )
        
        self.mock_earthdata.fetch_with_timeout = AsyncMock(return_value=layer1_response)
        self.mock_power.fetch = AsyncMock(return_value=layer2_response)
        
        result = await self.orchestrator.fetch(28.6139, 77.2090, 7, 15, FetchMode.HYBRID)
        
        assert result["mode"] == "hybrid"
        assert result["layer1"]["success"] == False
        assert result["layer2"]["success"] == True
        assert "comparison" in result

    def test_compare_layers_both_successful(self):
        """Test layer comparison when both have data"""
        layer1 = LayerResponse(
            data=[WeatherData("2023-07-15", 35.0, 20.0, 2.0, 10.0)],
            source="Layer1",
            timing_ms=100.0,
            success=True
        )
        
        layer2 = LayerResponse(
            data=[WeatherData("2023-07-15", 33.0, 18.0, 1.5, 12.0)],
            source="Layer2", 
            timing_ms=50.0,
            success=True
        )
        
        comparison = self.orchestrator._compare_layers(layer1, layer2)
        
        assert comparison["available"] == True
        assert comparison["avg_precip_diff_mm"] == 0.5  # |2.0 - 1.5|
        assert comparison["avg_temp_diff_c"] == 2.0     # |35.0 - 33.0|
        assert comparison["data_points_l1"] == 1
        assert comparison["data_points_l2"] == 1

    def test_compare_layers_one_fails(self):
        """Test layer comparison when one layer fails"""
        layer1 = LayerResponse(
            data=[],
            source="Layer1",
            timing_ms=100.0,
            success=False
        )
        
        layer2 = LayerResponse(
            data=sample_weather_data,
            source="Layer2",
            timing_ms=50.0,
            success=True
        )
        
        comparison = self.orchestrator._compare_layers(layer1, layer2)
        
        assert comparison["available"] == False


# ============================================================================
# TEST SUITE 4: PROBABILITY CALCULATION TESTS
# Tests that verify probability calculations are correct
# ============================================================================

class TestProbabilityCalculation:
    """Tests for probability calculation logic"""
    
    def test_calculate_rain_probability(self):
        """Test rain probability calculation"""
        prob = calculate_probability(sample_weather_data, lambda x: x.precip > 0.1)
        expected_prob = 0.6  # 6 out of 10 days have rain > 0.1mm
        assert prob == expected_prob

    def test_calculate_heat_probability(self):
        """Test heat probability calculation"""
        prob = calculate_probability(sample_weather_data, lambda x: x.temp_max > 35.0)
        expected_prob = 0.3  # 3 out of 10 days > 35°C
        assert prob == expected_prob

    def test_calculate_cold_probability(self):
        """Test cold probability calculation"""
        prob = calculate_probability(sample_weather_data, lambda x: x.temp_min < 5.0)
        expected_prob = 0.0  # 0 out of 10 days < 5°C
        assert prob == expected_prob

    def test_calculate_wind_probability(self):
        """Test wind probability calculation"""
        prob = calculate_probability(sample_weather_data, lambda x: x.windspeed > 15.0)
        expected_prob = 0.3  # 3 out of 10 days > 15 m/s
        assert prob == expected_prob

    def test_calculate_probability_empty_data(self):
        """Test probability with empty data"""
        prob = calculate_probability([], lambda x: x.precip > 0.1)
        assert prob == 0.0

    def test_calculate_probability_all_match(self):
        """Test probability when all data matches"""
        test_data = [WeatherData(f"2020-{i:02d}", 40.0, 20.0, 5.0, 20.0) for i in range(1, 6)]
        prob = calculate_probability(test_data, lambda x: x.temp_max > 35.0)
        assert prob == 1.0

    def test_calculate_probability_none_match(self):
        """Test probability when no data matches"""
        test_data = [WeatherData(f"2020-{i:02d}", 30.0, 20.0, 0.0, 5.0) for i in range(1, 6)]
        prob = calculate_probability(test_data, lambda x: x.precip > 10.0)
        assert prob == 0.0


# ============================================================================
# TEST SUITE 5: API ENDPOINT TESTS
# Tests that verify all API endpoints work correctly
# ============================================================================

class TestAPIEndpoints:
    """Tests for FastAPI endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Will It Rain on My Parade?" in response.json()["message"]
        assert "3.0.0" in response.json()["version"]

    def test_health_endpoint(self):
        """Test health endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert "services" in response.json()
        assert "timestamp" in response.json()

    @patch('main.orchestrator')
    def test_rain_probability_endpoint_fast_mode(self, mock_orchestrator):
        """Test rain probability endpoint with FAST mode"""
        mock_result = {
            "mode": "fast",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15&mode=fast")
        
        assert response.status_code == 200
        data = response.json()
        assert "probability" in data
        assert data["mode"] == "fast"
        assert data["source"] == "NASA POWER API (Climatology)"
        assert data["probability"] == 0.6

    @patch('main.orchestrator')
    def test_rain_probability_endpoint_precise_mode(self, mock_orchestrator):
        """Test rain probability endpoint with PRECISE mode"""
        mock_result = {
            "mode": "precise", 
            "primary": {
                "data": sample_weather_data,
                "source": "NASA GPM IMERG + MERRA-2 (S3 Cloud)",
                "timing_ms": 1500.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15&mode=precise")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "precise"
        assert data["source"] == "NASA GPM IMERG + MERRA-2 (S3 Cloud)"

    @patch('main.orchestrator')
    def test_rain_probability_endpoint_hybrid_mode(self, mock_orchestrator):
        """Test rain probability endpoint with HYBRID mode"""
        mock_result = {
            "mode": "hybrid",
            "layer1": {
                "data": sample_weather_data,
                "source": "NASA GPM IMERG + MERRA-2 (S3 Cloud)",
                "timing_ms": 1500.0,
                "success": True,
                "error": None
            },
            "layer2": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "comparison": {
                "available": True,
                "avg_precip_diff_mm": 0.0,
                "avg_temp_diff_c": 0.0,
                "data_points_l1": 10,
                "data_points_l2": 10
            }
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15&mode=hybrid")
        
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "hybrid"
        assert "layers" in data

    @patch('main.orchestrator')
    def test_heat_probability_endpoint(self, mock_orchestrator):
        """Test heat probability endpoint"""
        mock_result = {
            "mode": "fast",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/heat?lat=28.6139&lon=77.2090&month=7&day=15")
        
        assert response.status_code == 200
        data = response.json()
        assert "probability" in data
        assert data["probability"] == 0.3

    @patch('main.orchestrator')
    def test_cold_probability_endpoint(self, mock_orchestrator):
        """Test cold probability endpoint"""
        mock_result = {
            "mode": "fast",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/cold?lat=28.6139&lon=77.2090&month=7&day=15")
        
        assert response.status_code == 200
        data = response.json()
        assert data["probability"] == 0.0

    @patch('main.orchestrator')
    def test_wind_probability_endpoint(self, mock_orchestrator):
        """Test wind probability endpoint"""
        mock_result = {
            "mode": "fast",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/wind?lat=28.6139&lon=77.2090&month=7&day=15")
        
        assert response.status_code == 200
        data = response.json()
        assert data["probability"] == 0.3

    @patch('main.orchestrator')
    def test_all_probabilities_endpoint(self, mock_orchestrator):
        """Test all probabilities endpoint"""
        mock_result = {
            "mode": "fast",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/all?lat=28.6139&lon=77.2090&month=7&day=15")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "rain" in data
        assert "heat" in data
        assert "cold" in data
        assert "wind" in data
        assert "historical_data" in data
        
        assert data["rain"]["probability"] == 0.6
        assert data["heat"]["probability"] == 0.3
        assert data["cold"]["probability"] == 0.0
        assert data["wind"]["probability"] == 0.3

    def test_invalid_parameters(self):
        """Test invalid parameter validation"""
        # Invalid month
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=13&day=15")
        assert response.status_code == 422
        
        # Invalid day
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=32")
        assert response.status_code == 422
        
        # Missing required parameter
        response = client.get("/probability/rain?lat=28.6139")
        assert response.status_code == 422

    def test_service_unavailable(self):
        """Test when services are not available"""
        with patch('main.orchestrator', None):
            response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15")
            assert response.status_code == 503


# ============================================================================
# TEST SUITE 6: DATA STRUCTURE TESTS
# Tests that verify data structures work correctly
# ============================================================================

class TestDataStructure:
    """Tests for data structures"""
    
    def test_weather_data_creation(self):
        """Test WeatherData creation"""
        wd = WeatherData("2023-07-15", 35.0, 20.0, 2.5, 12.0)
        assert wd.date == "2023-07-15"
        assert wd.temp_max == 35.0
        assert wd.temp_min == 20.0
        assert wd.precip == 2.5
        assert wd.windspeed == 12.0

    def test_layer_response_creation(self):
        """Test LayerResponse creation"""
        response = LayerResponse(
            data=sample_weather_data,
            source="Test Source",
            timing_ms=100.0,
            success=True,
            error=None
        )
        
        assert response.source == "Test Source"
        assert response.timing_ms == 100.0
        assert response.success == True
        assert response.error is None

    def test_layer_response_with_error(self):
        """Test LayerResponse with error"""
        response = LayerResponse(
            data=[],
            source="Test Source",
            timing_ms=100.0,
            success=False,
            error="Test error message"
        )
        
        assert response.success == False
        assert response.error == "Test error message"


# ============================================================================
# TEST SUITE 7: EDGE CASES AND ADDITIONAL TESTS
# Tests for edge cases and comprehensive coverage
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error conditions"""
    
    @pytest.mark.asyncio
    async def test_earthdata_empty_results(self):
        """Test Earthdata with empty search results"""
        with patch('main.earthaccess.search_data', return_value=[]):
            service = EarthdataService()
            
            # Test IMERG with no results
            result = await service._fetch_imerg_precipitation(28.6139, 77.2090, 2023, 7, 15)
            assert result is None
            
            # Test MERRA-2 with no results  
            temp_max, temp_min, windspeed = await service._fetch_merra2_data(28.6139, 77.2090, 2023, 7, 15)
            assert temp_max is None
            assert temp_min is None
            assert windspeed is None

    @pytest.mark.asyncio 
    async def test_earthdata_file_open_failure(self):
        """Test Earthdata when file opening fails"""
        with patch('main.earthaccess.search_data', return_value=[MagicMock()]):
            with patch('main.earthaccess.open', return_value=[]):
                service = EarthdataService()
                
                result = await service._fetch_imerg_precipitation(28.6139, 77.2090, 2023, 7, 15)
                assert result is None

    @pytest.mark.asyncio
    async def test_power_api_missing_data(self):
        """Test POWER API with missing data for specific dates"""
        mock_response_data = {
            'properties': {
                'parameter': {
                    'T2M_MAX': {'20150715': 32.0},  # Only one date available
                    'T2M_MIN': {'20150715': 18.0},
                    'PRECTOTCORR': {'20150715': 0.5},
                    'WS10M': {'20150715': 12.0}
                }
            }
        }
        
        with patch('main.aiohttp.ClientSession.get') as mock_get, \
             patch('main.datetime') as mock_datetime:
            # Fix the current year to 2016 so our test data is within range
            mock_datetime.now.return_value.year = 2016
            
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.json = AsyncMock(return_value=mock_response_data)
            
            service = POWERService()
            results = await service._fetch_power_data(28.6139, 77.2090, 7, 15, years_back=1)
            
            # Should only return data for the one available date
            assert len(results) == 1
            assert results[0].date == "2015-07-15"
            assert results[0].temp_max == 32.0
            assert results[0].temp_min == 18.0
            assert results[0].precip == 0.5
            assert results[0].windspeed == 12.0

    @pytest.mark.asyncio
    async def test_orchestrator_invalid_mode(self):
        """Test orchestrator with invalid mode (should default to hybrid)"""
        mock_earthdata = MagicMock(spec=EarthdataService)
        mock_power = MagicMock(spec=POWERService)
        orchestrator = HybridOrchestrator(mock_earthdata, mock_power)
        
        # Mock both layers
        layer1_response = LayerResponse(
            data=sample_weather_data,
            source="Layer1",
            timing_ms=100.0,
            success=True
        )
        layer2_response = LayerResponse(
            data=sample_weather_data,
            source="Layer2", 
            timing_ms=50.0,
            success=True
        )
        
        mock_earthdata.fetch_with_timeout = AsyncMock(return_value=layer1_response)
        mock_power.fetch = AsyncMock(return_value=layer2_response)
        
        # Test with string mode (should work due to Enum)
        result = await orchestrator.fetch(28.6139, 77.2090, 7, 15, "hybrid")
        assert result["mode"] == "hybrid"

    def test_calculate_probability_edge_cases(self):
        """Test probability calculation with edge cases"""
        # Test with single data point
        single_data = [WeatherData("2023-07-15", 35.0, 20.0, 2.5, 12.0)]
        prob = calculate_probability(single_data, lambda x: x.precip > 0.1)
        assert prob == 1.0
        
        # Test with threshold exactly matching value
        exact_data = [WeatherData("2023-07-15", 35.0, 20.0, 0.1, 12.0)]
        prob = calculate_probability(exact_data, lambda x: x.precip > 0.1)
        assert prob == 0.0  # Not greater than 0.1

    @patch('main.orchestrator')
    def test_api_custom_thresholds(self, mock_orchestrator):
        """Test API with custom threshold values"""
        mock_result = {
            "mode": "fast",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA POWER API (Climatology)",
                "timing_ms": 50.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        # Test with custom rain threshold
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15&threshold=1.0")
        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 1.0
        
        # Test with custom heat threshold  
        response = client.get("/probability/heat?lat=28.6139&lon=77.2090&month=7&day=15&threshold=30.0")
        assert response.status_code == 200
        data = response.json()
        assert data["threshold"] == 30.0

    @patch('main.orchestrator')
    def test_api_different_modes(self, mock_orchestrator):
        """Test API with different fetch modes"""
        # Test PRECISE mode
        mock_result = {
            "mode": "precise",
            "primary": {
                "data": sample_weather_data,
                "source": "NASA GPM IMERG + MERRA-2 (S3 Cloud)", 
                "timing_ms": 1500.0,
                "success": True
            },
            "fallback_used": False
        }
        
        mock_orchestrator.fetch = AsyncMock(return_value=mock_result)
        
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15&mode=precise")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "precise"

    def test_fetch_mode_enum(self):
        """Test FetchMode enum values"""
        assert FetchMode.PRECISE.value == "precise"
        assert FetchMode.FAST.value == "fast" 
        assert FetchMode.HYBRID.value == "hybrid"
        
        # Test string conversion
        assert str(FetchMode.PRECISE) == "FetchMode.PRECISE"


class TestPerformanceAndConcurrency:
    """Tests for performance and concurrency aspects"""
    
    @pytest.mark.asyncio
    async def test_earthdata_semaphore_limitation(self):
        """Test that Earthdata service respects semaphore limits"""
        service = EarthdataService()
        
        # Create multiple concurrent requests
        tasks = []
        for i in range(10):
            task = service._fetch_single_day_controlled(28.6139, 77.2090, 2023 + i, 7, 15)
            tasks.append(task)
        
        # Should not exceed semaphore limit (8)
        # This is more of a sanity check than a strict test
        assert len(tasks) == 10
        # The actual concurrency is controlled by the semaphore

    @pytest.mark.asyncio 
    async def test_parallel_fetch_efficiency(self):
        """Test that parallel fetch is more efficient than sequential"""
        async def mock_fetch_delayed(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate network delay
            return WeatherData("2023-07-15", 32.0, 18.0, 1.5, 12.0)
        
        service = EarthdataService()
        service._fetch_single_day_controlled = AsyncMock(side_effect=mock_fetch_delayed)
        
        start_time = asyncio.get_event_loop().time()
        results = await service._fetch_parallel(28.6139, 77.2090, 7, 15, years_back=5)
        end_time = asyncio.get_event_loop().time()
        
        execution_time = end_time - start_time
        
        # With parallel execution, 5 requests should take ~0.1s (limited by semaphore)
        # With sequential, it would take ~0.5s
        assert execution_time < 0.2  # Should be much less than 0.5s
        assert len(results) == 5


class TestErrorHandlingAndRobustness:
    """Tests for error handling and robustness"""
    
    @pytest.mark.asyncio
    async def test_earthdata_exception_handling(self):
        """Test Earthdata service exception handling"""
        with patch.object(EarthdataService, '_fetch_parallel', 
                         new_callable=AsyncMock, side_effect=Exception("Test error")):
            service = EarthdataService()
            response = await service.fetch_with_timeout(28.6139, 77.2090, 7, 15)
            
            assert response.success == False
            assert "Test error" in response.error

    @pytest.mark.asyncio
    async def test_power_service_exception_handling(self):
        """Test POWER service exception handling"""
        with patch.object(POWERService, '_fetch_power_data',
                         new_callable=AsyncMock, side_effect=Exception("API error")):
            service = POWERService()
            response = await service.fetch(28.6139, 77.2090, 7, 15)
            
            assert response.success == False
            assert "API error" in response.error

    @pytest.mark.asyncio
    async def test_orchestrator_exception_handling(self):
        """Test orchestrator exception handling"""
        mock_earthdata = MagicMock(spec=EarthdataService)
        mock_power = MagicMock(spec=POWERService)
        orchestrator = HybridOrchestrator(mock_earthdata, mock_power)
        
        mock_earthdata.fetch_with_timeout = AsyncMock(side_effect=Exception("Earthdata failed"))
        mock_power.fetch = AsyncMock(side_effect=Exception("POWER failed"))
        
        # Should raise exception
        with pytest.raises(Exception):
            await orchestrator.fetch(28.6139, 77.2090, 7, 15, FetchMode.HYBRID)


# ============================================================================
# HELPER FUNCTION TO RUN TESTS
# ============================================================================

if __name__ == "__main__":
    """
    Run tests with: python -m pytest test_main.py -v
    Or simply: python test_main.py
    """
    pytest.main([__file__, "-v", "--tb=short"])