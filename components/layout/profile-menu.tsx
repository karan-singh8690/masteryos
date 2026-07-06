'use client'

import * as React from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { LogOut, Settings, User as UserIcon, Shield, ChevronDown } from 'lucide-react'

import { useAuth } from '@/providers/auth-provider'
import { ROUTES } from '@/lib/constants'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { getInitials } from '@/lib/format'

export function ProfileMenu() {
  const { user, logout } = useAuth()
  const router = useRouter()

  if (!user) return null

  const profile = user.profile

  const handleLogout = async () => {
    await logout(false)
  }

  const handleLogoutAll = async () => {
    await logout(true)
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="flex items-center gap-2 px-2">
          <Avatar className="h-8 w-8">
            {profile.avatar_url && <AvatarImage src={profile.avatar_url} alt={profile.display_name} />}
            <AvatarFallback className="text-xs">
              {getInitials(profile.display_name)}
            </AvatarFallback>
          </Avatar>
          <span className="hidden text-sm font-medium sm:inline-block">
            {profile.display_name}
          </span>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col gap-1">
          <span className="font-medium">{profile.display_name}</span>
          <span className="text-xs text-muted-foreground">{user.user.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push(ROUTES.PROFILE)}>
          <UserIcon className="mr-2 h-4 w-4" />
          Profile
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push(ROUTES.SECURITY)}>
          <Shield className="mr-2 h-4 w-4" />
          Security
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push(ROUTES.SETTINGS)}>
          <Settings className="mr-2 h-4 w-4" />
          Settings
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
        <DropdownMenuItem onClick={handleLogoutAll} className="text-destructive">
          <LogOut className="mr-2 h-4 w-4" />
          Log out all devices
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
