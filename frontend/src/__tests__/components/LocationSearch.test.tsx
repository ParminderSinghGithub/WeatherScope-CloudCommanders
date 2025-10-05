import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LocationSearch from '../../components/LocationSearch'

// Mock fetch for Nominatim API
global.fetch = jest.fn()

const mockOnLocationSelect = jest.fn()

const mockNominatimResponse = [
  {
    lat: '40.7128',
    lon: '-74.0060',
    display_name: 'New York, NY, United States',
    address: {
      city: 'New York',
      state: 'New York',
      country: 'United States'
    }
  },
  {
    lat: '34.0522',
    lon: '-118.2437',
    display_name: 'Los Angeles, CA, United States',
    address: {
      city: 'Los Angeles',
      state: 'California',
      country: 'United States'
    }
  }
]

describe('LocationSearch Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    ;(fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockNominatimResponse
    })
  })

  test('renders location search input', () => {
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    expect(screen.getByPlaceholderText(/search for a city/i)).toBeInTheDocument()
    expect(screen.getByText('Use Current Location')).toBeInTheDocument()
  })

  test('searches for locations when typing', async () => {
    const user = userEvent.setup()
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    const searchInput = screen.getByPlaceholderText(/search for a city/i)
    await user.type(searchInput, 'New York')
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('nominatim.openstreetmap.org/search')
      )
    })
  })

  test('displays search results', async () => {
    const user = userEvent.setup()
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    const searchInput = screen.getByPlaceholderText(/search for a city/i)
    await user.type(searchInput, 'New York')
    
    await waitFor(() => {
      expect(screen.getByText('New York, New York, United States')).toBeInTheDocument()
      expect(screen.getByText('Los Angeles, California, United States')).toBeInTheDocument()
    })
  })

  test('selects location from search results', async () => {
    const user = userEvent.setup()
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    const searchInput = screen.getByPlaceholderText(/search for a city/i)
    await user.type(searchInput, 'New York')
    
    await waitFor(() => {
      expect(screen.getByText('New York, New York, United States')).toBeInTheDocument()
    })
    
    const locationButton = screen.getByText('New York, New York, United States')
    await user.click(locationButton)
    
    expect(mockOnLocationSelect).toHaveBeenCalledWith({
      lat: 40.7128,
      lon: -74.0060,
      name: 'New York, New York, United States'
    })
  })

  test('handles current location request', async () => {
    const mockGetCurrentPosition = jest.fn()
    ;(navigator.geolocation as any).getCurrentPosition = mockGetCurrentPosition
    
    // Mock reverse geocoding response
    ;(fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockNominatimResponse[0]
    })
    
    const user = userEvent.setup()
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    const currentLocationButton = screen.getByText('Use Current Location')
    await user.click(currentLocationButton)
    
    expect(mockGetCurrentPosition).toHaveBeenCalled()
    
    // Simulate successful geolocation
    const successCallback = mockGetCurrentPosition.mock.calls[0][0]
    successCallback({
      coords: {
        latitude: 40.7128,
        longitude: -74.0060
      }
    })
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('nominatim.openstreetmap.org/reverse')
      )
    })
  })

  test('handles search error gracefully', async () => {
    ;(fetch as jest.Mock).mockRejectedValue(new Error('Network error'))
    
    const user = userEvent.setup()
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    const searchInput = screen.getByPlaceholderText(/search for a city/i)
    await user.type(searchInput, 'New York')
    
    // Should not crash and should handle error gracefully
    await waitFor(() => {
      expect(fetch).toHaveBeenCalled()
    })
  })

  test('does not search for queries shorter than 3 characters', async () => {
    const user = userEvent.setup()
    render(<LocationSearch onLocationSelect={mockOnLocationSelect} />)
    
    const searchInput = screen.getByPlaceholderText(/search for a city/i)
    await user.type(searchInput, 'NY')
    
    // Wait a bit to ensure debounce doesn't trigger
    await new Promise(resolve => setTimeout(resolve, 600))
    
    expect(fetch).not.toHaveBeenCalled()
  })

  test('closes search results when clicking outside', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <LocationSearch onLocationSelect={mockOnLocationSelect} />
        <div data-testid="outside">Outside element</div>
      </div>
    )
    
    const searchInput = screen.getByPlaceholderText(/search for a city/i)
    await user.type(searchInput, 'New York')
    
    await waitFor(() => {
      expect(screen.getByText('New York, New York, United States')).toBeInTheDocument()
    })
    
    const outsideElement = screen.getByTestId('outside')
    await user.click(outsideElement)
    
    await waitFor(() => {
      expect(screen.queryByText('New York, New York, United States')).not.toBeInTheDocument()
    })
  })
})
