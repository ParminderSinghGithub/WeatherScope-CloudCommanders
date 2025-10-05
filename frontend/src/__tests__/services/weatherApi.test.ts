import { 
  fetchRainProbability, 
  fetchHeatProbability, 
  fetchColdProbability, 
  fetchWindProbability,
  fetchAllProbabilities,
  checkApiHealth
} from '../../services/weatherApi'

// Mock fetch
global.fetch = jest.fn()

describe('Weather API Service', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('fetchRainProbability', () => {
    test('fetches rain probability successfully', async () => {
      const mockResponse = {
        probability: 0.3,
        source: 'VisualCrossing',
        threshold: 0.1,
        data_points: 10,
        location: { lat: 40.7128, lon: -74.0060 },
        date: { month: 6, day: 15 }
      }

      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      })

      const result = await fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/probability/rain?lat=40.7128&lon=-74.0060&month=6&day=15&threshold=0.1')
      )
      expect(result).toEqual(mockResponse)
    })

    test('uses custom threshold', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({})
      })

      await fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15,
        threshold: 0.5
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('threshold=0.5')
      )
    })
  })

  describe('fetchAllProbabilities', () => {
    test('fetches all probabilities successfully', async () => {
      const mockResponse = {
        rain: { probability: 0.3, threshold: 0.1 },
        heat: { probability: 0.6, threshold: 35 },
        cold: { probability: 0.1, threshold: 5 },
        wind: { probability: 0.4, threshold: 15 },
        source: 'VisualCrossing',
        data_points: 10,
        location: { lat: 40.7128, lon: -74.0060 },
        date: { month: 6, day: 15 },
        historical_data: []
      }

      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      })

      const result = await fetchAllProbabilities({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15,
        rainThreshold: 0.1,
        heatThreshold: 35,
        coldThreshold: 5,
        windThreshold: 15
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/probability/all?')
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('error handling', () => {
    test('handles 503 service unavailable error', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 503
      })

      await expect(fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })).rejects.toThrow('Weather service is currently unavailable')
    })

    test('handles 422 validation error', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 422
      })

      await expect(fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })).rejects.toThrow('Invalid parameters provided')
    })

    test('handles 500 server error', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: false,
        status: 500
      })

      await expect(fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })).rejects.toThrow('Server error occurred')
    })

    test('handles network error', async () => {
      ;(fetch as jest.Mock).mockRejectedValue(new TypeError('Network error'))

      await expect(fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })).rejects.toThrow('Network error. Please check your connection')
    })

    test('handles unexpected error', async () => {
      ;(fetch as jest.Mock).mockRejectedValue(new Error('Unexpected error'))

      await expect(fetchRainProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })).rejects.toThrow('An unexpected error occurred')
    })
  })

  describe('checkApiHealth', () => {
    test('checks API health successfully', async () => {
      const mockResponse = {
        status: 'healthy',
        timestamp: '2023-01-01T00:00:00Z'
      }

      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => mockResponse
      })

      const result = await checkApiHealth()

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/health')
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('individual probability endpoints', () => {
    test('fetchHeatProbability works correctly', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ probability: 0.6 })
      })

      await fetchHeatProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/probability/heat')
      )
    })

    test('fetchColdProbability works correctly', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ probability: 0.1 })
      })

      await fetchColdProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/probability/cold')
      )
    })

    test('fetchWindProbability works correctly', async () => {
      ;(fetch as jest.Mock).mockResolvedValue({
        ok: true,
        json: async () => ({ probability: 0.4 })
      })

      await fetchWindProbability({
        lat: 40.7128,
        lon: -74.0060,
        month: 6,
        day: 15
      })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/probability/wind')
      )
    })
  })
})
