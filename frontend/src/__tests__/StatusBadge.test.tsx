import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { StatusBadge } from '../components/common/StatusBadge'

describe('StatusBadge Component', () => {
  it('renders with critical severity styling', () => {
    const { container } = render(<StatusBadge status="CRITICAL" variant="critical" />)
    expect(screen.getByText('CRITICAL')).toBeDefined()
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('text-rose-400')
    expect(badge?.className).toContain('bg-rose-500/10')
  })

  it('renders with high severity styling', () => {
    const { container } = render(<StatusBadge status="HIGH" variant="high" />)
    expect(screen.getByText('HIGH')).toBeDefined()
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('text-orange-400')
    expect(badge?.className).toContain('bg-orange-500/10')
  })

  it('renders with medium severity styling', () => {
    const { container } = render(<StatusBadge status="MEDIUM" variant="medium" />)
    expect(screen.getByText('MEDIUM')).toBeDefined()
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('text-amber-400')
    expect(badge?.className).toContain('bg-amber-500/10')
  })

  it('renders with ready and completed green styling', () => {
    const { container } = render(<StatusBadge status="READY" variant="ready" />)
    expect(screen.getByText('READY')).toBeDefined()
    const badge = container.querySelector('span')
    expect(badge?.className).toContain('text-emerald-400')
    expect(badge?.className).toContain('bg-emerald-500/10')
  })

  it('renders without dot indicator when showDot is false', () => {
    const { container } = render(<StatusBadge status="INFO" showDot={false} />)
    const dot = container.querySelector('.rounded-full')
    expect(dot).toBeNull()
  })
})
