'use client'

import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/cn'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg text-sm font-medium ring-offset-background transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-black font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 hover:scale-[1.02]',
        destructive:
          'bg-red-500/90 text-white shadow-lg shadow-red-500/20 hover:bg-red-500 hover:shadow-red-500/40',
        outline:
          'border border-white/15 bg-white/5 text-white backdrop-blur-sm hover:bg-white/10 hover:border-white/25',
        secondary:
          'bg-white/10 text-white backdrop-blur-sm hover:bg-white/15',
        ghost: 'text-zinc-400 hover:bg-white/5 hover:text-white',
        link: 'text-emerald-400 underline-offset-4 hover:text-emerald-300 hover:underline',
        success: 'bg-gradient-to-r from-emerald-500 to-teal-500 text-black font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-12 rounded-lg px-8 text-base',
        xl: 'h-14 rounded-xl px-10 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
  loading?: boolean
  leftIcon?: React.ReactNode
  rightIcon?: React.ReactNode
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref,
  ) => {
    const Comp = asChild ? Slot : 'button'

    // When asChild is true, Slot expects a single child element.
    // We need to wrap multiple children in a fragment or span.
    if (asChild) {
      return (
        <Comp
          className={cn(buttonVariants({ variant, size, className }))}
          ref={ref}
          disabled={disabled || loading}
          aria-busy={loading}
          aria-disabled={disabled || loading}
          {...props}
        >
          {React.cloneElement(children as React.ReactElement, {}, (
            <>
              {loading && <Loader2 className="animate-spin" aria-hidden="true" />}
              {!loading && leftIcon}
              {(children as React.ReactElement<{ children?: React.ReactNode }>).props.children}
              {!loading && rightIcon}
            </>
          ))}
        </Comp>
      )
    }

    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading}
        aria-disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 className="animate-spin" aria-hidden="true" />}
        {!loading && leftIcon}
        {children}
        {!loading && rightIcon}
      </Comp>
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
