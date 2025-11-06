"""
Tests for the weather probability API (NASA Data Version)
Updated to work with NASAWeatherService using GPM IMERG and MERRA-2 data
Tests verify that backend is using NASA datasets instead of VisualCrossing
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from main import app, NASAWeatherService, WeatherData, calculate_probability
import numpy as np


client = TestClient(app)


# Sample test data - represents 10 years of data for July 15th
# IMPORTANT: These values are carefully chosen to match test expectations
# Data structure: (date, temp_max, temp_min, precip, windspeed)
# Values: temp in Celsius, precip in mm, wind in m/s
sample_weather_data = [
    WeatherData("2015-07-15", 32.0, 18.0, 0.0, 12.0),   # No rain (0.0)
    WeatherData("2016-07-15", 38.0, 22.0, 2.5, 8.0),    # Rain
    WeatherData("2017-07-15", 29.0, 16.0, 0.0, 18.0),   # No rain (0.0)
    WeatherData("2018-07-15", 36.0, 20.0, 1.2, 15.0),   # Rain
    WeatherData("2019-07-15", 33.0, 19.0, 0.0, 10.0),   # No rain (0.0)
    WeatherData("2020-07-15", 35.0, 21.0, 1.5, 14.0),   # Rain
    WeatherData("2021-07-15", 31.0, 17.0, 0.0, 16.0),   # No rain (0.0)
    WeatherData("2022-07-15", 37.0, 23.0, 2.1, 9.0),    # Rain
    WeatherData("2023-07-15", 30.0, 15.0, 0.0, 17.0),   # No rain (0.0)
    WeatherData("2024-07-15", 34.0, 19.0, 0.0, 11.0),   # No rain (0.0)
]

# Calculation verification:
# Rain (precip > 0.1mm): 2.5, 1.2, 1.5, 2.1 = 4 out of 10 = 0.4 (not 0.6)
# Actually let me recalculate: we want 6 days with rain > 0.1mm out of 10
# So we need to adjust - 6 rainy days and 4 dry days

sample_weather_data_corrected = [
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

# Corrected calculation verification:
# Rain (precip > 0.1mm): 0.5, 2.5, 0.2, 1.2, 0.8, 1.5 = 6 out of 10 = 0.6 ✓
# Heat (temp_max > 35°C): 38, 36, 37 = 3 out of 10 = 0.3 ✓
# Cold (temp_min < 5°C): NONE = 0 out of 10 = 0.0 ✓
# Wind (windspeed > 15 m/s): 18, 16, 17 = 3 out of 10 = 0.3 ✓

# Use corrected data
sample_weather_data = sample_weather_data_corrected


# ============================================================================
# TEST SUITE 1: NASA WEATHER SERVICE TESTS
# Tests that verify NASA data fetching works correctly
# ============================================================================

class TestNASAWeatherService:
    """
    Tests for NASAWeatherService class
    Verifies that data is correctly fetched from:
    - GPM IMERG (precipitation)
    - MERRA-2 (temperature and wind)
    """
    
    @pytest.mark.asyncio
    async def test_fetch_single_day_success(self):
        """
        Test: Can successfully fetch a single day of weather data from NASA
        Expected: Returns WeatherData with correct values from IMERG + MERRA-2
        """
        # Mock the NASA data sources
        with patch.object(NASAWeatherService, '_fetch_imerg_precipitation', 
                         new_callable=AsyncMock, return_value=1.5):
            with patch.object(NASAWeatherService, '_fetch_merra2_data', 
                             new_callable=AsyncMock, return_value=(32.5, 18.2, 12.3)):
                
                with patch('earthaccess.login'):
                    service = NASAWeatherService()
                    result = await service._fetch_single_day(28.6139, 77.2090, 2023, 7, 15)
                    
                    # Verify all fields are populated correctly
                    assert result is not None, "Single day fetch should return data"
                    assert result.date == "2023-07-15", "Date should be formatted as YYYY-MM-DD"
                    assert result.temp_max == 32.5, "Temperature max should come from MERRA-2"
                    assert result.temp_min == 18.2, "Temperature min should come from MERRA-2"
                    assert result.precip == 1.5, "Precipitation should come from GPM IMERG"
                    assert result.windspeed == 12.3, "Wind speed should come from MERRA-2"


    @pytest.mark.asyncio
    async def test_fetch_imerg_precipitation_success(self):
        """
        Test: GPM IMERG data fetching works correctly
        Expected: Returns precipitation value in millimeters
        """
        mock_search_result = [MagicMock()]
        mock_ds = MagicMock()
        mock_precip = MagicMock()
        
        # Mock the precipitation data
        mock_precip.sel.return_value.values = 2.5  # 2.5mm of rain
        mock_ds.__getitem__.return_value = mock_precip
        mock_ds.close = MagicMock()
        
        with patch('earthaccess.search_data', return_value=mock_search_result):
            with patch('earthaccess.open', return_value=[mock_ds]):
                with patch('xarray.open_dataset', return_value=mock_ds):
                    with patch('earthaccess.login'):
                        service = NASAWeatherService()
                        result = await service._fetch_imerg_precipitation(28.6139, 77.2090, 2023, 7, 15)
                        
                        assert result == 2.5, "Should return precipitation in mm"
                        assert isinstance(result, float), "Precipitation should be a float"


    @pytest.mark.asyncio
    async def test_fetch_imerg_no_data(self):
        """
        Test: Handle case when IMERG has no data for a date
        Expected: Returns None gracefully
        """
        with patch('earthaccess.search_data', return_value=[]):
            with patch('earthaccess.login'):
                service = NASAWeatherService()
                result = await service._fetch_imerg_precipitation(28.6139, 77.2090, 2000, 1, 1)
                
                assert result is None, "Should return None when no data found"


    @pytest.mark.asyncio
    async def test_fetch_merra2_data_success(self):
        """
        Test: MERRA-2 temperature and wind data fetching works correctly
        Expected: Returns tuple of (temp_max_C, temp_min_C, windspeed_ms)
        """
        mock_search_result = [MagicMock()]
        mock_ds = MagicMock()
        
        # Mock MERRA-2 data
        # T2M: Temperature in Kelvin (24 hourly values for a day)
        # Simulating: max ~305K (32°C), min ~291K (18°C)
        temp_values = np.array([291.15, 292.0, 293.5, 294.0, 292.5, 291.0, 290.0, 
                               295.0, 300.0, 305.0, 305.15, 304.0, 303.0, 302.0, 301.0,
                               300.0, 298.0, 296.0, 294.0, 293.0, 292.0, 291.5, 291.0, 290.5])
        
        # Wind components (U10M and V10M)
        u_wind_values = np.ones(24) * 5.0   # 5 m/s eastward
        v_wind_values = np.ones(24) * 8.0   # 8 m/s northward
        
        mock_temp = MagicMock()
        mock_u_wind = MagicMock()
        mock_v_wind = MagicMock()
        
        mock_temp.sel.return_value.values = temp_values
        mock_u_wind.sel.return_value.values = u_wind_values
        mock_v_wind.sel.return_value.values = v_wind_values
        
        def mock_getitem(key):
            if key == 'T2M':
                return mock_temp
            elif key == 'U10M':
                return mock_u_wind
            elif key == 'V10M':
                return mock_v_wind
        
        mock_ds.__getitem__.side_effect = mock_getitem
        mock_ds.close = MagicMock()
        
        with patch('earthaccess.search_data', return_value=mock_search_result):
            with patch('earthaccess.open', return_value=[mock_ds]):
                with patch('xarray.open_dataset', return_value=mock_ds):
                    with patch('earthaccess.login'):
                        service = NASAWeatherService()
                        temp_max, temp_min, windspeed = await service._fetch_merra2_data(28.6139, 77.2090, 2023, 7, 15)
                        
                        # Verify temperature conversion from Kelvin to Celsius
                        assert temp_max is not None, "Temperature max should be returned"
                        assert temp_min is not None, "Temperature min should be returned"
                        assert windspeed is not None, "Wind speed should be returned"
                        
                        # Max temp should be ~305K - 273.15 = ~31.85°C
                        assert temp_max > 31 and temp_max < 33, f"Max temp should be ~32°C, got {temp_max}"
                        
                        # Min temp should be ~290K - 273.15 = ~17.15°C
                        assert temp_min > 16 and temp_min < 19, f"Min temp should be ~18°C, got {temp_min}"
                        
                        # Wind speed: sqrt(5^2 + 8^2) = sqrt(89) ≈ 9.43 m/s
                        assert windspeed > 9 and windspeed < 10, f"Wind speed should be ~9.4 m/s, got {windspeed}"


    @pytest.mark.asyncio
    async def test_fetch_merra2_no_data(self):
        """
        Test: Handle case when MERRA-2 has no data
        Expected: Returns (None, None, None) gracefully
        """
        with patch('earthaccess.search_data', return_value=[]):
            with patch('earthaccess.login'):
                service = NASAWeatherService()
                temp_max, temp_min, windspeed = await service._fetch_merra2_data(28.6139, 77.2090, 2023, 7, 15)
                
                assert temp_max is None, "Should return None for temp_max when no data"
                assert temp_min is None, "Should return None for temp_min when no data"
                assert windspeed is None, "Should return None for windspeed when no data"


    




    @pytest.mark.asyncio
    async def test_fetch_historical_data_multiple_years(self):
        """
        Test: Can fetch historical data across multiple years
        Expected: Returns list of WeatherData for each year
        """
        mock_data = WeatherData("2023-07-15", 32.0, 18.0, 1.5, 12.0)
        
        with patch.object(NASAWeatherService, '_fetch_single_day', 
                         new_callable=AsyncMock, return_value=mock_data):
            with patch('earthaccess.login'):
                service = NASAWeatherService()
                result = await service.fetch_historical_data(28.6139, 77.2090, 7, 15, years_back=5)
                
                assert len(result) >= 1, "Should return at least one year of data"
                assert all(isinstance(item, WeatherData) for item in result), "All items should be WeatherData"
                assert all(item.date.startswith("20") for item in result), "All dates should be valid"


# ============================================================================
# TEST SUITE 2: PROBABILITY CALCULATION TESTS
# Tests that verify probability calculations are correct
# ============================================================================

class TestProbabilityCalculation:
    """
    Tests for probability calculation logic
    Verifies that weather probabilities are calculated correctly from data
    """
    
    def test_calculate_rain_probability(self):
        """
        Test: Calculate probability of rain (precip > 0.1mm)
        Expected: 6 out of 10 days have rain > 0.1mm = 0.6 probability
        
        Data breakdown:
        - 0.5mm (YES), 2.5mm (YES), 0.2mm (YES), 1.2mm (YES), 0.8mm (YES), 
          1.5mm (YES), 0.0mm (NO), 0.0mm (NO), 0.0mm (NO), 0.0mm (NO)
        - Count: 6 YES out of 10 = 0.6 probability
        """
        prob = calculate_probability(sample_weather_data, lambda x: x.precip > 0.1)
        
        expected_prob = 0.6
        assert prob == expected_prob, f"Expected {expected_prob}, got {prob}"


    def test_calculate_heat_probability(self):
        """
        Test: Calculate probability of extreme heat (temp_max > 35°C)
        Expected: 3 out of 10 days > 35°C = 0.3 probability
        
        Data breakdown:
        - 32 (NO), 38 (YES), 29 (NO), 36 (YES), 33 (NO), 
          35 (NO), 31 (NO), 37 (YES), 30 (NO), 34 (NO)
        - Count: 3 YES (38, 36, 37) out of 10 = 0.3 probability
        """
        prob = calculate_probability(sample_weather_data, lambda x: x.temp_max > 35.0)
        
        expected_prob = 0.3
        assert prob == expected_prob, f"Expected {expected_prob}, got {prob}"


    def test_calculate_cold_probability(self):
        """
        Test: Calculate probability of extreme cold (temp_min < 5°C)
        Expected: 0 out of 10 days < 5°C = 0.0 probability
        
        Data breakdown:
        - All temp_min values are >= 15°C, so none are < 5°C
        - Count: 0 YES out of 10 = 0.0 probability
        """
        prob = calculate_probability(sample_weather_data, lambda x: x.temp_min < 5.0)
        
        expected_prob = 0.0
        assert prob == expected_prob, f"Expected {expected_prob}, got {prob}"


    def test_calculate_wind_probability(self):
        """
        Test: Calculate probability of strong wind (windspeed > 15 m/s)
        Expected: 3 out of 10 days > 15 m/s = 0.3 probability
        
        Data breakdown:
        - 12 (NO), 8 (NO), 18 (YES), 12 (NO), 10 (NO), 
          14 (NO), 16 (YES), 9 (NO), 17 (YES), 11 (NO)
        - Count: 3 YES (18, 16, 17) out of 10 = 0.3 probability
        """
        prob = calculate_probability(sample_weather_data, lambda x: x.windspeed > 15.0)
        
        expected_prob = 0.3
        assert prob == expected_prob, f"Expected {expected_prob}, got {prob}"


    def test_calculate_probability_empty_data(self):
        """
        Test: Handle empty data gracefully
        Expected: Returns 0.0 probability
        """
        prob = calculate_probability([], lambda x: x.precip > 0.1)
        assert prob == 0.0, "Empty data should return 0.0 probability"


    def test_calculate_probability_all_match(self):
        """
        Test: When all data matches condition
        Expected: Returns 1.0 probability
        """
        test_data = [WeatherData(f"2020-{i:02d}", 40.0, 20.0, 5.0, 20.0) for i in range(1, 6)]
        prob = calculate_probability(test_data, lambda x: x.temp_max > 35.0)
        
        assert prob == 1.0, "All matching data should return 1.0 probability"


    def test_calculate_probability_none_match(self):
        """
        Test: When no data matches condition
        Expected: Returns 0.0 probability
        """
        test_data = [WeatherData(f"2020-{i:02d}", 30.0, 20.0, 0.0, 5.0) for i in range(1, 6)]
        prob = calculate_probability(test_data, lambda x: x.precip > 10.0)
        
        assert prob == 0.0, "No matching data should return 0.0 probability"


# ============================================================================
# TEST SUITE 3: API ENDPOINT TESTS
# Tests that verify all API endpoints work correctly with NASA data
# ============================================================================

class TestAPIEndpoints:
    """
    Tests for FastAPI endpoints
    Verifies that API returns correct responses using NASA data
    """
    
    def test_root_endpoint(self):
        """
        Test: GET / endpoint
        Expected: Returns 200 OK with app info
        """
        response = client.get("/")
        
        assert response.status_code == 200, "Root endpoint should return 200 OK"
        assert "Will It Rain on My Parade?" in response.json()["message"]


    def test_health_endpoint(self):
        """
        Test: GET /health endpoint
        Expected: Returns 200 OK with healthy status
        """
        response = client.get("/health")
        
        assert response.status_code == 200, "Health endpoint should return 200 OK"
        assert response.json()["status"] == "healthy"


    @patch('main.weather_service')
    def test_rain_probability_endpoint(self, mock_service):
        """
        Test: GET /probability/rain endpoint with NASA data
        Expected: Returns rain probability with NASA GPM IMERG source
        """
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15&threshold=1")
        
        assert response.status_code == 200, "Rain endpoint should return 200 OK"
        
        data = response.json()
        assert "probability" in data, "Response should contain probability"
        assert "source" in data, "Response should contain data source"
        # CRITICAL: Verify it's using NASA data, not VisualCrossing
        assert data["source"] == "NASA GPM IMERG", f"Source should be NASA GPM IMERG, got {data['source']}"
        assert data["threshold"] == 1, "Threshold should match request"
        assert data["data_points"] > 0, "Should have data points"


    @patch('main.weather_service')
    def test_heat_probability_endpoint(self, mock_service):
        """
        Test: GET /probability/heat endpoint with NASA data
        Expected: Returns heat probability with NASA MERRA-2 source
        """
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/heat?lat=28.6139&lon=77.2090&month=7&day=15&threshold=30")
        
        assert response.status_code == 200, "Heat endpoint should return 200 OK"
        
        data = response.json()
        assert "probability" in data, "Response should contain probability"
        assert data["threshold"] == 30, "Threshold should match request"
        # CRITICAL: Verify it's using NASA MERRA-2 data
        assert data["source"] == "NASA MERRA-2", f"Source should be NASA MERRA-2, got {data['source']}"


    @patch('main.weather_service')
    def test_cold_probability_endpoint(self, mock_service):
        """
        Test: GET /probability/cold endpoint with NASA data
        Expected: Returns cold probability with NASA MERRA-2 source
        """
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/cold?lat=28.6139&lon=77.2090&month=7&day=15&threshold=5")
        
        assert response.status_code == 200, "Cold endpoint should return 200 OK"
        
        data = response.json()
        assert "probability" in data, "Response should contain probability"
        # CRITICAL: Verify it's using NASA data
        assert data["source"] == "NASA MERRA-2", f"Source should be NASA MERRA-2, got {data['source']}"


    @patch('main.weather_service')
    def test_wind_probability_endpoint(self, mock_service):
        """
        Test: GET /probability/wind endpoint with NASA data
        Expected: Returns wind probability with NASA MERRA-2 source
        """
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/wind?lat=28.6139&lon=77.2090&month=7&day=15&threshold=15")
        
        assert response.status_code == 200, "Wind endpoint should return 200 OK"
        
        data = response.json()
        assert "probability" in data, "Response should contain probability"
        assert data["threshold"] == 15, "Threshold should match request"
        # CRITICAL: Verify it's using NASA data
        assert data["source"] == "NASA MERRA-2", f"Source should be NASA MERRA-2, got {data['source']}"


    @patch('main.weather_service')
    def test_all_probabilities_endpoint(self, mock_service):
        """
        Test: GET /probability/all endpoint
        Expected: Returns all weather probabilities with NASA data sources
        """
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/all?lat=28.6139&lon=77.2090&month=7&day=15")
        
        assert response.status_code == 200, "All probabilities endpoint should return 200 OK"
        
        data = response.json()
        assert "rain" in data, "Should have rain probability"
        assert "heat" in data, "Should have heat probability"
        assert "cold" in data, "Should have cold probability"
        assert "wind" in data, "Should have wind probability"
        assert "historical_data" in data, "Should have historical data"
        
        # CRITICAL: Verify it's using NASA combined data
        assert data["source"] == "NASA GPM IMERG + MERRA-2", f"Source should be NASA GPM IMERG + MERRA-2, got {data['source']}"
        
        # Verify historical data is included
        assert len(data["historical_data"]) > 0, "Should have historical data points"
        assert "temp_max" in data["historical_data"][0], "Historical data should have temp_max"
        assert "precip" in data["historical_data"][0], "Historical data should have precip"


    @patch('main.weather_service')
    def test_default_threshold_values(self, mock_service):
        """
        Test: Default threshold values are applied correctly
        Expected: Each endpoint has correct default threshold
        """
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        # Test rain endpoint default threshold (0.1mm)
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15")
        data = response.json()
        assert data["threshold"] == 0.1, "Default rain threshold should be 0.1mm"
        
        # Test heat endpoint default threshold (35°C)
        response = client.get("/probability/heat?lat=28.6139&lon=77.2090&month=7&day=15")
        data = response.json()
        assert data["threshold"] == 35.0, "Default heat threshold should be 35°C"
        
        # Test cold endpoint default threshold (5°C)
        response = client.get("/probability/cold?lat=28.6139&lon=77.2090&month=7&day=15")
        data = response.json()
        assert data["threshold"] == 5.0, "Default cold threshold should be 5°C"
        
        # Test wind endpoint default threshold (15 m/s)
        response = client.get("/probability/wind?lat=28.6139&lon=77.2090&month=7&day=15")
        data = response.json()
        assert data["threshold"] == 15.0, "Default wind threshold should be 15 m/s"


    def test_invalid_month_parameter(self):
        """
        Test: Invalid month parameter (month > 12)
        Expected: Returns 422 Validation Error
        """
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=13&day=15")
        
        assert response.status_code == 422, "Invalid month should return 422 validation error"


    def test_invalid_day_parameter(self):
        """
        Test: Invalid day parameter (day > 31)
        Expected: Returns 422 Validation Error
        """
        response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=32")
        
        assert response.status_code == 422, "Invalid day should return 422 validation error"


    def test_missing_required_parameter(self):
        """
        Test: Missing required parameter
        Expected: Returns 422 Validation Error
        """
        response = client.get("/probability/rain?lat=28.6139")
        
        assert response.status_code == 422, "Missing parameters should return 422 validation error"


    def test_service_unavailable(self):
        """
        Test: Weather service is not initialized
        Expected: Returns 503 Service Unavailable
        """
        with patch('main.weather_service', None):
            response = client.get("/probability/rain?lat=28.6139&lon=77.2090&month=7&day=15")
            
            assert response.status_code == 503, "Unavailable service should return 503"


# ============================================================================
# TEST SUITE 4: DATA STRUCTURE TESTS
# Tests that verify data structures are compatible with NASA data
# ============================================================================

class TestDataStructure:
    """
    Tests for WeatherData dataclass
    Verifies that data structure can hold NASA data correctly
    """
    
    def test_weather_data_creation(self):
        """
        Test: Create WeatherData object
        Expected: All fields are correctly assigned
        """
        wd = WeatherData("2023-07-15", 35.0, 20.0, 2.5, 12.0)
        
        assert wd.date == "2023-07-15"
        assert wd.temp_max == 35.0
        assert wd.temp_min == 20.0
        assert wd.precip == 2.5
        assert wd.windspeed == 12.0


    def test_weather_data_from_imerg(self):
        """
        Test: WeatherData with IMERG precipitation values
        Expected: Can store realistic IMERG precipitation (0-50mm)
        """
        # IMERG precipitation ranges from 0 to ~50mm on rainy days
        imerg_precip = 3.7  # mm of rain
        wd = WeatherData("2023-07-15", 32.0, 18.0, imerg_precip, 12.0)
        
        assert wd.precip == 3.7
        assert isinstance(wd.precip, float)


    def test_weather_data_from_merra2(self):
        """
        Test: WeatherData with MERRA-2 temperature and wind values
        Expected: Can store realistic MERRA-2 values in Celsius and m/s
        """
        # MERRA-2 data is provided in:
        # - Temperature: Celsius (after conversion from Kelvin)
        # - Wind speed: m/s (calculated from U10M and V10M)
        wd = WeatherData(
            date="2023-07-15",
            temp_max=32.5,      # Celsius from MERRA-2
            temp_min=18.2,      # Celsius from MERRA-2
            precip=2.5,         # mm from IMERG
            windspeed=9.5       # m/s from MERRA-2 (calculated from components)
        )
        
        assert isinstance(wd, WeatherData)
        assert wd.temp_max > wd.temp_min
        assert wd.precip >= 0
        assert wd.windspeed >= 0


    def test_weather_data_realistic_nasa_values(self):
        """
        Test: WeatherData with realistic NASA data ranges
        Expected: Can handle all valid NASA data ranges
        """
        # Realistic ranges from NASA data
        test_cases = [
            # (temp_max, temp_min, precip, windspeed, description)
            (50.0, 30.0, 0.0, 25.0, "Extreme heat, dry, windy"),
            (-20.0, -30.0, 5.0, 15.0, "Extreme cold, snow, moderate wind"),
            (25.0, 15.0, 0.5, 3.0, "Mild, light rain, calm"),
            (35.0, 20.0, 25.0, 20.0, "Hot, heavy rain, strong wind"),
            (0.0, -10.0, 0.0, 0.0, "Freezing, no rain, no wind"),
        ]
        
        for temp_max, temp_min, precip, windspeed, desc in test_cases:
            wd = WeatherData("2023-07-15", temp_max, temp_min, precip, windspeed)
            assert isinstance(wd, WeatherData), f"Should create WeatherData for: {desc}"


# ============================================================================
# HELPER FUNCTION TO RUN TESTS
# ============================================================================

if __name__ == "__main__":
    """
    Run tests with: python -m pytest test_main.py -v
    Or simply: python test_main.py
    """
    pytest.main([__file__, "-v", "--tb=short"])