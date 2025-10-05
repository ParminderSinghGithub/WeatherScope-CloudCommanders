import * as React from 'react'

interface WeatherParticlesProps {
  type: 'rain' | 'heat' | 'cold' | 'wind'
  probability: number
}

const WeatherParticles: React.FC<WeatherParticlesProps> = ({ type, probability }) => {
  // Only show particles if probability is above 30%
  if (probability < 0.3) {
    return null
  }

  const getParticleEmoji = () => {
    switch (type) {
      case 'rain': return '💧'
      case 'heat': return '☀️'
      case 'cold': return '❄️'
      case 'wind': return '💨'
      default: return ''
    }
  }

  const particleCount = Math.min(Math.floor(probability * 10), 8)
  const particles = Array.from({ length: particleCount }, (_, i) => i)

  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {particles.map((_, index) => (
        <div
          key={index}
          className="absolute animate-pulse"
          style={{
            left: `${Math.random() * 80 + 10}%`,
            top: `${Math.random() * 80 + 10}%`,
            animationDelay: `${Math.random() * 2}s`,
            animationDuration: `${2 + Math.random() * 2}s`
          }}
        >
          <span className="text-sm opacity-60">
            {getParticleEmoji()}
          </span>
        </div>
      ))}
    </div>
  )
}

export default WeatherParticles
