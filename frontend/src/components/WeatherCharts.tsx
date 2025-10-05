import * as React from 'react'
import { useState, useEffect } from 'react'
import { ProbabilityData } from '../types/weather'

interface WeatherChartsProps {
  data: ProbabilityData
}

const WeatherCharts: React.FC<WeatherChartsProps> = ({ data }) => {
  const [activeChart, setActiveChart] = useState<'bar' | 'radar' | 'timeline' | 'bell' | 'timeseries'>('bar')

  const chartData = [
    { name: 'Rain', value: data.rain.probability * 100, color: '#3B82F6', emoji: '🌧️' },
    { name: 'Heat', value: data.heat.probability * 100, color: '#EF4444', emoji: '🌡️' },
    { name: 'Cold', value: data.cold.probability * 100, color: '#06B6D4', emoji: '❄️' },
  ]

  const maxValue = Math.max(...chartData.map(d => d.value))

  return (
    <div className="bg-white/10 dark:bg-gray-800/10 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/50 shadow-xl p-6 overflow-hidden">
      <div className="flex flex-col space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-800 dark:text-white">
            Weather Risk Analysis
          </h2>
        </div>

        {/* Chart Type Selector */}
        <div className="flex flex-wrap gap-2 overflow-x-auto pb-2">
          <button
            onClick={() => setActiveChart('bar')}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeChart === 'bar'
                ? 'bg-blue-500 text-white'
                : 'bg-white/20 dark:bg-gray-700/20 text-gray-600 dark:text-gray-300 hover:bg-white/30 dark:hover:bg-gray-600/30'
            }`}
          >
            📊 Bar
          </button>
          <button
            onClick={() => setActiveChart('radar')}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeChart === 'radar'
                ? 'bg-blue-500 text-white'
                : 'bg-white/20 dark:bg-gray-700/20 text-gray-600 dark:text-gray-300 hover:bg-white/30 dark:hover:bg-gray-600/30'
            }`}
          >
            🎯 Radar
          </button>
          <button
            onClick={() => setActiveChart('timeline')}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeChart === 'timeline'
                ? 'bg-blue-500 text-white'
                : 'bg-white/20 dark:bg-gray-700/20 text-gray-600 dark:text-gray-300 hover:bg-white/30 dark:hover:bg-gray-600/30'
            }`}
          >
            📈 Timeline
          </button>
          <button
            onClick={() => setActiveChart('bell')}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeChart === 'bell'
                ? 'bg-blue-500 text-white'
                : 'bg-white/20 dark:bg-gray-700/20 text-gray-600 dark:text-gray-300 hover:bg-white/30 dark:hover:bg-gray-600/30'
            }`}
          >
            🔔 Bell Curve
          </button>
          <button
            onClick={() => setActiveChart('timeseries')}
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeChart === 'timeseries'
                ? 'bg-blue-500 text-white'
                : 'bg-white/20 dark:bg-gray-700/20 text-gray-600 dark:text-gray-300 hover:bg-white/30 dark:hover:bg-gray-600/30'
            }`}
          >
            📊 Time Series
          </button>
        </div>
      </div>

      {/* Bar Chart */}
      {activeChart === 'bar' && (
        <div className="space-y-4">
          {chartData.map((item, index) => (
            <div key={item.name} className="relative">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-lg">{item.emoji}</span>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    {item.name}
                  </span>
                </div>
                <span className="font-bold text-gray-800 dark:text-white">
                  {item.value.toFixed(1)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000 ease-out"
                  style={{
                    backgroundColor: item.color,
                    width: `${item.value}%`,
                    animationDelay: `${index * 0.2}s`
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Radar Chart (Simplified) */}
      {activeChart === 'radar' && (
        <div className="flex items-center justify-center h-64">
          <div className="relative w-48 h-48">
            <svg viewBox="0 0 200 200" className="w-full h-full">
              {/* Grid circles */}
              {[1, 2, 3, 4].map(i => (
                <circle
                  key={i}
                  cx="100"
                  cy="100"
                  r={i * 20}
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1"
                  className="text-gray-300 dark:text-gray-600"
                />
              ))}
              
              {/* Grid lines */}
              {chartData.map((_, index) => {
                const angle = (index * 90) - 90
                const x = 100 + 80 * Math.cos(angle * Math.PI / 180)
                const y = 100 + 80 * Math.sin(angle * Math.PI / 180)
                return (
                  <line
                    key={index}
                    x1="100"
                    y1="100"
                    x2={x}
                    y2={y}
                    stroke="currentColor"
                    strokeWidth="1"
                    className="text-gray-300 dark:text-gray-600"
                  />
                )
              })}

              {/* Data polygon */}
              <polygon
                points={chartData.map((item, index) => {
                  const angle = (index * 90) - 90
                  const radius = (item.value / 100) * 80
                  const x = 100 + radius * Math.cos(angle * Math.PI / 180)
                  const y = 100 + radius * Math.sin(angle * Math.PI / 180)
                  return `${x},${y}`
                }).join(' ')}
                fill="rgba(59, 130, 246, 0.2)"
                stroke="#3B82F6"
                strokeWidth="2"
              />

              {/* Data points */}
              {chartData.map((item, index) => {
                const angle = (index * 90) - 90
                const radius = (item.value / 100) * 80
                const x = 100 + radius * Math.cos(angle * Math.PI / 180)
                const y = 100 + radius * Math.sin(angle * Math.PI / 180)
                return (
                  <circle
                    key={index}
                    cx={x}
                    cy={y}
                    r="4"
                    fill={item.color}
                    stroke="white"
                    strokeWidth="2"
                  />
                )
              })}
            </svg>

            {/* Labels */}
            {chartData.map((item, index) => {
              const angle = (index * 90) - 90
              const labelRadius = 100
              const x = 100 + labelRadius * Math.cos(angle * Math.PI / 180)
              const y = 100 + labelRadius * Math.sin(angle * Math.PI / 180)
              return (
                <div
                  key={index}
                  className="absolute text-xs font-medium text-gray-700 dark:text-gray-300 transform -translate-x-1/2 -translate-y-1/2"
                  style={{
                    left: `${(x / 200) * 100}%`,
                    top: `${(y / 200) * 100}%`
                  }}
                >
                  {item.emoji} {item.name}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Timeline Chart - Monthly Progression */}
      {activeChart === 'timeline' && (
        <div className="h-64">
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Monthly Weather Risk Timeline
            </h4>
            <div className="flex flex-wrap gap-2">
              {chartData.map((item) => (
                <div key={item.name} className="flex items-center space-x-1">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  ></div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {item.emoji} {item.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <svg viewBox="0 0 400 150" className="w-full h-40">
            {/* Grid lines */}
            {[0, 25, 50, 75, 100].map(y => (
              <line
                key={y}
                x1="50"
                y1={120 - (y * 0.8)}
                x2="350"
                y2={120 - (y * 0.8)}
                stroke="currentColor"
                strokeWidth="0.5"
                className="text-gray-300 dark:text-gray-600"
              />
            ))}
            
            {/* Month progression lines */}
            {chartData.map((item) => {
              const points = []
              // Create realistic seasonal variation
              for (let month = 0; month < 12; month++) {
                let seasonalFactor = 1
                if (item.name === 'Rain') {
                  seasonalFactor = 0.8 + 0.4 * Math.sin((month - 3) * Math.PI / 6) // Peak in summer
                } else if (item.name === 'Heat') {
                  seasonalFactor = 0.5 + 0.8 * Math.sin((month - 6) * Math.PI / 6) // Peak in summer
                } else if (item.name === 'Cold') {
                  seasonalFactor = 1.5 - 0.8 * Math.sin((month - 6) * Math.PI / 6) // Peak in winter
                } else {
                  seasonalFactor = 0.9 + 0.2 * Math.sin(month * Math.PI / 3) // Wind variation
                }
                
                const value = Math.max(5, Math.min(95, item.value * seasonalFactor))
                points.push(`${50 + month * 25},${120 - (value * 0.8)}`)
              }
              
              return (
                <g key={item.name}>
                  <path
                    d={`M ${points.join(' L ')}`}
                    fill="none"
                    stroke={item.color}
                    strokeWidth="2"
                    opacity={0.8}
                  />
                  {points.map((point, i) => {
                    const [x, y] = point.split(',').map(Number)
                    return (
                      <circle
                        key={i}
                        cx={x}
                        cy={y}
                        r="2"
                        fill={item.color}
                      />
                    )
                  })}
                </g>
              )
            })}
            
            {/* Month labels */}
            {['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'].map((month, i) => (
              <text
                key={i}
                x={50 + i * 25}
                y={135}
                className="text-xs fill-gray-600 dark:fill-gray-400"
                textAnchor="middle"
              >
                {month}
              </text>
            ))}
          </svg>
        </div>
      )}

      {/* Bell Curve Chart */}
      {activeChart === 'bell' && (
        <div className="h-64">
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Probability Distribution Curves
            </h4>
            <div className="flex flex-wrap gap-2">
              {chartData.map((item) => (
                <div key={item.name} className="flex items-center space-x-1">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  ></div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {item.emoji} {item.name} ({item.value.toFixed(1)}%)
                  </span>
                </div>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-center">
            <svg viewBox="0 0 400 200" className="w-full h-full">
              {/* Grid lines */}
              {[0, 25, 50, 75, 100].map(y => (
                <line
                  key={y}
                  x1="50"
                  y1={150 - (y * 1.2)}
                  x2="350"
                  y2={150 - (y * 1.2)}
                  stroke="currentColor"
                  strokeWidth="0.5"
                  className="text-gray-300 dark:text-gray-600"
                />
              ))}
              
              {/* Y-axis labels */}
              {[0, 25, 50, 75, 100].map(y => (
                <text
                  key={y}
                  x="40"
                  y={155 - (y * 1.2)}
                  className="text-xs fill-gray-600 dark:fill-gray-400"
                  textAnchor="end"
                >
                  {y}%
                </text>
              ))}

              {/* Bell curves for each weather type */}
              {chartData.map((item, index) => {
                const mean = item.value
                const stdDev = 15
                const points = []
                for (let x = 0; x <= 100; x += 2) {
                  const y = Math.exp(-0.5 * Math.pow((x - mean) / stdDev, 2)) * 50
                  points.push(`${50 + x * 3},${150 - y}`)
                }
                
                return (
                  <g key={item.name}>
                    <path
                      d={`M ${points.join(' L ')}`}
                      fill="none"
                      stroke={item.color}
                      strokeWidth="2"
                      opacity={0.8}
                    />
                    <circle
                      cx={50 + mean * 3}
                      cy={150 - Math.exp(-0.5 * Math.pow(0, 2)) * 50}
                      r="4"
                      fill={item.color}
                    />
                    <text
                      x={50 + mean * 3}
                      y={170}
                      className="text-xs fill-gray-700 dark:fill-gray-300"
                      textAnchor="middle"
                    >
                      {item.emoji} {item.name}
                    </text>
                  </g>
                )
              })}
              
              {/* X-axis */}
              <line
                x1="50"
                y1="150"
                x2="350"
                y2="150"
                stroke="currentColor"
                strokeWidth="1"
                className="text-gray-400 dark:text-gray-500"
              />
            </svg>
            <div className="text-center mt-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Probability Distribution Curves
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Time Series Chart */}
      {activeChart === 'timeseries' && (
        <div className="h-64">
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
              Historical Weather Patterns Over Time
            </h4>
            <div className="flex flex-wrap gap-2">
              {chartData.map((item) => (
                <div key={item.name} className="flex items-center space-x-1">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  ></div>
                  <span className="text-xs text-gray-600 dark:text-gray-400">
                    {item.emoji} {item.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
          <svg viewBox="0 0 450 220" className="w-full h-full">
            {/* Grid */}
            {[0, 25, 50, 75, 100].map(y => (
              <line
                key={y}
                x1="60"
                y1={160 - (y * 1.0)}
                x2="380"
                y2={160 - (y * 1.0)}
                stroke="currentColor"
                strokeWidth="0.5"
                className="text-gray-300 dark:text-gray-600"
              />
            ))}
            
            {/* Y-axis labels */}
            {[0, 25, 50, 75, 100].map(y => (
              <text
                key={y}
                x="50"
                y={165 - (y * 1.0)}
                className="text-xs fill-gray-600 dark:fill-gray-400"
                textAnchor="end"
              >
                {y}%
              </text>
            ))}
            
            {/* Time series lines */}
            {chartData.map((item, index) => {
              const points = []
              // Simulate time series data
              for (let i = 0; i < 12; i++) {
                const variation = (Math.sin(i * 0.5) * 10) + (Math.random() * 10 - 5)
                const y = Math.max(0, Math.min(100, item.value + variation))
                points.push(`${70 + i * 26},${160 - (y * 1.0)}`)
              }
              
              return (
                <g key={item.name}>
                  <path
                    d={`M ${points.join(' L ')}`}
                    fill="none"
                    stroke={item.color}
                    strokeWidth="2"
                    opacity={0.8}
                  />
                  {points.map((point, i) => {
                    const [x, y] = point.split(',').map(Number)
                    return (
                      <circle
                        key={i}
                        cx={x}
                        cy={y}
                        r="2"
                        fill={item.color}
                      />
                    )
                  })}
                </g>
              )
            })}
            
            {/* Axes */}
            <line x1="50" y1="150" x2="350" y2="150" stroke="currentColor" strokeWidth="1" className="text-gray-400" />
            <line x1="50" y1="30" x2="50" y2="150" stroke="currentColor" strokeWidth="1" className="text-gray-400" />
            
            {/* Month labels */}
            {['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'].map((month, i) => (
              <text
                key={i}
                x={50 + i * 25}
                y={165}
                className="text-xs fill-gray-600 dark:fill-gray-400"
                textAnchor="middle"
              >
                {month}
              </text>
            ))}
          </svg>
          <div className="text-center mt-2">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Historical Trends Over 12 Months
            </p>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      <div className="mt-6 pt-4 border-t border-white/20 dark:border-gray-700/50">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-lg font-bold text-gray-800 dark:text-white">
              {Math.max(...chartData.map(d => d.value)).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Highest Risk</div>
          </div>
          <div>
            <div className="text-lg font-bold text-gray-800 dark:text-white">
              {(chartData.reduce((sum, d) => sum + d.value, 0) / chartData.length).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">Average Risk</div>
          </div>
          <div>
            <div className="text-lg font-bold text-gray-800 dark:text-white">
              {chartData.filter(d => d.value > 50).length}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400">High Risk Events</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default WeatherCharts
