import React from 'react'
import { render, screen } from '@testing-library/react'
import { Droplets } from 'lucide-react'
import ProbabilityCard from '../../components/ProbabilityCard'

describe('ProbabilityCard Component', () => {
  const defaultProps = {
    type: 'rain' as const,
    label: 'Rain',
    icon: Droplets,
    probability: 0.3,
    threshold: 0.1,
    unit: 'mm',
    description: 'Chance of precipitation',
    color: '#0ea5e9',
    bgColor: 'bg-rain-50 dark:bg-rain-900/20',
    borderColor: 'border-rain-200 dark:border-rain-700'
  }

  test('renders probability card with correct information', () => {
    render(<ProbabilityCard {...defaultProps} />)
    
    expect(screen.getByText('Rain')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('> 0.1mm')).toBeInTheDocument()
    expect(screen.getByText('Chance of precipitation')).toBeInTheDocument()
  })

  test('displays correct risk level for high probability', () => {
    render(<ProbabilityCard {...defaultProps} probability={0.8} />)
    
    expect(screen.getByText('High Risk')).toBeInTheDocument()
  })

  test('displays correct risk level for medium probability', () => {
    render(<ProbabilityCard {...defaultProps} probability={0.5} />)
    
    expect(screen.getByText('Medium Risk')).toBeInTheDocument()
  })

  test('displays correct risk level for low probability', () => {
    render(<ProbabilityCard {...defaultProps} probability={0.2} />)
    
    expect(screen.getByText('Low Risk')).toBeInTheDocument()
  })

  test('renders cold threshold with correct format', () => {
    render(
      <ProbabilityCard 
        {...defaultProps} 
        type="cold"
        threshold={5}
        unit="°C"
      />
    )
    
    expect(screen.getByText('< 5°C')).toBeInTheDocument()
  })

  test('renders heat threshold with correct format', () => {
    render(
      <ProbabilityCard 
        {...defaultProps} 
        type="heat"
        threshold={35}
        unit="°C"
      />
    )
    
    expect(screen.getByText('> 35°C')).toBeInTheDocument()
  })

  test('displays interpretation text correctly', () => {
    render(<ProbabilityCard {...defaultProps} />)
    
    expect(screen.getByText(/based on historical data/i)).toBeInTheDocument()
    expect(screen.getByText(/30% chance/i)).toBeInTheDocument()
    expect(screen.getByText(/precipitation will exceed/i)).toBeInTheDocument()
  })

  test('renders with zero probability', () => {
    render(<ProbabilityCard {...defaultProps} probability={0} />)
    
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.getByText('Low Risk')).toBeInTheDocument()
  })

  test('renders with maximum probability', () => {
    render(<ProbabilityCard {...defaultProps} probability={1} />)
    
    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText('High Risk')).toBeInTheDocument()
  })

  test('renders different weather types correctly', () => {
    const windProps = {
      ...defaultProps,
      type: 'wind' as const,
      label: 'Wind',
      threshold: 15,
      unit: 'm/s'
    }
    
    render(<ProbabilityCard {...windProps} />)
    
    expect(screen.getByText('Wind')).toBeInTheDocument()
    expect(screen.getByText('> 15m/s')).toBeInTheDocument()
    expect(screen.getByText(/wind speed will exceed/i)).toBeInTheDocument()
  })
})
