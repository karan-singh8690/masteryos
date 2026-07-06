'use client'

import * as React from 'react'
import * as SwitchPrimitives from '@radix-ui/react-switch'

import { cn } from '@/lib/cn'

const Switch = React.forwardRef<
  React.ElementRef<typeof SwitchPrimitives.Root>,
  React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>
>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    className={cn(
      'peer inline-flex h-7 w-12 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-all duration-300',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
      'disabled:cursor-not-allowed disabled:opacity-50',
      // Unchecked: dark glass with subtle border
      'data-[state=unchecked]:bg-white/5 data-[state=unchecked]:border-white/10',
      // Checked: emerald gradient with glow
      'data-[state=checked]:bg-gradient-to-r data-[state=checked]:from-emerald-500 data-[state=checked]:to-teal-500',
      'data-[state=checked]:shadow-[0_0_12px_-2px_rgba(16,185,129,0.5)]',
      className,
    )}
    {...props}
    ref={ref}
  >
    <SwitchPrimitives.Thumb
      className={cn(
        'pointer-events-none block h-5 w-5 rounded-full shadow-lg ring-0 transition-all duration-300',
        'data-[state=unchecked]:bg-zinc-400 data-[state=unchecked]:translate-x-1',
        'data-[state=checked]:bg-white data-[state=checked]:translate-x-6',
        'data-[state=checked]:shadow-[0_0_8px_rgba(255,255,255,0.3)]',
      )}
    />
  </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
