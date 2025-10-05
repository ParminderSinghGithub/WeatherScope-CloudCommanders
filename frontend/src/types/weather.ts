export interface WeatherData {
  date: string
  temp_max: number
  temp_min: number
  precip: number
  windspeed: number
}

export interface ProbabilityResponse {
  probability: number
  source: string
  threshold: number
  data_points: number
  location: {
    lat: number
    lon: number
  }
  date: {
    month: number
    day: number
  }
}

export interface ProbabilityData {
  rain: {
    probability: number
    threshold: number
  }
  heat: {
    probability: number
    threshold: number
  }
  cold: {
    probability: number
    threshold: number
  }
  wind: {
    probability: number
    threshold: number
  }
  source: string
  data_points: number
  location: {
    lat: number
    lon: number
  }
  date: {
    month: number
    day: number
  }
  historical_data: WeatherData[]
}

export interface LocationData {
  lat: number
  lon: number
  name: string
  country?: string
  state?: string
}

export interface FetchProbabilitiesParams {
  lat: number
  lon: number
  month: number
  day: number
  rainThreshold: number
  heatThreshold: number
  coldThreshold: number
  windThreshold: number
}

export interface DateSelection {
  month: number
  day: number
}

export interface ThresholdSettings {
  rain: number
  heat: number
  cold: number
  wind: number
}
