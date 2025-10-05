import * as React from 'react'
import { ProbabilityData } from '../types/weather'
import WeatherCharts from './WeatherCharts'

interface ProbabilityDashboardProps {
  data: ProbabilityData
}

const ProbabilityDashboard: React.FC<ProbabilityDashboardProps> = ({ data }) => {
  const weatherTypes = [
    {
      key: 'rain' as const,
      label: 'Rain Probability',
      probability: data.rain.probability,
      threshold: data.rain.threshold,
      unit: 'mm',
      description: 'Chance of precipitation',
      color: '#3b82f6',
      emoji: '🌧️'
    },
    {
      key: 'heat' as const,
      label: 'Heat Risk',
      probability: data.heat.probability,
      threshold: data.heat.threshold,
      unit: '°C',
      description: 'High temperature risk',
      color: '#ef4444',
      emoji: '🌡️'
    },
    {
      key: 'cold' as const,
      label: 'Cold Risk',
      probability: data.cold.probability,
      threshold: data.cold.threshold,
      unit: '°C',
      description: 'Low temperature risk',
      color: '#06b6d4',
      emoji: '❄️'
    },
    {
      key: 'wind' as const,
      label: 'Wind Risk',
      probability: data.wind.probability,
      threshold: data.wind.threshold,
      unit: 'm/s',
      description: 'Strong wind conditions',
      color: '#10b981',
      emoji: '💨'
    }
  ]

  const getOverallRisk = () => {
    const avgProbability = weatherTypes.reduce((sum, w) => sum + w.probability, 0) / weatherTypes.length
    if (avgProbability >= 0.6) return { level: 'High', color: 'text-red-500', emoji: '⚠️' }
    if (avgProbability >= 0.3) return { level: 'Moderate', color: 'text-yellow-500', emoji: '⚡' }
    return { level: 'Low', color: 'text-green-500', emoji: '✅' }
  }

  const overallRisk = getOverallRisk()

  return (
    <div className="space-y-8 relative">
      {/* Hero Header */}
      <div className="text-center relative">
        <div className="text-6xl mb-4 animate-pulse">🌦️</div>
        <h2 className="text-4xl font-bold bg-gradient-to-r from-blue-600 via-purple-600 to-blue-800 bg-clip-text text-transparent mb-3">
          Weather Risk Analysis
        </h2>
        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
          Advanced probability assessment based on historical weather patterns
        </p>
        
        {/* Overall Risk Indicator */}
        <div className="mt-6 inline-flex items-center space-x-2 px-6 py-3 bg-white/10 dark:bg-gray-800/20 backdrop-blur-md rounded-full border border-white/20 dark:border-gray-700/30">
          <span className="text-2xl">{overallRisk.emoji}</span>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Overall Risk:</span>
          <span className={`font-bold ${overallRisk.color}`}>{overallRisk.level}</span>
        </div>
      </div>

      {/* Enhanced Probability Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {weatherTypes.map((weather, index) => {
          const percentage = Math.round(weather.probability * 100)
          const risk = weather.probability >= 0.7 ? 'High' : 
                      weather.probability >= 0.4 ? 'Medium' : 'Low'
          const riskColor = weather.probability >= 0.7 ? 'text-red-500' :
                           weather.probability >= 0.4 ? 'text-yellow-500' : 'text-green-500'
          
          return (
            <div
              key={weather.key}
              className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-white/80 to-white/60 dark:from-gray-800/80 dark:to-gray-900/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/50 shadow-xl hover:shadow-2xl transition-all duration-300 group"
            >
              {/* Glassmorphism overlay */}
              <div className="absolute inset-0 bg-white/10 dark:bg-white/5 backdrop-blur-sm"></div>
              
              <div className="relative p-6">
                {/* Header */}
                <div className="mb-6">
                  <div className="flex items-center space-x-3 mb-3">
                    <div className="text-3xl animate-bounce">{weather.emoji}</div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-lg font-bold text-gray-800 dark:text-white truncate">
                        {weather.label}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-300">
                        Risk Assessment
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex justify-center">
                    <div className={`px-4 py-2 rounded-full text-sm font-bold ${riskColor} bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm`}>
                      {risk} Risk
                    </div>
                  </div>
                </div>

                {/* Circular Progress Gauge */}
                <div className="flex items-center justify-center mb-6">
                  <div className="relative">
                    <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
                      {/* Background circle */}
                      <circle
                        cx="50"
                        cy="50"
                        r="45"
                        stroke="currentColor"
                        strokeWidth="6"
                        fill="transparent"
                        className="text-gray-200 dark:text-gray-700"
                      />
                      
                      {/* Progress circle */}
                      <circle
                        cx="50"
                        cy="50"
                        r="45"
                        stroke={weather.color}
                        strokeWidth="6"
                        fill="transparent"
                        strokeDasharray={`${percentage * 2.83} 283`}
                        strokeLinecap="round"
                        className="drop-shadow-sm transition-all duration-1000"
                      />
                    </svg>
                    
                    {/* Center content */}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-3xl font-bold text-gray-800 dark:text-white">
                          {percentage}%
                        </div>
                        <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                          Probability
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400">
                    <span>0%</span>
                    <span>50%</span>
                    <span>100%</span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-1000 shadow-sm"
                      style={{
                        backgroundColor: weather.color,
                        width: `${percentage}%`
                      }}
                    />
                  </div>
                </div>

                {/* Threshold Info */}
                <div className="bg-white/20 dark:bg-gray-800/20 backdrop-blur-sm rounded-lg p-3 border border-white/30 dark:border-gray-600/30">
                  <div className="text-xs text-gray-700 dark:text-gray-300">
                    <div className="flex justify-between items-center">
                      <span>Threshold:</span>
                      <span className="font-semibold">
                        {weather.key === 'cold' ? '< ' : '> '}{weather.threshold}{weather.unit}
                      </span>
                    </div>
                    <div className="mt-2 text-gray-600 dark:text-gray-400">
                      {weather.description}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Enhanced Summary Stats */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 backdrop-blur-sm border border-white/20 dark:border-gray-700/50 shadow-xl">
        {/* Glassmorphism overlay */}
        <div className="absolute inset-0 bg-white/10 dark:bg-white/5 backdrop-blur-sm"></div>
        
        <div className="relative p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-gray-800 dark:text-white flex items-center">
              <span className="mr-3">📊</span>
              Risk Assessment Summary
            </h3>
            <div className="text-2xl animate-spin" style={{ animationDuration: '20s' }}>⚡</div>
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {weatherTypes.map((weather, index) => {
              const risk = weather.probability >= 0.7 ? 'High' : 
                          weather.probability >= 0.4 ? 'Medium' : 'Low'
              const riskColor = weather.probability >= 0.7 ? 'text-red-500 dark:text-red-400' :
                               weather.probability >= 0.4 ? 'text-yellow-500 dark:text-yellow-400' : 
                               'text-green-500 dark:text-green-400'
              
              return (
                <div
                  key={weather.key}
                  className="text-center p-4 bg-white/20 dark:bg-gray-800/20 backdrop-blur-sm rounded-xl border border-white/30 dark:border-gray-600/30 hover:bg-white/30 dark:hover:bg-gray-700/30 transition-all duration-300"
                >
                  <div className="text-2xl mb-2">{weather.emoji}</div>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {weather.label.split(' ')[0]}
                  </div>
                  <div className={`text-lg font-bold ${riskColor} mb-1`}>
                    {Math.round(weather.probability * 100)}%
                  </div>
                  <div className={`text-xs font-semibold ${riskColor}`}>
                    {risk} Risk
                  </div>
                </div>
              )
            })}
          </div>

          {/* Additional Insights */}
          <div className="mt-6 p-4 bg-white/10 dark:bg-gray-800/10 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-600/20">
            <div className="flex items-start space-x-3">
              <div className="text-2xl">💡</div>
              <div>
                <h4 className="font-semibold text-gray-800 dark:text-white mb-2">
                  Weather Insights
                </h4>
                <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
                  Analysis based on historical weather data patterns. Higher probabilities indicate 
                  increased likelihood of weather conditions exceeding your specified thresholds 
                  on the selected date.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Advanced Charts Section */}
        <div className="mt-8">
          <WeatherCharts data={data} />
        </div>
      </div>
    </div>
  )
}

export default ProbabilityDashboard
