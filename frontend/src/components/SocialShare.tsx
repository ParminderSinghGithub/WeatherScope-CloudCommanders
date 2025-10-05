import * as React from 'react'
import { ProbabilityData, DateSelection } from '../types/weather'

interface SocialShareProps {
  data: ProbabilityData
  location: { lat: number; lon: number; name: string } | null
  date: DateSelection
}

const SocialShare: React.FC<SocialShareProps> = ({ data, location, date }) => {
  const generateShareText = () => {
    const locationName = location?.name || 'Unknown Location'
    const dateStr = `${date.month}/${date.day}`
    const rainProb = Math.round(data.rain.probability * 100)
    const heatProb = Math.round(data.heat.probability * 100)
    const coldProb = Math.round(data.cold.probability * 100)
    const windProb = Math.round(data.wind.probability * 100)

    return `Weather probabilities for ${locationName} on ${dateStr}: 🌧️ ${rainProb}% rain, 🌡️ ${heatProb}% heat, ❄️ ${coldProb}% cold, 💨 ${windProb}% wind. Check yours at`
  }

  const generateShareUrl = () => {
    const baseUrl = window.location.origin
    const params = new URLSearchParams({
      lat: data.location.lat.toString(),
      lon: data.location.lon.toString(),
      month: date.month.toString(),
      day: date.day.toString(),
      location: location?.name || ''
    })
    return `${baseUrl}?${params.toString()}`
  }

  const shareText = generateShareText()
  const shareUrl = generateShareUrl()

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      console.log('Link copied to clipboard')
    } catch (err) {
      console.error('Failed to copy link:', err)
    }
  }

  return (
    <div className="weather-card">
      <h3 className="text-lg font-semibold mb-4">Share Results</h3>
      
      <div className="space-y-4">
        {/* Share Preview */}
        <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
          <div className="text-sm text-gray-700 dark:text-gray-300 mb-2">
            Preview:
          </div>
          <div className="text-xs text-gray-600 dark:text-gray-400 italic">
            "{shareText}"
          </div>
        </div>

        {/* Simple Share Buttons */}
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => {
              const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}&url=${encodeURIComponent(shareUrl)}`
              window.open(twitterUrl, '_blank', 'width=550,height=420')
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white text-xs py-2 px-3 rounded-lg transition-colors"
          >
            Twitter
          </button>
          <button
            onClick={() => {
              const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl)}`
              window.open(facebookUrl, '_blank', 'width=550,height=420')
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs py-2 px-3 rounded-lg transition-colors"
          >
            Facebook
          </button>
          <button
            onClick={() => {
              const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`
              window.open(whatsappUrl, '_blank')
            }}
            className="bg-green-500 hover:bg-green-600 text-white text-xs py-2 px-3 rounded-lg transition-colors"
          >
            WhatsApp
          </button>
          <button
            onClick={copyToClipboard}
            className="bg-gray-500 hover:bg-gray-600 text-white text-xs py-2 px-3 rounded-lg transition-colors"
          >
            Copy Link
          </button>
        </div>

        {/* Share Statistics */}
        <div className="grid grid-cols-2 gap-4 text-center">
          <div className="p-2 bg-primary-50 dark:bg-primary-900/30 rounded-lg">
            <div className="text-lg font-bold text-primary-600 dark:text-primary-400">
              {Math.max(
                data.rain.probability,
                data.heat.probability,
                data.cold.probability,
                data.wind.probability
              ) * 100 | 0}%
            </div>
            <div className="text-xs text-primary-700 dark:text-primary-300">
              Highest Risk
            </div>
          </div>
          <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <div className="text-lg font-bold text-gray-600 dark:text-gray-400">
              {data.data_points}
            </div>
            <div className="text-xs text-gray-700 dark:text-gray-300">
              Years Analyzed
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SocialShare
