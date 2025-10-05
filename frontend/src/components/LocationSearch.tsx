import * as React from 'react'
import { useState, useEffect, useRef } from 'react'

interface LocationSearchProps {
  onLocationSelect: (location: { lat: number; lon: number; name: string }) => void
}

interface NominatimResult {
  lat: string
  lon: string
  display_name: string
  address?: {
    city?: string
    town?: string
    village?: string
    state?: string
    country?: string
  }
}

const LocationSearch: React.FC<LocationSearchProps> = ({ onLocationSelect }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<NominatimResult[]>([])
  const [loading, setLoading] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedLocation, setSelectedLocation] = useState<string>('')
  const searchRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<NodeJS.Timeout>()

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }

    if (query.length < 3) {
      setResults([])
      setShowResults(false)
      return
    }

    debounceRef.current = setTimeout(() => {
      searchLocations(query)
    }, 500)

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current)
      }
    }
  }, [query])

  const searchLocations = async (searchQuery: string) => {
    setLoading(true)
    try {
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
          searchQuery
        )}&limit=5&addressdetails=1`
      )
      const data: NominatimResult[] = await response.json()
      setResults(data)
      setShowResults(true)
    } catch (error) {
      console.error('Error searching locations:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleLocationSelect = (result: NominatimResult) => {
    const location = {
      lat: parseFloat(result.lat),
      lon: parseFloat(result.lon),
      name: formatLocationName(result)
    }
    
    setSelectedLocation(location.name)
    setQuery(location.name)
    setShowResults(false)
    onLocationSelect(location)
  }

  const formatLocationName = (result: NominatimResult): string => {
    const { address } = result
    if (!address) return result.display_name.split(',')[0]

    const city = address.city || address.town || address.village
    const state = address.state
    const country = address.country

    if (city && state && country) {
      return `${city}, ${state}, ${country}`
    } else if (city && country) {
      return `${city}, ${country}`
    } else {
      return result.display_name.split(',').slice(0, 2).join(', ')
    }
  }

  const getCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by this browser.')
      return
    }

    setLoading(true)
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        const { latitude, longitude } = position.coords
        
        try {
          // Reverse geocode to get location name
          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
          )
          const data = await response.json()
          
          const location = {
            lat: latitude,
            lon: longitude,
            name: formatLocationName(data)
          }
          
          setSelectedLocation(location.name)
          setQuery(location.name)
          onLocationSelect(location)
        } catch (error) {
          console.error('Error getting location name:', error)
          const location = {
            lat: latitude,
            lon: longitude,
            name: `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`
          }
          setSelectedLocation(location.name)
          setQuery(location.name)
          onLocationSelect(location)
        } finally {
          setLoading(false)
        }
      },
      (error) => {
        console.error('Error getting location:', error)
        alert('Unable to get your location. Please search manually.')
        setLoading(false)
      }
    )
  }

  return (
    <div className="weather-card">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <span className="mr-2">📍</span>
        Location
      </h3>
      
      <div className="space-y-3">
        <div className="relative" ref={searchRef}>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">🔍</span>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for a city or location..."
              className="input-field pl-10 pr-10"
              onFocus={() => results.length > 0 && setShowResults(true)}
            />
            {loading && (
              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400">⏳</span>
            )}
          </div>

          {/* Search Results */}
          {showResults && results.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {results.map((result, index) => (
                <button
                  key={index}
                  onClick={() => handleLocationSelect(result)}
                  className="w-full text-left px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700 last:border-b-0 transition-colors"
                >
                  <div className="flex items-start">
                    <span className="text-gray-400 mt-0.5 mr-3 flex-shrink-0">📍</span>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-gray-100">
                        {formatLocationName(result)}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400 truncate">
                        {result.display_name}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={getCurrentLocation}
          disabled={loading}
          className="w-full btn-secondary flex items-center justify-center"
        >
          {loading ? (
            <span className="mr-2">⏳</span>
          ) : (
            <span className="mr-2">📍</span>
          )}
          Use Current Location
        </button>

        {selectedLocation && (
          <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3">
            <div className="flex items-center">
              <span className="text-blue-600 mr-2">📍</span>
              <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Selected: {selectedLocation}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LocationSearch
