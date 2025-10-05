import * as React from 'react'

interface ProbabilityCardProps {
  type: 'rain' | 'heat' | 'cold' | 'wind'
  label: string
  icon: string
  probability: number
  threshold: number
  unit: string
  description: string
  color: string
  bgColor: string
  borderColor: string
}

const ProbabilityCard: React.FC<ProbabilityCardProps> = ({
  type,
  label,
  icon,
  probability,
  threshold,
  unit,
  description,
  color,
  bgColor,
  borderColor
}) => {
  const percentage = Math.round(probability * 100)
  
  // Create circular progress indicator
  const circumference = 2 * Math.PI * 45 // radius = 45
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (probability * circumference)

  const getRiskLevel = (prob: number) => {
    if (prob >= 0.7) return { level: 'High', color: 'text-red-600 dark:text-red-400' }
    if (prob >= 0.4) return { level: 'Medium', color: 'text-yellow-600 dark:text-yellow-400' }
    return { level: 'Low', color: 'text-green-600 dark:text-green-400' }
  }

  const risk = getRiskLevel(probability)

  return (
    <div className={`weather-card ${bgColor} border ${borderColor} relative overflow-hidden`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <span className="text-2xl mr-2" style={{ color }}>{icon}</span>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {label}
          </h3>
        </div>
        <div className={`px-2 py-1 rounded-full text-xs font-medium ${risk.color} bg-white dark:bg-gray-800`}>
          {risk.level} Risk
        </div>
      </div>

      {/* Probability Gauge */}
      <div className="flex items-center justify-between mb-4">
        <div className="relative">
          <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
            {/* Background circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              stroke="currentColor"
              strokeWidth="8"
              fill="transparent"
              className="text-gray-200 dark:text-gray-700"
            />
            {/* Progress circle */}
            <circle
              cx="50"
              cy="50"
              r="45"
              stroke={color}
              strokeWidth="8"
              fill="transparent"
              strokeDasharray={strokeDasharray}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {percentage}%
              </div>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">
            Threshold
          </div>
          <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {type === 'cold' ? '< ' : '> '}{threshold}{unit}
          </div>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        {description}
      </p>

      {/* Probability Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className="h-2 rounded-full transition-all duration-1000"
            style={{ backgroundColor: color, width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* Interpretation */}
      <div className="mt-4 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
        <div className="text-xs text-gray-600 dark:text-gray-400">
          <strong>Interpretation:</strong> Based on historical data, there's a{' '}
          <span className="font-semibold" style={{ color }}>
            {percentage}% chance
          </span>{' '}
          that {type === 'rain' ? 'precipitation will exceed' : 
               type === 'heat' ? 'maximum temperature will exceed' :
               type === 'cold' ? 'minimum temperature will be below' :
               'wind speed will exceed'} {threshold}{unit} on this date.
        </div>
      </div>
    </div>
  )
}

export default ProbabilityCard
