import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip'
import { Button } from '@/components/ui/button'

describe('Tooltip', () => {
  it('does not show content by default', () => {
    render(
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button>Hover me</Button>
          </TooltipTrigger>
          <TooltipContent>Tooltip text</TooltipContent>
        </Tooltip>
      </TooltipProvider>,
    )
    expect(screen.queryByText('Tooltip text')).not.toBeInTheDocument()
  })
})

describe('Sheet', () => {
  it('does not show content when closed', () => {
    const { Sheet, SheetTrigger, SheetContent, SheetTitle } = require('@/components/ui/sheet')
    render(
      <Sheet>
        <SheetTrigger>Open</SheetTrigger>
        <SheetContent>
          <SheetTitle>Sheet Title</SheetTitle>
        </SheetContent>
      </Sheet>,
    )
    expect(screen.queryByText('Sheet Title')).not.toBeInTheDocument()
  })

  it('shows content when trigger clicked', async () => {
    const { Sheet, SheetTrigger, SheetContent, SheetTitle } = require('@/components/ui/sheet')
    render(
      <Sheet>
        <SheetTrigger>Open</SheetTrigger>
        <SheetContent>
          <SheetTitle>Sheet Title</SheetTitle>
        </SheetContent>
      </Sheet>,
    )
    await userEvent.click(screen.getByText('Open'))
    expect(screen.getByText('Sheet Title')).toBeInTheDocument()
  })
})

describe('Select', () => {
  it('renders trigger', () => {
    const { Select, SelectTrigger, SelectValue } = require('@/components/ui/select')
    render(
      <Select defaultValue="a">
        <SelectTrigger>
          <SelectValue placeholder="Choose" />
        </SelectTrigger>
      </Select>,
    )
    expect(screen.getByText('Choose')).toBeInTheDocument()
  })
})

describe('Card sub-components', () => {
  it('CardHeader renders with padding', async () => {
    const { Card, CardHeader } = await import('@/components/ui/card')
    const { container } = render(
      <Card>
        <CardHeader>Header</CardHeader>
      </Card>,
    )
    expect(container.querySelector('.p-6')).toBeInTheDocument()
  })

  it('CardTitle renders as h3', async () => {
    const { Card, CardTitle } = await import('@/components/ui/card')
    render(
      <Card>
        <CardTitle>My Title</CardTitle>
      </Card>,
    )
    const heading = screen.getByText('My Title')
    expect(heading.tagName).toBe('H3')
  })

  it('CardDescription renders as p', async () => {
    const { Card, CardDescription } = await import('@/components/ui/card')
    render(
      <Card>
        <CardDescription>Description text</CardDescription>
      </Card>,
    )
    const desc = screen.getByText('Description text')
    expect(desc.tagName).toBe('P')
  })

  it('CardFooter renders with flex', async () => {
    const { Card, CardFooter } = await import('@/components/ui/card')
    const { container } = render(
      <Card>
        <CardFooter>Footer</CardFooter>
      </Card>,
    )
    expect(container.querySelector('.flex.items-center')).toBeInTheDocument()
  })
})

describe('Spinner variants', () => {
  it('renders different sizes', async () => {
    const { Spinner } = await import('@/components/ui/spinner')
    const { rerender } = render(<Spinner size="xs" data-testid="spinner" />)
    expect(screen.getByTestId('spinner').className).toContain('h-3')

    rerender(<Spinner size="sm" data-testid="spinner" />)
    expect(screen.getByTestId('spinner').className).toContain('h-4')

    rerender(<Spinner size="md" data-testid="spinner" />)
    expect(screen.getByTestId('spinner').className).toContain('h-6')

    rerender(<Spinner size="lg" data-testid="spinner" />)
    expect(screen.getByTestId('spinner').className).toContain('h-8')

    rerender(<Spinner size="xl" data-testid="spinner" />)
    expect(screen.getByTestId('spinner').className).toContain('h-12')
  })

  it('FullPageSpinner renders', async () => {
    const { FullPageSpinner } = await import('@/components/ui/spinner')
    render(<FullPageSpinner label="Loading app" />)
    expect(screen.getByText('Loading app')).toBeInTheDocument()
  })

  it('CenteredSpinner renders', async () => {
    const { CenteredSpinner } = await import('@/components/ui/spinner')
    render(<CenteredSpinner label="Loading data" />)
    expect(screen.getByText('Loading data')).toBeInTheDocument()
  })
})

describe('Skeleton variants', () => {
  it('SkeletonCard renders', async () => {
    const { SkeletonCard } = await import('@/components/ui/skeleton')
    const { container } = render(<SkeletonCard />)
    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll('[aria-hidden="true"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('SkeletonText renders default 3 lines', async () => {
    const { SkeletonText } = await import('@/components/ui/skeleton')
    const { container } = render(<SkeletonText />)
    const skeletons = container.querySelectorAll('[aria-hidden="true"]')
    expect(skeletons).toHaveLength(3)
  })

  it('SkeletonText renders custom line count', async () => {
    const { SkeletonText } = await import('@/components/ui/skeleton')
    const { container } = render(<SkeletonText lines={5} />)
    const skeletons = container.querySelectorAll('[aria-hidden="true"]')
    expect(skeletons).toHaveLength(5)
  })
})

describe('Badge variants', () => {
  it.each([
    ['default', 'bg-primary'],
    ['secondary', 'bg-secondary'],
    ['destructive', 'bg-destructive'],
    ['success', 'bg-success'],
    ['warning', 'bg-warning'],
    ['outline', 'text-foreground'],
  ])('renders %s variant', async (variant, expectedClass) => {
    const { Badge } = await import('@/components/ui/badge')
    render(
      <Badge variant={variant as any} data-testid="badge">
        Test
      </Badge>,
    )
    expect(screen.getByTestId('badge').className).toContain(expectedClass)
  })
})

describe('Alert variants', () => {
  it.each([
    ['info'],
    ['success'],
    ['warning'],
    ['destructive'],
  ])('renders %s variant with icon', async (variant) => {
    const { Alert, AlertDescription } = await import('@/components/ui/alert')
    render(
      <Alert variant={variant as any}>
        <AlertDescription>Message</AlertDescription>
      </Alert>,
    )
    expect(screen.getByText('Message')).toBeInTheDocument()
  })

  it('hides icon when icon=false', async () => {
    const { Alert } = await import('@/components/ui/alert')
    render(
      <Alert icon={false}>
        <span>No icon alert</span>
      </Alert>,
    )
    expect(screen.getByText('No icon alert')).toBeInTheDocument()
  })
})

describe('Button variants', () => {
  it.each([
    ['default', 'bg-primary'],
    ['destructive', 'bg-destructive'],
    ['outline', 'border'],
    ['secondary', 'bg-secondary'],
    ['ghost', 'hover:bg-accent'],
    ['link', 'underline'],
    ['success', 'bg-success'],
  ])('renders %s variant', (variant, expectedClass) => {
    render(
      <Button variant={variant as any} data-testid="btn">
        Test
      </Button>,
    )
    expect(screen.getByTestId('btn').className).toContain(expectedClass)
  })
})

describe('Button sizes', () => {
  it.each([
    ['sm', 'h-9'],
    ['default', 'h-10'],
    ['lg', 'h-11'],
    ['xl', 'h-12'],
    ['icon', 'h-10 w-10'],
  ])('renders %s size', (size, expectedClass) => {
    render(
      <Button size={size as any} data-testid="btn">
        {size === 'icon' ? 'X' : 'Test'}
      </Button>,
    )
    expect(screen.getByTestId('btn').className).toContain(expectedClass)
  })
})
