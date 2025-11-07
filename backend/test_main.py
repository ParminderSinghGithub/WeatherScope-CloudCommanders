"""
Tests for the NASA OpenDAP-based weather probability API
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from main import app, WeatherService, WeatherData, calculate_probability

client = TestClient(app)

# Sample test data
sample_weather_data = [
    WeatherData("2020-06-15", 0.0, 0.0, 0.0, 0.0),
    WeatherData("2021-06-15", 0.0, 0.0, 2.5, 0.0),
    WeatherData("2022-06-15", 0.0, 0.0, 0.0, 0.0),
    WeatherData("2023-06-15", 0.0, 0.0, 1.2, 0.0),
]


class TestWeatherService:
    @pytest.mark.asyncio
    @patch("main.xr.open_dataset")
    async def test_fetch_single_day_success(self, mock_open):
        """Test successful single day data fetch (NASA OpenDAP)"""
        mock_ds = MagicMock()
        mock_ds.__enter__.return_value = mock_ds
        mock_ds.__exit__.return_value = None
        mock_ds["precipitationCal"].sel.return_value.values = 4.2
        mock_open.return_value = mock_ds

        service = WeatherService()
        result = await service._fetch_single_day(40.7128, -74.0060, "2023-06-15")

        assert result is not None
        assert result.precip == 4.2

    @pytest.mark.asyncio
    @patch("main.xr.open_dataset", side_effect=Exception("Dataset not found"))
    async def test_fetch_single_day_error(self, mock_open):
        """Test error handling in single day fetch (NASA)"""
        service = WeatherService()
        result = await service._fetch_single_day(40.7128, -74.0060, "2023-06-15")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_historical_data(self):
        """Test fetching historical data for multiple years"""
        with patch.object(WeatherService, "_fetch_single_day") as mock_fetch:
            mock_fetch.return_value = sample_weather_data[0]

            service = WeatherService()
            result = await service.fetch_historical_data(40.7128, -74.0060, 6, 15, 2)

            assert len(result) == 2
            assert all(isinstance(item, WeatherData) for item in result)


class TestProbabilityCalculation:
    def test_calculate_rain_probability(self):
        """Test rain probability calculation"""
        # 2 out of 4 days have rain > 0.1mm
        prob = calculate_probability(sample_weather_data, lambda x: x.precip > 0.1)
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
        assert "NASA" in response.json()["message"]

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @patch("main.weather_service")
    def test_rain_probability_endpoint(self, mock_service):
        """Test rain probability endpoint (NASA backend)"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)

        response = client.get("/probability/rain?lat=40.7128&lon=-74.0060&month=6&day=15")
        assert response.status_code == 200

        data = response.json()
        assert "probability" in data
        assert "source" in data
        assert "NASA" in data["source"]

    @patch("main.weather_service")
    def test_all_probabilities_endpoint(self, mock_service):
        """Test all probabilities endpoint (NASA backend)"""
        mock_service.fetch_historical_data = AsyncMock(return_value=sample_weather_data)

        response = client.get("/probability/all?lat=40.7128&lon=-74.0060&month=6&day=15")
        assert response.status_code == 200

        data = response.json()
        assert "rain" in data
        assert "NASA" in data["source"]
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
        with patch("main.weather_service", None):
            response = client.get("/probability/rain?lat=40.7128&lon=-74.0060&month=6&day=15")
            assert response.status_code == 503

    @pytest.mark.skip(reason="NASA backend supports only rain/all endpoints")
    def test_heat_probability_endpoint(self):
        pass

    @pytest.mark.skip(reason="NASA backend supports only rain/all endpoints")
    def test_cold_probability_endpoint(self):
        pass

    @pytest.mark.skip(reason="NASA backend supports only rain/all endpoints")
    def test_wind_probability_endpoint(self):
        pass


if __name__ == "__main__":
    pytest.main([__file__])
