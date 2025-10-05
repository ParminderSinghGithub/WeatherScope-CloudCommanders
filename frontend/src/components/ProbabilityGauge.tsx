import * as React from 'react'
import { useEffect, useState } from 'react'

interface ProbabilityGaugeProps {
  probability: number
  type: 'rain' | 'heat' | 'cold' | 'wind'
  label: string
  threshold: number
  unit: string
}

const ProbabilityGauge: React.FC<ProbabilityGaugeProps> = ({
  probability,
  type,
  label,
  threshold,
  unit
}) => {
  const [animatedProbability, setAnimatedProbability] = useState(0)
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    setIsVisible(true)
    const timer = setTimeout(() => {
      setAnimatedProbability(probability)
    }, 300)
    return () => clearTimeout(timer)
  }, [probability])

  const getTypeConfig = (type: string) => {
    const configs = {
      rain: {
        emoji: '🌧️',
        primary: '#3B82F6',
        secondary: '#93C5FD',
        bg: 'from-blue-400/20 to-blue-600/20',
        darkBg: 'from-blue-500/10 to-blue-700/10',
        glow: 'shadow-blue-500/20'
      },
      heat: {
        emoji: '🌡️',
        primary: '#EF4444',
        secondary: '#FCA5A5',
        bg: 'from-red-400/20 to-red-600/20',
        darkBg: 'from-red-500/10 to-red-700/10',
        glow: 'shadow-red-500/20'
      },
      cold: {
        emoji: '❄️',
        primary: '#06B6D4',
        secondary: '#67E8F9',
        bg: 'from-cyan-400/20 to-cyan-600/20',
        darkBg: 'from-cyan-500/10 to-cyan-700/10',
        glow: 'shadow-cyan-500/20'
      },
      wind: {
        emoji: '💨',
        primary: '#10B981',
        secondary: '#6EE7B7',
        bg: 'from-emerald-400/20 to-emerald-600/20',
        darkBg: 'from-emerald-500/10 to-emerald-700/10',
        glow: 'shadow-emerald-500/20'
      }
    }
    return configs[type as keyof typeof configs] || configs.rain
  }

  const colors = getTypeConfig(type)
  const percentage = Math.round(animatedProbability * 100)
  const circumference = 2 * Math.PI * 45
  const strokeDasharray = circumference
  const strokeDashoffset = circumference - (animatedProbability * circumference)

  const getRiskLevel = () => {
    if (percentage >= 70) return { level: 'High', color: 'text-red-500' }
    if (percentage >= 40) return { level: 'Medium', color: 'text-yellow-500' }
    return { level: 'Low', color: 'text-green-500' }
  }

  const risk = getRiskLevel()

  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${colors.bg} dark:bg-gradient-to-br dark:${colors.darkBg} backdrop-blur-sm border border-white/20 dark:border-gray-700/50 shadow-xl hover:shadow-2xl transition-all duration-300 group animate-fade-in`}
    >
      {/* Glassmorphism overlay */}
      <div className="absolute inset-0 bg-white/10 dark:bg-white/5 backdrop-blur-sm"></div>
      
      {/* Animated background particles */}
      <div className="absolute inset-0 overflow-hidden">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full opacity-20 animate-pulse"
            style={{ 
              backgroundColor: colors.primary,
              left: `${10 + i * 15}%`,
              top: `${20 + i * 10}%`,
              animationDelay: `${i * 0.5}s`
            }}
          />
        ))}
      </div>

      <div className="relative p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="text-3xl animate-bounce">
              {colors.emoji}
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-800 dark:text-white">
                {label}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Threshold: {threshold}{unit}
              </p>
            </div>
          </div>
          <div className={`px-3 py-1 rounded-full text-xs font-semibold ${risk.color} bg-white/20 dark:bg-gray-800/20`}>
            {risk.level}
          </div>
        </div>

        {/* Circular Progress */}
        <div className="flex items-center justify-center mb-6">
          <div className="relative w-32 h-32">
            <svg className="w-32 h-32 transform -rotate-90" viewBox="0 0 100 100">
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
                stroke={colors.primary}
                strokeWidth="8"
                fill="transparent"
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                className="drop-shadow-lg transition-all duration-1000"
                style={{ filter: `drop-shadow(0 0 8px ${colors.primary}40)` }}
              />
            </svg>
            
            {/* Center content */}
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-800 dark:text-white mb-1">
                  {percentage}%
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">
                  Probability
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Risk Level</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">{percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-1000"
              style={{ backgroundColor: colors.primary, width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 text-center">
          <div className="bg-white/10 dark:bg-gray-800/10 rounded-lg p-3">
            <div className="text-lg font-bold text-gray-800 dark:text-white">
              {threshold}{unit}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">
              Threshold
            </div>
          </div>
          <div className="bg-white/10 dark:bg-gray-800/10 rounded-lg p-3">
            <div className={`text-lg font-bold ${risk.color}`}>
              {risk.level}
            </div>
            <div className="text-xs text-gray-600 dark:text-gray-400 uppercase tracking-wide">
              Risk
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
export default ProbabilityGauge
