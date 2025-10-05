import * as React from 'react'
import { useState } from 'react'
import { ProbabilityData } from '../types/weather'

interface WeatherMapProps {
  center: [number, number]
  probabilityData?: ProbabilityData | null
  onLocationSelect?: (location: { lat: number; lon: number; name: string }) => void
}

const WeatherMap: React.FC<WeatherMapProps> = ({ 
  center, 
  probabilityData,
  onLocationSelect 
}) => {
  const [isMapLoaded, setIsMapLoaded] = useState(true)

  return (
    <div className="relative w-full h-96 rounded-2xl overflow-hidden bg-white/10 dark:bg-gray-800/10 backdrop-blur-sm border border-white/20 dark:border-gray-700/50 shadow-xl">
      {/* Header */}
      <div className="absolute top-4 left-4 right-4 z-10">
        <div className="bg-white/20 dark:bg-gray-800/20 backdrop-blur-sm rounded-lg p-3 border border-white/30 dark:border-gray-600/30">
          <h3 className="text-lg font-bold text-gray-800 dark:text-white mb-1">
            Weather Risk Overview
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Interactive weather analysis for selected location
          </p>
        </div>
      </div>

      {/* Weather Data Display */}
      <div className="flex items-center justify-center h-full bg-gradient-to-br from-blue-100 to-green-100 dark:from-blue-900 dark:to-green-900">
        <div className="text-center p-8">
          <div className="text-6xl mb-4">🌍</div>
          <h3 className="text-xl font-bold text-gray-800 dark:text-white mb-2">
            Weather Analysis
          </h3>
          <p className="text-gray-600 dark:text-gray-300 mb-4">
            Coordinates: {center[0].toFixed(4)}, {center[1].toFixed(4)}
          </p>
          {probabilityData && (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="bg-white/20 dark:bg-gray-800/20 rounded-lg p-3">
                <div className="text-blue-600 dark:text-blue-400 font-bold">
                  🌧️ {Math.round(probabilityData.rain.probability * 100)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Rain</div>
              </div>
              <div className="bg-white/20 dark:bg-gray-800/20 rounded-lg p-3">
                <div className="text-red-600 dark:text-red-400 font-bold">
                  🌡️ {Math.round(probabilityData.heat.probability * 100)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Heat</div>
              </div>
              <div className="bg-white/20 dark:bg-gray-800/20 rounded-lg p-3">
                <div className="text-cyan-600 dark:text-cyan-400 font-bold">
                  ❄️ {Math.round(probabilityData.cold.probability * 100)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Cold</div>
              </div>
              <div className="bg-white/20 dark:bg-gray-800/20 rounded-lg p-3">
                <div className="text-green-600 dark:text-green-400 font-bold">
                  💨 {Math.round(probabilityData.wind.probability * 100)}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">Wind</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default WeatherMap
