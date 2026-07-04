import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
  FormDescription,
} from '@/components/forms/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

const testSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().email('Invalid email'),
})

type TestFormData = z.infer<typeof testSchema>

function TestForm({ onSubmit }: { onSubmit: (data: TestFormData) => void }) {
  const form = useForm<TestFormData>({
    resolver: zodResolver(testSchema),
    defaultValues: { name: '', email: '' },
  })

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input type="email" {...field} />
              </FormControl>
              <FormDescription>We&apos;ll never share your email.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Submit</Button>
      </form>
    </Form>
  )
}

describe('Form components', () => {
  it('renders form with fields', () => {
    render(<TestForm onSubmit={() => {}} />)
    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /submit/i })).toBeInTheDocument()
  })

  it('shows description text', () => {
    render(<TestForm onSubmit={() => {}} />)
    expect(screen.getByText(/we'll never share your email/i)).toBeInTheDocument()
  })

  it('shows validation errors on submit', async () => {
    render(<TestForm onSubmit={() => {}} />)
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))

    expect(screen.getByText('Name must be at least 2 characters')).toBeInTheDocument()
    expect(screen.getByText('Invalid email')).toBeInTheDocument()
  })

  it('submits valid data', async () => {
    const onSubmit = vi.fn()
    render(<TestForm onSubmit={onSubmit} />)

    await userEvent.type(screen.getByLabelText('Name'), 'John')
    await userEvent.type(screen.getByLabelText('Email'), 'john@example.com')
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))

    expect(onSubmit).toHaveBeenCalledWith({
      name: 'John',
      email: 'john@example.com',
    })
  })

  it('shows error for invalid email', async () => {
    render(<TestForm onSubmit={() => {}} />)

    await userEvent.type(screen.getByLabelText('Name'), 'John')
    await userEvent.type(screen.getByLabelText('Email'), 'not-an-email')
    await userEvent.click(screen.getByRole('button', { name: /submit/i }))

    expect(screen.getByText('Invalid email')).toBeInTheDocument()
  })

  it('associates label with input', () => {
    render(<TestForm onSubmit={() => {}} />)
    const nameInput = screen.getByLabelText('Name')
    expect(nameInput).toHaveAttribute('id')
  })
})

describe('mapServerErrorsToForm', () => {
  it('maps field errors to form', async () => {
    const { mapServerErrorsToForm } = await import('@/components/forms/form')
    const setError = vi.fn()

    mapServerErrorsToForm<{ name: string; email: string }>(
      {
        name: ['Name too short'],
        email: ['Already exists', 'Invalid format'],
      },
      setError,
    )

    expect(setError).toHaveBeenCalledWith('name', {
      type: 'server',
      message: 'Name too short',
    })
    expect(setError).toHaveBeenCalledWith('email', {
      type: 'server',
      message: 'Already exists',
    })
  })

  it('skips empty field errors', async () => {
    const { mapServerErrorsToForm } = await import('@/components/forms/form')
    const setError = vi.fn()

    mapServerErrorsToForm(
      { name: [], email: ['Error'] },
      setError,
    )

    expect(setError).toHaveBeenCalledTimes(1)
    expect(setError).toHaveBeenCalledWith('email', expect.any(Object))
  })
})
