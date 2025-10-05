"""
Tests for the weather probability API
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from main import app, WeatherService, WeatherData, calculate_probability
import httpx

client = TestClient(app)

# Sample test data
sample_weather_data = [
    WeatherData("2020-06-15", 32.0, 18.0, 0.0, 12.0),
    WeatherData("2021-06-15", 38.0, 22.0, 2.5, 8.0),
    WeatherData("2022-06-15", 29.0, 16.0, 0.0, 18.0),
    WeatherData("2023-06-15", 36.0, 20.0, 1.2, 15.0),
]

class TestWeatherService:
    @pytest.mark.asyncio
    async def test_fetch_single_day_success(self):
        """Test successful single day data fetch"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "days": [{
                "datetime": "2023-06-15",
                "tempmax": 32.5,
                "tempmin": 18.2,
                "precip": 1.5,
                "windspeed": 12.3
            }]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            
            service = WeatherService("test_key")
            result = await service._fetch_single_day(40.7128, -74.0060, "2023-06-15")
            
            assert result is not None
            assert result.date == "2023-06-15"
            assert result.temp_max == 32.5
            assert result.temp_min == 18.2
            assert result.precip == 1.5
            assert result.windspeed == 12.3

    @pytest.mark.asyncio
    async def test_fetch_single_day_error(self):
        """Test error handling in single day fetch"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.get = AsyncMock(side_effect=httpx.HTTPError("API Error"))
            
            service = WeatherService("test_key")
            result = await service._fetch_single_day(40.7128, -74.0060, "2023-06-15")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_fetch_historical_data(self):
        """Test fetching historical data for multiple years"""
        with patch.object(WeatherService, '_fetch_single_day') as mock_fetch:
            mock_fetch.return_value = sample_weather_data[0]
            
            service = WeatherService("test_key")
            result = await service.fetch_historical_data(40.7128, -74.0060, 6, 15, 2)
            
            assert len(result) == 2
            assert all(isinstance(item, WeatherData) for item in result)

class TestProbabilityCalculation:
    def test_calculate_rain_probability(self):
        """Test rain probability calculation"""
        # 2 out of 4 days have rain > 0.1mm
        prob = calculate_probability(sample_weather_data, lambda x: x.precip > 0.1)
        assert prob == 0.5

    def test_calculate_heat_probability(self):
        """Test heat probability calculation"""
        # 2 out of 4 days have temp > 35°C
        prob = calculate_probability(sample_weather_data, lambda x: x.temp_max > 35.0)
        assert prob == 0.5

    def test_calculate_cold_probability(self):
        """Test cold probability calculation"""
        # 0 out of 4 days have temp < 5°C
        prob = calculate_probability(sample_weather_data, lambda x: x.temp_min < 5.0)
        assert prob == 0.0

    def test_calculate_wind_probability(self):
        """Test wind probability calculation"""
        # 2 out of 4 days have wind > 15 m/s
        prob = calculate_probability(sample_weather_data, lambda x: x.windspeed > 15.0)
        assert prob == 0.5

    def test_empty_data(self):
        """Test probability calculation with empty data"""
        prob = calculate_probability([], lambda x: x.precip > 0.1)
        assert prob == 0.0

class TestAPIEndpoints:
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        assert "Will It Rain on My Parade?" in response.json()["message"]

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch('main.weather_service')
    def test_rain_probability_endpoint(self, mock_service):
        """Test rain probability endpoint"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/rain?lat=40.7128&lon=-74.0060&month=6&day=15")
        assert response.status_code == 200
        
        data = response.json()
        assert "probability" in data
        assert "source" in data
        assert data["source"] == "VisualCrossing"

    @patch('main.weather_service')
    def test_heat_probability_endpoint(self, mock_service):
        """Test heat probability endpoint"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/heat?lat=40.7128&lon=-74.0060&month=6&day=15&threshold=30")
        assert response.status_code == 200
        
        data = response.json()
        assert "probability" in data
        assert data["threshold"] == 30

    @patch('main.weather_service')
    def test_cold_probability_endpoint(self, mock_service):
        """Test cold probability endpoint"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/cold?lat=40.7128&lon=-74.0060&month=6&day=15")
        assert response.status_code == 200
        
        data = response.json()
        assert "probability" in data

    @patch('main.weather_service')
    def test_wind_probability_endpoint(self, mock_service):
        """Test wind probability endpoint"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/wind?lat=40.7128&lon=-74.0060&month=6&day=15")
        assert response.status_code == 200
        
        data = response.json()
        assert "probability" in data

    @patch('main.weather_service')
    def test_all_probabilities_endpoint(self, mock_service):
        """Test all probabilities endpoint"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)
        
        response = client.get("/probability/all?lat=40.7128&lon=-74.0060&month=6&day=15")
        assert response.status_code == 200
        
        data = response.json()
        assert "rain" in data
        assert "heat" in data
        assert "cold" in data
        assert "wind" in data
        assert "historical_data" in data

    def test_invalid_parameters(self):
        """Test endpoints with invalid parameters"""
        # Invalid month
        response = client.get("/probability/rain?lat=40.7128&lon=-74.0060&month=13&day=15")
        assert response.status_code == 422
        
        # Invalid day
        response = client.get("/probability/rain?lat=40.7128&lon=-74.0060&month=6&day=32")
        assert response.status_code == 422
        
        # Missing required parameters
        response = client.get("/probability/rain?lat=40.7128")
        assert response.status_code == 422

    def test_service_unavailable(self):
        """Test endpoints when weather service is unavailable"""
        with patch('main.weather_service', None):
            response = client.get("/probability/rain?lat=40.7128&lon=-74.0060&month=6&day=15")
            assert response.status_code == 503

if __name__ == "__main__":
    pytest.main([__file__])
