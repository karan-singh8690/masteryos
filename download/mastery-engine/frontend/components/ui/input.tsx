'use client'

import * as React from 'react'
import { Eye, EyeOff } from 'lucide-react'

import { cn } from '@/lib/cn'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
  hasError?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, leftIcon, rightIcon, hasError, type = 'text', ...props }, ref) => {
    return (
      <div className="relative">
        {leftIcon && (
          <div
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          >
            {leftIcon}
          </div>
        )}
        <input
          type={type}
          className={cn(
            'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background transition-colors',
            'file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground',
            'placeholder:text-muted-foreground',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            'disabled:cursor-not-allowed disabled:opacity-50',
            leftIcon && 'pl-10',
            rightIcon && 'pr-10',
            hasError && 'border-destructive focus-visible:ring-destructive',
            className,
          )}
          ref={ref}
          {...props}
        />
        {rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {rightIcon}
          </div>
        )}
      </div>
    )
  },
)
Input.displayName = 'Input'

export { Input }

// ============================================================
// Password Input (with show/hide toggle)
// ============================================================

export interface PasswordInputProps
  extends Omit<InputProps, 'type' | 'rightIcon'> {
  showToggle?: boolean
}

const PasswordInput = React.forwardRef<HTMLInputElement, PasswordInputProps>(
  ({ className, showToggle = true, hasError, ...props }, ref) => {
    const [show, setShow] = React.useState(false)

    return (
      <Input
        ref={ref}
        type={show ? 'text' : 'password'}
        className={className}
        hasError={hasError}
        rightIcon={
          showToggle ? (
            <button
              type="button"
              onClick={() => setShow((s) => !s)}
              className="hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
              aria-label={show ? 'Hide password' : 'Show password'}
              aria-pressed={show}
              tabIndex={-1}
            >
              {show ? (
                <EyeOff className="h-4 w-4" aria-hidden="true" />
              ) : (
                <Eye className="h-4 w-4" aria-hidden="true" />
              )}
            </button>
          ) : null
        }
        {...props}
      />
    )
  },
)
PasswordInput.displayName = 'PasswordInput'

export { PasswordInput }
