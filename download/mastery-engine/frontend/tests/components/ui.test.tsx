import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'

describe('Card', () => {
  it('renders children', () => {
    render(
      <Card>
        <CardContent>Card content</CardContent>
      </Card>,
    )
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  it('renders all sub-components', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Title</CardTitle>
          <CardDescription>Description</CardDescription>
        </CardHeader>
        <CardContent>Content</CardContent>
        <CardFooter>Footer</CardFooter>
      </Card>,
    )
    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Description')).toBeInTheDocument()
    expect(screen.getByText('Content')).toBeInTheDocument()
    expect(screen.getByText('Footer')).toBeInTheDocument()
  })

  it('accepts custom className', () => {
    render(<Card className="custom-class" data-testid="card" />)
    expect(screen.getByTestId('card').className).toContain('custom-class')
  })
})

describe('Badge', () => {
  it('renders children', async () => {
    const { Badge } = await import('@/components/ui/badge')
    render(<Badge>New</Badge>)
    expect(screen.getByText('New')).toBeInTheDocument()
  })

  it('applies variant classes', async () => {
    const { Badge } = await import('@/components/ui/badge')
    render(<Badge variant="destructive" data-testid="badge">Error</Badge>)
    expect(screen.getByTestId('badge').className).toContain('bg-destructive')
  })
})

describe('Alert', () => {
  it('renders with title and description', async () => {
    const { Alert, AlertTitle, AlertDescription } = await import('@/components/ui/alert')
    render(
      <Alert>
        <AlertTitle>Heads up</AlertTitle>
        <AlertDescription>You can add components to your app.</AlertDescription>
      </Alert>,
    )
    expect(screen.getByText('Heads up')).toBeInTheDocument()
    expect(screen.getByText('You can add components to your app.')).toBeInTheDocument()
  })

  it('has alert role', async () => {
    const { Alert } = await import('@/components/ui/alert')
    render(<Alert>Message</Alert>)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })
})

describe('Spinner', () => {
  it('renders with status role', async () => {
    const { Spinner } = await import('@/components/ui/spinner')
    render(<Spinner />)
    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('shows label text', async () => {
    const { Spinner } = await import('@/components/ui/spinner')
    render(<Spinner label="Loading data" />)
    expect(screen.getByRole('status')).toHaveAttribute('aria-label', 'Loading data')
  })
})

describe('Skeleton', () => {
  it('renders with aria-hidden', async () => {
    const { Skeleton } = await import('@/components/ui/skeleton')
    render(<Skeleton data-testid="skeleton" />)
    expect(screen.getByTestId('skeleton')).toHaveAttribute('aria-hidden', 'true')
  })

  it('SkeletonText renders multiple lines', async () => {
    const { SkeletonText } = await import('@/components/ui/skeleton')
    const { container } = render(<SkeletonText lines={3} />)
    const skeletons = container.querySelectorAll('[aria-hidden="true"]')
    expect(skeletons).toHaveLength(3)
  })
})

describe('EmptyState', () => {
  it('renders title and description', async () => {
    const { EmptyState } = await import('@/components/ui/empty-state')
    render(
      <EmptyState
        title="No items"
        description="You haven't added any items yet."
      />,
    )
    expect(screen.getByText('No items')).toBeInTheDocument()
    expect(screen.getByText("You haven't added any items yet.")).toBeInTheDocument()
  })

  it('renders action button when provided', async () => {
    const { EmptyState } = await import('@/components/ui/empty-state')
    render(
      <EmptyState
        title="No items"
        action={{ label: 'Add item', onClick: () => {} }}
      />,
    )
    expect(screen.getByRole('button', { name: /add item/i })).toBeInTheDocument()
  })
})

describe('ErrorState', () => {
  it('renders error message', async () => {
    const { ErrorState } = await import('@/components/ui/error-state')
    render(
      <ErrorState
        title="Failed to load"
        description="Please try again later."
      />,
    )
    expect(screen.getByText('Failed to load')).toBeInTheDocument()
    expect(screen.getByText('Please try again later.')).toBeInTheDocument()
  })

  it('has alert role', async () => {
    const { ErrorState } = await import('@/components/ui/error-state')
    render(<ErrorState />)
    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  it('renders retry button when onRetry provided', async () => {
    const { ErrorState } = await import('@/components/ui/error-state')
    render(<ErrorState onRetry={() => {}} />)
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })
})
