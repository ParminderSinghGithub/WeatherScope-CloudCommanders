import * as React from 'react'
import { ProbabilityData, DateSelection } from '../types/weather'

interface ExportDataProps {
  data: ProbabilityData
  location: { lat: number; lon: number; name: string } | null
  date: DateSelection
}

const ExportData: React.FC<ExportDataProps> = ({ data, location, date }) => {
  const generateCSV = () => {
    const headers = [
      'Date',
      'Temperature Max (°C)',
      'Temperature Min (°C)',
      'Precipitation (mm)',
      'Wind Speed (m/s)'
    ]

    const rows = data.historical_data.map(item => [
      item.date,
      item.temp_max.toString(),
      item.temp_min.toString(),
      item.precip.toString(),
      item.windspeed.toString()
    ])

    const csvContent = [
      `# Weather Probability Report`,
      `# Location: ${location?.name || 'Unknown'} (${data.location.lat}, ${data.location.lon})`,
      `# Date: ${date.month}/${date.day}`,
      `# Generated: ${new Date().toISOString()}`,
      `#`,
      `# Probabilities:`,
      `# Rain (>${data.rain.threshold}mm): ${(data.rain.probability * 100).toFixed(1)}%`,
      `# Heat (>${data.heat.threshold}°C): ${(data.heat.probability * 100).toFixed(1)}%`,
      `# Cold (<${data.cold.threshold}°C): ${(data.cold.probability * 100).toFixed(1)}%`,
      `# Wind (>${data.wind.threshold}m/s): ${(data.wind.probability * 100).toFixed(1)}%`,
      `#`,
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n')

    return csvContent
  }

  const generateJSON = () => {
    const exportData = {
      metadata: {
        location: {
          name: location?.name || 'Unknown',
          coordinates: {
            lat: data.location.lat,
            lon: data.location.lon
          }
        },
        date: {
          month: date.month,
          day: date.day
        },
        generated: new Date().toISOString(),
        source: data.source,
        dataPoints: data.data_points
      },
      probabilities: {
        rain: {
          probability: data.rain.probability,
          percentage: Math.round(data.rain.probability * 100),
          threshold: data.rain.threshold,
          unit: 'mm'
        },
        heat: {
          probability: data.heat.probability,
          percentage: Math.round(data.heat.probability * 100),
          threshold: data.heat.threshold,
          unit: '°C'
        },
        cold: {
          probability: data.cold.probability,
          percentage: Math.round(data.cold.probability * 100),
          threshold: data.cold.threshold,
          unit: '°C'
        },
        wind: {
          probability: data.wind.probability,
          percentage: Math.round(data.wind.probability * 100),
          threshold: data.wind.threshold,
          unit: 'm/s'
        }
      },
      historicalData: data.historical_data.map(item => ({
        date: item.date,
        temperature: {
          max: item.temp_max,
          min: item.temp_min
        },
        precipitation: item.precip,
        windSpeed: item.windspeed
      }))
    }

    return JSON.stringify(exportData, null, 2)
  }

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const handleCSVExport = () => {
    const csv = generateCSV()
    const filename = `weather-probability-${location?.name?.replace(/[^a-zA-Z0-9]/g, '-') || 'unknown'}-${date.month}-${date.day}.csv`
    downloadFile(csv, filename, 'text/csv')
  }

  const handleJSONExport = () => {
    const json = generateJSON()
    const filename = `weather-probability-${location?.name?.replace(/[^a-zA-Z0-9]/g, '-') || 'unknown'}-${date.month}-${date.day}.json`
    downloadFile(json, filename, 'application/json')
  }

  const copyToClipboard = async (content: string, format: string) => {
    try {
      await navigator.clipboard.writeText(content)
      // You could add a toast notification here
      console.log(`${format} data copied to clipboard`)
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }

  return (
    <div className="weather-card">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <span className="mr-2">📥</span>
        Export Data
      </h3>
      
      <div className="space-y-3">
        {/* CSV Export */}
        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
          <div className="flex items-center">
            <span className="mr-2">📄</span>
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                CSV Format
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Spreadsheet-compatible data
              </div>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleCSVExport}
              className="btn-primary text-xs py-1 px-2"
            >
              Download
            </button>
            <button
              onClick={() => copyToClipboard(generateCSV(), 'CSV')}
              className="btn-secondary text-xs py-1 px-2"
            >
              Copy
            </button>
          </div>
        </div>

        {/* JSON Export */}
        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600">
          <div className="flex items-center">
            <span className="mr-2">🗄</span>
            <div>
              <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                JSON Format
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Structured data with metadata
              </div>
            </div>
          </div>
          <div className="flex space-x-2">
            <button
              onClick={handleJSONExport}
              className="btn-primary text-xs py-1 px-2"
            >
              Download
            </button>
            <button
              onClick={() => copyToClipboard(generateJSON(), 'JSON')}
              className="btn-secondary text-xs py-1 px-2"
            >
              Copy
            </button>
          </div>
        </div>

        {/* Export Info */}
        <div className="text-xs text-gray-500 dark:text-gray-400 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3">
          <p className="mb-1">
            <strong>Export includes:</strong>
          </p>
          <ul className="space-y-1">
            <li>• Historical weather data ({data.data_points} years)</li>
            <li>• Calculated probabilities for all weather types</li>
            <li>• Location and date information</li>
            <li>• Threshold settings used for calculations</li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default ExportData
