import { ProbabilityResponse, ProbabilityData, FetchProbabilitiesParams } from '../types/weather'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

class WeatherApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = 'WeatherApiError'
  }
}

async function fetchWithErrorHandling(url: string): Promise<any> {
  try {
    const response = await fetch(url)
    
    if (!response.ok) {
      if (response.status === 503) {
        throw new WeatherApiError('Weather service is currently unavailable. Please try again later.', 503)
      } else if (response.status === 422) {
        throw new WeatherApiError('Invalid parameters provided.', 422)
      } else if (response.status >= 500) {
        throw new WeatherApiError('Server error occurred. Please try again later.', response.status)
      } else {
        throw new WeatherApiError(`Request failed with status ${response.status}`, response.status)
      }
    }
    
    return await response.json()
  } catch (error) {
    if (error instanceof WeatherApiError) {
      throw error
    } else if (error instanceof TypeError) {
      throw new WeatherApiError('Network error. Please check your connection and try again.')
    } else {
      throw new WeatherApiError('An unexpected error occurred.')
    }
  }
}

export async function fetchRainProbability(params: {
  lat: number
  lon: number
  month: number
  day: number
  threshold?: number
}): Promise<ProbabilityResponse> {
  const { lat, lon, month, day, threshold = 0.1 } = params
  const url = `${API_BASE_URL}/probability/rain?lat=${lat}&lon=${lon}&month=${month}&day=${day}&threshold=${threshold}`
  return fetchWithErrorHandling(url)
}

export async function fetchHeatProbability(params: {
  lat: number
  lon: number
  month: number
  day: number
  threshold?: number
}): Promise<ProbabilityResponse> {
  const { lat, lon, month, day, threshold = 35 } = params
  const url = `${API_BASE_URL}/probability/heat?lat=${lat}&lon=${lon}&month=${month}&day=${day}&threshold=${threshold}`
  return fetchWithErrorHandling(url)
}

export async function fetchColdProbability(params: {
  lat: number
  lon: number
  month: number
  day: number
  threshold?: number
}): Promise<ProbabilityResponse> {
  const { lat, lon, month, day, threshold = 5 } = params
  const url = `${API_BASE_URL}/probability/cold?lat=${lat}&lon=${lon}&month=${month}&day=${day}&threshold=${threshold}`
  return fetchWithErrorHandling(url)
}

export async function fetchWindProbability(params: {
  lat: number
  lon: number
  month: number
  day: number
  threshold?: number
}): Promise<ProbabilityResponse> {
  const { lat, lon, month, day, threshold = 15 } = params
  const url = `${API_BASE_URL}/probability/wind?lat=${lat}&lon=${lon}&month=${month}&day=${day}&threshold=${threshold}`
  return fetchWithErrorHandling(url)
}

export async function fetchAllProbabilities(params: FetchProbabilitiesParams): Promise<ProbabilityData> {
  const { lat, lon, month, day, rainThreshold, heatThreshold, coldThreshold, windThreshold } = params
  const url = `${API_BASE_URL}/probability/all?lat=${lat}&lon=${lon}&month=${month}&day=${day}&rain_threshold=${rainThreshold}&heat_threshold=${heatThreshold}&cold_threshold=${coldThreshold}&wind_threshold=${windThreshold}`
  return fetchWithErrorHandling(url)
}

export async function checkApiHealth(): Promise<{ status: string; timestamp: string }> {
  const url = `${API_BASE_URL}/health`
  return fetchWithErrorHandling(url)
}
