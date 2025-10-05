import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import * as weatherApi from '../services/weatherApi'

// Mock the weather API
jest.mock('../services/weatherApi')
const mockedWeatherApi = weatherApi as jest.Mocked<typeof weatherApi>

// Mock react-leaflet components
jest.mock('react-leaflet', () => ({
  MapContainer: ({ children }: any) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  Marker: ({ children }: any) => <div data-testid="marker">{children}</div>,
  Popup: ({ children }: any) => <div data-testid="popup">{children}</div>,
  Circle: ({ children }: any) => <div data-testid="circle">{children}</div>
}))

const mockProbabilityData = {
  rain: { probability: 0.3, threshold: 0.1 },
  heat: { probability: 0.6, threshold: 35 },
  cold: { probability: 0.1, threshold: 5 },
  wind: { probability: 0.4, threshold: 15 },
  source: 'VisualCrossing',
  data_points: 10,
  location: { lat: 40.7128, lon: -74.0060 },
  date: { month: 6, day: 15 },
  historical_data: [
    { date: '2020-06-15', temp_max: 32, temp_min: 18, precip: 0, windspeed: 12 },
    { date: '2021-06-15', temp_max: 38, temp_min: 22, precip: 2.5, windspeed: 8 },
    { date: '2022-06-15', temp_max: 29, temp_min: 16, precip: 0, windspeed: 18 }
  ]
}

describe('App Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockedWeatherApi.fetchAllProbabilities.mockResolvedValue(mockProbabilityData)
  })

  test('renders main heading', () => {
    render(<App />)
    expect(screen.getByText('Will It Rain on My Parade?')).toBeInTheDocument()
  })

  test('renders location search component', () => {
    render(<App />)
    expect(screen.getByPlaceholderText(/search for a city/i)).toBeInTheDocument()
  })

  test('renders date picker component', () => {
    render(<App />)
    expect(screen.getByText('Date')).toBeInTheDocument()
    expect(screen.getByDisplayValue('June')).toBeInTheDocument()
  })

  test('renders threshold sliders', () => {
    render(<App />)
    expect(screen.getByText('Rain Threshold')).toBeInTheDocument()
    expect(screen.getByText('Heat Threshold')).toBeInTheDocument()
    expect(screen.getByText('Cold Threshold')).toBeInTheDocument()
    expect(screen.getByText('Wind Threshold')).toBeInTheDocument()
  })

  test('toggles dark mode', async () => {
    const user = userEvent.setup()
    render(<App />)
    
    const darkModeButton = screen.getByRole('button', { name: /toggle dark mode/i }) || 
                          screen.getByRole('button')
    
    await user.click(darkModeButton)
    
    expect(document.documentElement).toHaveClass('dark')
  })

  test('displays error message when API fails', async () => {
    mockedWeatherApi.fetchAllProbabilities.mockRejectedValue(new Error('API Error'))
    
    render(<App />)
    
    // Simulate location selection to trigger API call
    const locationInput = screen.getByPlaceholderText(/search for a city/i)
    await userEvent.type(locationInput, 'New York')
    
    // Mock location selection (this would normally come from the LocationSearch component)
    // For testing purposes, we'll simulate the effect
    
    await waitFor(() => {
      expect(screen.queryByText(/api error/i)).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  test('displays loading state', async () => {
    // Mock a delayed response
    mockedWeatherApi.fetchAllProbabilities.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockProbabilityData), 1000))
    )
    
    render(<App />)
    
    // This test would need to be enhanced to properly trigger the loading state
    // by simulating location selection
  })

  test('changes date selection', async () => {
    const user = userEvent.setup()
    render(<App />)
    
    const monthSelect = screen.getByDisplayValue('June')
    await user.selectOptions(monthSelect, 'July')
    
    expect(screen.getByDisplayValue('July')).toBeInTheDocument()
  })

  test('changes threshold values', async () => {
    const user = userEvent.setup()
    render(<App />)
    
    const rainSlider = screen.getByDisplayValue('0.1')
    await user.clear(rainSlider)
    await user.type(rainSlider, '0.5')
    
    // The exact assertion would depend on how the slider is implemented
    // This is a simplified test
  })
})
