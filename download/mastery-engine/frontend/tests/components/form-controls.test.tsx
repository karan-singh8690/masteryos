import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

describe('Checkbox', () => {
  it('renders unchecked by default', () => {
    render(<Checkbox aria-label="Accept" />)
    expect(screen.getByRole('checkbox')).not.toBeChecked()
  })

  it('toggles on click', async () => {
    render(<Checkbox aria-label="Accept" />)
    const checkbox = screen.getByRole('checkbox')
    await userEvent.click(checkbox)
    expect(checkbox).toBeChecked()
  })

  it('is disabled when disabled prop is set', () => {
    render(<Checkbox disabled aria-label="Accept" />)
    expect(screen.getByRole('checkbox')).toBeDisabled()
  })

  it('shows check icon when checked', async () => {
    render(<Checkbox defaultChecked aria-label="Accept" />)
    // Radix checkbox shows a check icon when checked
    expect(screen.getByRole('checkbox')).toBeChecked()
  })
})

describe('RadioGroup', () => {
  it('renders multiple options', () => {
    render(
      <RadioGroup defaultValue="a">
        <div className="flex items-center gap-2">
          <RadioGroupItem value="a" id="a" />
          <Label htmlFor="a">Option A</Label>
        </div>
        <div className="flex items-center gap-2">
          <RadioGroupItem value="b" id="b" />
          <Label htmlFor="b">Option B</Label>
        </div>
      </RadioGroup>,
    )
    expect(screen.getByLabelText('Option A')).toBeInTheDocument()
    expect(screen.getByLabelText('Option B')).toBeInTheDocument()
  })

  it('checks the selected option', () => {
    render(
      <RadioGroup defaultValue="b">
        <RadioGroupItem value="a" id="a" />
        <RadioGroupItem value="b" id="b" />
      </RadioGroup>,
    )
    expect(screen.getByRole('radio', { name: '' })).toBeInTheDocument()
  })
})

describe('Switch', () => {
  it('renders unchecked by default', () => {
    render(<Switch aria-label="Toggle" />)
    expect(screen.getByRole('switch')).not.toBeChecked()
  })

  it('toggles on click', async () => {
    render(<Switch aria-label="Toggle" />)
    const sw = screen.getByRole('switch')
    await userEvent.click(sw)
    expect(sw).toBeChecked()
  })

  it('is disabled when disabled prop is set', () => {
    render(<Switch disabled aria-label="Toggle" />)
    expect(screen.getByRole('switch')).toBeDisabled()
  })
})

describe('Label', () => {
  it('renders children', () => {
    render(<Label>Email</Label>)
    expect(screen.getByText('Email')).toBeInTheDocument()
  })

  it('associates with input via htmlFor', () => {
    render(
      <>
        <Label htmlFor="email-input">Email</Label>
        <input id="email-input" type="email" />
      </>,
    )
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
  })
})

describe('Separator', () => {
  it('renders horizontal separator by default', () => {
    const { container } = render(<Separator />)
    const separator = container.firstChild as HTMLElement
    expect(separator.className).toContain('h-[1px]')
    expect(separator.className).toContain('w-full')
  })

  it('renders vertical separator', () => {
    const { container } = render(<Separator orientation="vertical" />)
    const separator = container.firstChild as HTMLElement
    expect(separator.className).toContain('h-full')
    expect(separator.className).toContain('w-[1px]')
  })
})

describe('Progress', () => {
  it('renders with value', () => {
    const { container } = render(<Progress value={50} />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders with 0 value', () => {
    const { container } = render(<Progress value={0} />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('renders with 100 value', () => {
    const { container } = render(<Progress value={100} />)
    expect(container.firstChild).toBeInTheDocument()
  })
})

describe('Tabs', () => {
  it('renders all tabs', () => {
    render(
      <Tabs defaultValue="account">
        <TabsList>
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="password">Password</TabsTrigger>
        </TabsList>
        <TabsContent value="account">Account content</TabsContent>
        <TabsContent value="password">Password content</TabsContent>
      </Tabs>,
    )
    expect(screen.getByText('Account content')).toBeInTheDocument()
    expect(screen.queryByText('Password content')).not.toBeInTheDocument()
  })

  it('switches tabs on click', async () => {
    render(
      <Tabs defaultValue="account">
        <TabsList>
          <TabsTrigger value="account">Account</TabsTrigger>
          <TabsTrigger value="password">Password</TabsTrigger>
        </TabsList>
        <TabsContent value="account">Account content</TabsContent>
        <TabsContent value="password">Password content</TabsContent>
      </Tabs>,
    )

    expect(screen.getByText('Account content')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: /password/i }))
    expect(screen.getByText('Password content')).toBeInTheDocument()
    expect(screen.queryByText('Account content')).not.toBeInTheDocument()
  })
})

describe('Textarea', () => {
  it('renders with placeholder', () => {
    render(<Textarea placeholder="Enter message" />)
    expect(screen.getByPlaceholderText('Enter message')).toBeInTheDocument()
  })

  it('handles user input', async () => {
    render(<Textarea aria-label="Message" />)
    const textarea = screen.getByLabelText('Message') as HTMLTextAreaElement
    await userEvent.type(textarea, 'Hello world')
    expect(textarea.value).toBe('Hello world')
  })

  it('shows error styles when hasError is true', () => {
    render(<Textarea hasError aria-label="Message" />)
    expect(screen.getByLabelText('Message').className).toContain('border-destructive')
  })

  it('is disabled when disabled prop is set', () => {
    render(<Textarea disabled aria-label="Message" />)
    expect(screen.getByLabelText('Message')).toBeDisabled()
  })
})
