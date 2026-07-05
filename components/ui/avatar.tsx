'use client'

import * as React from 'react'
import * as AvatarPrimitive from '@radix-ui/react-avatar'

import { cn } from '@/lib/cn'
import { getInitials } from '@/lib/format'
import { generateAvatar } from '@/lib/avatar'

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn(
      'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full',
      className,
    )}
    {...props}
  />
))
Avatar.displayName = AvatarPrimitive.Root.displayName

const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn('aspect-square h-full w-full', className)}
    {...props}
  />
))
AvatarImage.displayName = AvatarPrimitive.Image.displayName

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center rounded-full bg-muted text-sm font-medium',
      className,
    )}
    {...props}
  />
))
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName

interface UserAvatarProps {
  name: string
  src?: string | null
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

const sizeMap = {
  sm: 'h-8 w-8 text-xs',
  md: 'h-10 w-10 text-sm',
  lg: 'h-12 w-12 text-base',
  xl: 'h-16 w-16 text-lg',
}

export function UserAvatar({ name, src, size = 'md', className }: UserAvatarProps) {
  return (
    <Avatar className={cn(sizeMap[size], className)}>
      {src && <AvatarImage src={src} alt={name} />}
      <AvatarFallback>{getInitials(name)}</AvatarFallback>
    </Avatar>
  )
}

interface GradientAvatarProps {
  /** Email used to deterministically pick a gradient and derive initials. */
  email: string
  /** Optional display name. When provided, its initials take precedence. */
  name?: string
  /** Optional avatar image URL. When provided, renders a `UserAvatar` instead. */
  src?: string | null
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}

/**
 * Renders a circular avatar with a deterministic gradient background and
 * centered initials derived from the email (or an optional name).
 *
 * If `src` is provided, falls back to the standard `UserAvatar` so that
 * uploaded profile pictures take priority over generated gradients.
 */
export function GradientAvatar({
  email,
  name,
  src,
  size = 'md',
  className,
}: GradientAvatarProps) {
  if (src) {
    return <UserAvatar name={name || email} src={src} size={size} className={className} />
  }

  const generated = generateAvatar(email)
  const initials = name ? getInitials(name) : generated.initials
  const displayName = name || email

  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-full font-semibold text-white shadow-sm select-none',
        sizeMap[size],
        className,
      )}
      style={{ backgroundImage: generated.gradient }}
      role="img"
      aria-label={displayName ? `Avatar for ${displayName}` : 'User avatar'}
    >
      <span aria-hidden="true">{initials}</span>
    </div>
  )
}

export { Avatar, AvatarImage, AvatarFallback }
