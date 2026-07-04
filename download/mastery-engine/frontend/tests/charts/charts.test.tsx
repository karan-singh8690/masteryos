import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

import { TrendChart, ActivityBarChart, MasteryDonut, Sparkline } from '@/components/charts'

describe('Chart components', () => {
  describe('TrendChart', () => {
    it('renders with data', () => {
      const data = [
        { date: '2024-01-01', value: 50 },
        { date: '2024-01-02', value: 60 },
        { date: '2024-01-03', value: 70 },
      ]
      render(<TrendChart data={data} title="Mastery" />)
      expect(screen.getByText('Mastery')).toBeInTheDocument()
    })

    it('shows empty state for no data', () => {
      render(<TrendChart data={[]} title="Test" />)
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })
  })

  describe('ActivityBarChart', () => {
    it('renders with data', () => {
      const data = [
        { label: 'Mon', value: 10 },
        { label: 'Tue', value: 20 },
        { label: 'Wed', value: 15 },
      ]
      render(<ActivityBarChart data={data} title="Activity" />)
      expect(screen.getByText('Activity')).toBeInTheDocument()
    })

    it('shows empty state for no data', () => {
      render(<ActivityBarChart data={[]} title="Test" />)
      expect(screen.getByText('No data available')).toBeInTheDocument()
    })
  })

  describe('MasteryDonut', () => {
    it('renders with percentage', () => {
      const { container } = render(<MasteryDonut value={75} label="Mastered" />)
      expect(screen.getByText('75%')).toBeInTheDocument()
      expect(screen.getByText('Mastered')).toBeInTheDocument()
    })

    it('renders with custom size', () => {
      const { container } = render(<MasteryDonut value={50} size={200} />)
      expect(container.firstChild).toHaveStyle({ width: '200px', height: '200px' })
    })

    it('renders 0% correctly', () => {
      render(<MasteryDonut value={0} />)
      expect(screen.getByText('0%')).toBeInTheDocument()
    })

    it('renders 100% correctly', () => {
      render(<MasteryDonut value={100} />)
      expect(screen.getByText('100%')).toBeInTheDocument()
    })
  })

  describe('Sparkline', () => {
    it('renders with data', () => {
      const { container } = render(<Sparkline data={[10, 20, 15, 25, 30]} />)
      expect(container.firstChild).toBeInTheDocument()
    })

    it('returns null for empty data', () => {
      const { container } = render(<Sparkline data={[]} />)
      expect(container).toBeEmptyDOMElement()
    })
  })
})
