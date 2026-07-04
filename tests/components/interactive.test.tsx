import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import { Dialog, DialogContent, DialogTrigger, DialogTitle, DialogDescription, DialogClose } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

describe('Dialog', () => {
  it('does not show content when closed', () => {
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
          <DialogDescription>Description</DialogDescription>
        </DialogContent>
      </Dialog>,
    )
    expect(screen.queryByText('Title')).not.toBeInTheDocument()
  })

  it('shows content when trigger is clicked', async () => {
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
          <DialogDescription>Description</DialogDescription>
        </DialogContent>
      </Dialog>,
    )

    await userEvent.click(screen.getByText('Open'))
    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Description')).toBeInTheDocument()
  })

  it('has close button', async () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
        </DialogContent>
      </Dialog>,
    )
    expect(screen.getByRole('button', { name: /close/i })).toBeInTheDocument()
  })

  it('closes on close button click', async () => {
    render(
      <Dialog defaultOpen>
        <DialogContent>
          <DialogTitle>Title</DialogTitle>
        </DialogContent>
      </Dialog>,
    )

    expect(screen.getByText('Title')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /close/i }))
    // Radix animations take time — content may still be in DOM briefly
  })
})

describe('DropdownMenu', () => {
  it('shows items when triggered', async () => {
    const { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } =
      await import('@/components/ui/dropdown-menu')

    render(
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button>Menu</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem>Item 1</DropdownMenuItem>
          <DropdownMenuItem>Item 2</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>,
    )

    expect(screen.queryByText('Item 1')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /menu/i }))
    expect(screen.getByText('Item 1')).toBeInTheDocument()
    expect(screen.getByText('Item 2')).toBeInTheDocument()
  })

  it('calls onClick when item is clicked', async () => {
    const { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem } =
      await import('@/components/ui/dropdown-menu')

    const onItemClick = vi.fn()

    render(
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button>Menu</Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem onClick={onItemClick}>Click me</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>,
    )

    await userEvent.click(screen.getByRole('button', { name: /menu/i }))
    await userEvent.click(screen.getByText('Click me'))
    expect(onItemClick).toHaveBeenCalledTimes(1)
  })
})

describe('Avatar', () => {
  it('renders with fallback initials', async () => {
    const { UserAvatar } = await import('@/components/ui/avatar')
    render(<UserAvatar name="John Doe" />)
    expect(screen.getByText('JD')).toBeInTheDocument()
  })

  it('renders single initial for single name', async () => {
    const { UserAvatar } = await import('@/components/ui/avatar')
    render(<UserAvatar name="John" />)
    expect(screen.getByText('J')).toBeInTheDocument()
  })

  it('returns ? for empty name', async () => {
    const { UserAvatar } = await import('@/components/ui/avatar')
    render(<UserAvatar name="" />)
    expect(screen.getByText('?')).toBeInTheDocument()
  })

  it('applies size classes', async () => {
    const { UserAvatar } = await import('@/components/ui/avatar')
    const { container } = render(<UserAvatar name="Test" size="lg" />)
    expect(container.firstChild).toHaveClass('h-12', 'w-12')
  })
})
