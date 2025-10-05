import * as React from 'react'
import { ThresholdSettings } from '../types/weather'

interface ThresholdSlidersProps {
  thresholds: ThresholdSettings
  onThresholdChange: (thresholds: ThresholdSettings) => void
}

const ThresholdSliders: React.FC<ThresholdSlidersProps> = ({ thresholds, onThresholdChange }) => {
  const handleThresholdChange = (type: keyof ThresholdSettings, value: number) => {
    onThresholdChange({
      ...thresholds,
      [type]: value
    })
  }

  const sliderConfig = [
    {
      key: 'rain' as const,
      label: 'Rain Threshold',
      icon: '💧',
      value: thresholds.rain,
      min: 0,
      max: 10,
      step: 0.1,
      unit: 'mm',
      color: 'rain',
      description: 'Minimum precipitation to consider as "rainy"'
    },
    {
      key: 'heat' as const,
      label: 'Heat Threshold',
      icon: '🌡️',
      value: thresholds.heat,
      min: 25,
      max: 50,
      step: 1,
      unit: '°C',
      color: 'heat',
      description: 'Minimum temperature to consider as "very hot"'
    },
    {
      key: 'cold' as const,
      label: 'Cold Threshold',
      icon: '❄️',
      value: thresholds.cold,
      min: -10,
      max: 15,
      step: 1,
      unit: '°C',
      color: 'cold',
      description: 'Maximum temperature to consider as "very cold"'
    },
    {
      key: 'wind' as const,
      label: 'Wind Threshold',
      icon: '💨',
      value: thresholds.wind,
      min: 5,
      max: 30,
      step: 1,
      unit: 'm/s',
      color: 'wind',
      description: 'Minimum wind speed to consider as "very windy"'
    }
  ]

  const getColorClasses = (color: string) => {
    const colorMap = {
      rain: 'text-rain-600 bg-rain-100 dark:bg-rain-900/30 border-rain-200 dark:border-rain-700',
      heat: 'text-heat-600 bg-heat-100 dark:bg-heat-900/30 border-heat-200 dark:border-heat-700',
      cold: 'text-cold-600 bg-cold-100 dark:bg-cold-900/30 border-cold-200 dark:border-cold-700',
      wind: 'text-wind-600 bg-wind-100 dark:bg-wind-900/30 border-wind-200 dark:border-wind-700'
    }
    return colorMap[color as keyof typeof colorMap] || 'text-gray-600 bg-gray-100 dark:bg-gray-900/30 border-gray-200 dark:border-gray-700'
  }

  const getSliderColor = (color: string) => {
    const colorMap = {
      rain: 'accent-rain-500',
      heat: 'accent-heat-500',
      cold: 'accent-cold-500',
      wind: 'accent-wind-500'
    }
    return colorMap[color as keyof typeof colorMap] || 'accent-primary-500'
  }

  return (
    <div className="weather-card">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <span className="mr-2">🌡️</span>
        Thresholds
      </h3>
      
      <div className="space-y-6">
        {sliderConfig.map((config, index) => {
          const iconEmoji = config.icon
          return (
            <div key={config.key} className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <span className="mr-2">{iconEmoji}</span>
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {config.label}
                  </label>
                </div>
                <div className={`px-2 py-1 rounded-md border text-sm font-medium ${getColorClasses(config.color)}`}>
                  {config.value}{config.unit}
                </div>
              </div>
              
              <div className="relative">
                <input
                  type="range"
                  min={config.min}
                  max={config.max}
                  step={config.step}
                  value={config.value}
                  onChange={(e) => handleThresholdChange(config.key, parseFloat(e.target.value))}
                  className={`slider ${getSliderColor(config.color)}`}
                />
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                  <span>{config.min}{config.unit}</span>
                  <span>{config.max}{config.unit}</span>
                </div>
              </div>
              
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {config.description}
              </p>
            </div>
          )
        })}
        
        {/* Reset Button */}
        <button
          onClick={() => onThresholdChange({ rain: 0.1, heat: 35, cold: 5, wind: 15 })}
          className="w-full btn-secondary text-sm"
        >
          Reset to Defaults
        </button>
        
        {/* Info Box */}
        <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3">
          <div className="text-xs text-blue-800 dark:text-blue-200">
            <p className="font-medium mb-1">How thresholds work:</p>
            <ul className="space-y-1 text-blue-700 dark:text-blue-300">
              <li>• <strong>Rain:</strong> Days with precipitation above this amount</li>
              <li>• <strong>Heat:</strong> Days with maximum temperature above this value</li>
              <li>• <strong>Cold:</strong> Days with minimum temperature below this value</li>
              <li>• <strong>Wind:</strong> Days with wind speed above this value</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ThresholdSliders
