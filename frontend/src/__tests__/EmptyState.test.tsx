import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { EmptyState, ErrorState } from '../components/common/EmptyState'

describe('EmptyState Component', () => {
  it('renders title and description correctly', () => {
    render(
      <MemoryRouter>
        <EmptyState
          title="No Projects Found"
          description="Get started by importing your first code repository."
        />
      </MemoryRouter>
    )

    expect(screen.getByText('No Projects Found')).toBeDefined()
    expect(screen.getByText('Get started by importing your first code repository.')).toBeDefined()
  })

  it('renders action button and triggers onAction callback when clicked', () => {
    const handleAction = vi.fn()
    render(
      <MemoryRouter>
        <EmptyState
          title="No Issues Detected"
          actionLabel="Run Scan"
          onAction={handleAction}
        />
      </MemoryRouter>
    )

    const button = screen.getByText('Run Scan')
    expect(button).toBeDefined()
    fireEvent.click(button)
    expect(handleAction).toHaveBeenCalledTimes(1)
  })

  it('renders link when actionHref is provided', () => {
    render(
      <MemoryRouter>
        <EmptyState
          title="Empty Codebase"
          actionLabel="New Project"
          actionHref="/projects/new"
        />
      </MemoryRouter>
    )

    const link = screen.getByText('New Project').closest('a')
    expect(link?.getAttribute('href')).toBe('/projects/new')
  })
})

describe('ErrorState Component', () => {
  it('renders error message and retry button', () => {
    const handleRetry = vi.fn()
    render(
      <ErrorState
        title="Failed to Load Quality Report"
        message="Network error connecting to analysis backend."
        onRetry={handleRetry}
      />
    )

    expect(screen.getByText('Failed to Load Quality Report')).toBeDefined()
    expect(screen.getByText('Network error connecting to analysis backend.')).toBeDefined()

    const retryBtn = screen.getByText('Try Again')
    fireEvent.click(retryBtn)
    expect(handleRetry).toHaveBeenCalledTimes(1)
  })
})
