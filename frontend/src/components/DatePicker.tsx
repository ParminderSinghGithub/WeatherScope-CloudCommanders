import * as React from 'react'
import { DateSelection } from '../types/weather'

interface DatePickerProps {
  selectedDate: DateSelection
  onDateChange: (date: DateSelection) => void
}

const months = [
  { value: 1, name: 'January', short: 'Jan' },
  { value: 2, name: 'February', short: 'Feb' },
  { value: 3, name: 'March', short: 'Mar' },
  { value: 4, name: 'April', short: 'Apr' },
  { value: 5, name: 'May', short: 'May' },
  { value: 6, name: 'June', short: 'Jun' },
  { value: 7, name: 'July', short: 'Jul' },
  { value: 8, name: 'August', short: 'Aug' },
  { value: 9, name: 'September', short: 'Sep' },
  { value: 10, name: 'October', short: 'Oct' },
  { value: 11, name: 'November', short: 'Nov' },
  { value: 12, name: 'December', short: 'Dec' }
]

const getDaysInMonth = (month: number): number => {
  // Using 2024 as a leap year reference
  const daysInMonth = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
  return daysInMonth[month - 1]
}

const DatePicker: React.FC<DatePickerProps> = ({ selectedDate, onDateChange }) => {
  const handleMonthChange = (month: number) => {
    const maxDay = getDaysInMonth(month)
    const newDay = selectedDate.day > maxDay ? maxDay : selectedDate.day
    onDateChange({ month, day: newDay })
  }

  const handleDayChange = (day: number) => {
    onDateChange({ ...selectedDate, day })
  }

  const getQuickDateOptions = () => {
    const today = new Date()
    const currentMonth = today.getMonth() + 1
    const currentDay = today.getDate()
    
    return [
      { label: 'Today', month: currentMonth, day: currentDay },
      { label: 'New Year', month: 1, day: 1 },
      { label: 'Valentine\'s Day', month: 2, day: 14 },
      { label: 'Independence Day', month: 7, day: 4 },
      { label: 'Halloween', month: 10, day: 31 },
      { label: 'Christmas', month: 12, day: 25 }
    ]
  }

  return (
    <div className="weather-card">
      <h3 className="text-lg font-semibold mb-4 flex items-center">
        <span className="mr-2">📅</span>
        Date
      </h3>
      
      <div className="space-y-4">
        {/* Month and Day Selectors */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Month
            </label>
            <select
              value={selectedDate.month}
              onChange={(e) => handleMonthChange(parseInt(e.target.value))}
              className="input-field"
            >
              {months.map((month) => (
                <option key={month.value} value={month.value}>
                  {month.name}
                </option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Day
            </label>
            <select
              value={selectedDate.day}
              onChange={(e) => handleDayChange(parseInt(e.target.value))}
              className="input-field"
            >
              {Array.from({ length: getDaysInMonth(selectedDate.month) }, (_, i) => i + 1).map((day) => (
                <option key={day} value={day}>
                  {day}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Selected Date Display */}
        <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg p-3">
          <div className="text-center">
            <div className="text-lg font-semibold text-blue-800 dark:text-blue-200">
              {months[selectedDate.month - 1].name} {selectedDate.day}
            </div>
            <div className="text-sm text-blue-600 dark:text-blue-400">
              Historical data for this date across multiple years
            </div>
          </div>
        </div>

        {/* Quick Date Options */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Quick Select
          </label>
          <div className="grid grid-cols-2 gap-2">
            {getQuickDateOptions().map((option, index) => (
              <button
                key={option.label}
                onClick={() => onDateChange({ month: option.month, day: option.day })}
                className={`text-xs py-2 px-3 rounded-lg border transition-colors ${
                  selectedDate.month === option.month && selectedDate.day === option.day
                    ? 'bg-blue-100 dark:bg-blue-900/50 border-blue-300 dark:border-blue-600 text-blue-800 dark:text-blue-200'
                    : 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        {/* Date Info */}
        <div className="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
          <p className="mb-1">
            <strong>Note:</strong> We analyze historical weather data for this specific date across the past 10 years.
          </p>
          <p>
            Results show the probability of weather conditions occurring on {months[selectedDate.month - 1].name} {selectedDate.day} based on historical patterns.
          </p>
        </div>
      </div>
    </div>
  )
}

export default DatePicker
