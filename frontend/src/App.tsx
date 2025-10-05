import * as React from 'react'
import { useState, useEffect } from 'react'
import ProbabilityDashboard from './components/ProbabilityDashboard.tsx'
import WeatherMap from './components/WeatherMap.tsx'
import LocationSearch from './components/LocationSearch.tsx'
import DatePicker from './components/DatePicker.tsx'
import ThresholdSliders from './components/ThresholdSliders.tsx'
import ExportData from './components/ExportData.tsx'
import Globe3D from './components/Globe3D.tsx'
import { ProbabilityData, DateSelection, ThresholdSettings } from './types/weather'
import { fetchAllProbabilities } from './services/weatherApi'

function App() {
  const [darkMode, setDarkMode] = useState(false)
  const [location, setLocation] = useState<{ lat: number; lon: number; name: string } | null>({
    lat: 40.7128,
    lon: -74.0060,
    name: 'New York, NY'
  })
  const [selectedDate, setSelectedDate] = useState<DateSelection>({ month: 6, day: 15 })
  const [thresholds, setThresholds] = useState<ThresholdSettings>({
    rain: 0.1,
    heat: 35,
    cold: 5,
    wind: 15
  })
  const [probabilityData, setProbabilityData] = useState<ProbabilityData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize dark mode from localStorage
  useEffect(() => {
    const savedDarkMode = localStorage.getItem('darkMode')
    if (savedDarkMode) {
      setDarkMode(JSON.parse(savedDarkMode))
    }
  }, [])

  // Apply dark mode to document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
  }, [darkMode])

  // Fetch probability data when inputs change
  useEffect(() => {
    if (location) {
      fetchProbabilities()
    }
  }, [location, selectedDate, thresholds])

  const fetchProbabilities = async () => {
    if (!location) return

    setLoading(true)
    setError(null)

    try {
      const data = await fetchAllProbabilities({
        lat: location.lat,
        lon: location.lon,
        month: selectedDate.month,
        day: selectedDate.day,
        rainThreshold: thresholds.rain,
        heatThreshold: thresholds.heat,
        coldThreshold: thresholds.cold,
        windThreshold: thresholds.wind
      })
      setProbabilityData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch weather data')
    } finally {
      setLoading(false)
    }
  }

  const toggleDarkMode = () => {
    setDarkMode(!darkMode)
  }

  return (
    <div className={`min-h-screen transition-all duration-500 ${darkMode ? 'bg-gradient-to-br from-gray-900 via-blue-900 to-indigo-900' : 'bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50'}`}>
      {/* Animated Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-yellow-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse" style={{animationDelay: '2s'}}></div>
        <div className="absolute top-40 left-40 w-80 h-80 bg-pink-300 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse" style={{animationDelay: '4s'}}></div>
      </div>

      {/* Header */}
      <header className="relative bg-white/10 dark:bg-gray-900/10 backdrop-blur-md border-b border-white/20 dark:border-gray-700/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-20">
            <div className="flex items-center space-x-4">
              <div className="text-4xl animate-bounce">🌦️</div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
                  WeatherScope
                </h1>
                <p className="text-sm text-gray-600 dark:text-gray-300">
                  Personalized Weather Risk Dashboard
                </p>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <button
                onClick={toggleDarkMode}
                className="p-3 rounded-full bg-white/20 dark:bg-gray-800/20 backdrop-blur-sm border border-white/30 dark:border-gray-600/30 hover:bg-white/30 dark:hover:bg-gray-700/30 transition-all duration-300"
              >
                {darkMode ? '☀️' : '🌙'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section with Globe/Map */}
      <section className="relative py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-8">
            <h2 className="text-5xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent mb-4">
              Discover Weather Probabilities
            </h2>
            <p className="text-xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto">
              Advanced historical weather analysis powered by machine learning. 
              Click anywhere to explore weather risks for any location and date.
            </p>
          </div>

          {/* Interactive Globe with Earth Map */}
          <Globe3D 
            onLocationSelect={setLocation}
            selectedLocation={location}
          />
        </div>
      </section>

      {/* Main Content */}
      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Left Sidebar - Enhanced Controls */}
          <div className="lg:col-span-1 space-y-6">
            <LocationSearch onLocationSelect={setLocation} />
            <DatePicker 
              selectedDate={selectedDate}
              onDateChange={setSelectedDate}
            />
            <ThresholdSliders 
              thresholds={thresholds}
              onThresholdChange={setThresholds}
            />
          </div>

          {/* Main Content Area */}
          <div className="lg:col-span-3">

          {/* Error Display */}
          {error && (
            <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg p-4">
              <p className="text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          {/* Loading Display */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="flex items-center space-x-3">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span className="text-gray-600 dark:text-gray-400">
                  Calculating probabilities...
                </span>
              </div>
            </div>
          )}

          {/* Results */}
          {probabilityData && !loading && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2">
                <ProbabilityDashboard data={probabilityData} />
              </div>
              <div className="space-y-6">
                {location && (
                  <WeatherMap 
                    center={[location.lat, location.lon]}
                    probabilityData={probabilityData}
                  />
                )}
                <ExportData 
                  data={probabilityData}
                  location={location}
                  date={selectedDate}
                />
              </div>
            </div>
          )}
        </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-800 dark:text-white mb-1">
              Crafted by <span className="text-blue-600 dark:text-blue-400 font-bold">Cloud Commanders</span> © 2025
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              "Navigating the skies of innovation, one cloud at a time ☁️⚡"
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App
