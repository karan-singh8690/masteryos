import { describe, it, expect } from 'vitest'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert } from '@/components/ui/alert'
import { Spinner } from '@/components/ui/spinner'
import { Skeleton } from '@/components/ui/skeleton'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Checkbox } from '@/components/ui/checkbox'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { EmptyState } from '@/components/ui/empty-state'
import { ErrorState } from '@/components/ui/error-state'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { Pagination } from '@/components/ui/pagination'
import { Textarea } from '@/components/ui/textarea'
import { Avatar, UserAvatar } from '@/components/ui/avatar'
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip'
import { Dialog, DialogTrigger, DialogContent, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Sheet, SheetTrigger, SheetContent } from '@/components/ui/sheet'
import { Select, SelectTrigger, SelectContent, SelectItem, SelectValue } from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from '@/components/ui/dropdown-menu'

describe('Component exports', () => {
  it('all UI components are exported', () => {
    // These will throw if the component doesn't export correctly
    expect(Button).toBeDefined()
    expect(Input).toBeDefined()
    expect(Card).toBeDefined()
    expect(Badge).toBeDefined()
    expect(Alert).toBeDefined()
    expect(Spinner).toBeDefined()
    expect(Skeleton).toBeDefined()
    expect(Label).toBeDefined()
    expect(Separator).toBeDefined()
    expect(Checkbox).toBeDefined()
    expect(Switch).toBeDefined()
    expect(Tabs).toBeDefined()
    expect(TabsList).toBeDefined()
    expect(TabsTrigger).toBeDefined()
    expect(TabsContent).toBeDefined()
    expect(Progress).toBeDefined()
    expect(EmptyState).toBeDefined()
    expect(ErrorState).toBeDefined()
    expect(Breadcrumb).toBeDefined()
    expect(Pagination).toBeDefined()
    expect(Textarea).toBeDefined()
    expect(Avatar).toBeDefined()
    expect(UserAvatar).toBeDefined()
    expect(Tooltip).toBeDefined()
    expect(TooltipProvider).toBeDefined()
    expect(TooltipTrigger).toBeDefined()
    expect(TooltipContent).toBeDefined()
    expect(Dialog).toBeDefined()
    expect(DialogTrigger).toBeDefined()
    expect(DialogContent).toBeDefined()
    expect(DialogTitle).toBeDefined()
    expect(DialogDescription).toBeDefined()
    expect(Sheet).toBeDefined()
    expect(SheetTrigger).toBeDefined()
    expect(SheetContent).toBeDefined()
    expect(Select).toBeDefined()
    expect(SelectTrigger).toBeDefined()
    expect(SelectContent).toBeDefined()
    expect(SelectItem).toBeDefined()
    expect(SelectValue).toBeDefined()
    expect(DropdownMenu).toBeDefined()
    expect(DropdownMenuTrigger).toBeDefined()
    expect(DropdownMenuContent).toBeDefined()
    expect(DropdownMenuItem).toBeDefined()
  })
})

describe('Form exports', () => {
  it('form components are exported', async () => {
    const form = await import('@/components/forms/form')
    expect(form.Form).toBeDefined()
    expect(form.FormItem).toBeDefined()
    expect(form.FormLabel).toBeDefined()
    expect(form.FormControl).toBeDefined()
    expect(form.FormDescription).toBeDefined()
    expect(form.FormMessage).toBeDefined()
    expect(form.FormField).toBeDefined()
    expect(form.useFormField).toBeDefined()
    expect(form.mapServerErrorsToForm).toBeDefined()
  })

  it('password strength meter is exported', async () => {
    const meter = await import('@/components/forms/password-strength-meter')
    expect(meter.PasswordStrengthMeter).toBeDefined()
  })
})

describe('Layout exports', () => {
  it('layout components are exported', async () => {
    const appLayout = await import('@/components/layout/app-layout')
    expect(appLayout.AppLayout).toBeDefined()

    const authLayout = await import('@/components/layout/auth-layout')
    expect(authLayout.AuthLayout).toBeDefined()

    const publicLayout = await import('@/components/layout/public-layout')
    expect(publicLayout.PublicLayout).toBeDefined()

    const header = await import('@/components/layout/header')
    expect(header.Header).toBeDefined()

    const sidebar = await import('@/components/layout/sidebar')
    expect(sidebar.Sidebar).toBeDefined()

    const profileMenu = await import('@/components/layout/profile-menu')
    expect(profileMenu.ProfileMenu).toBeDefined()

    const notificationMenu = await import('@/components/layout/notification-menu')
    expect(notificationMenu.NotificationMenu).toBeDefined()

    const routeProtection = await import('@/components/layout/route-protection')
    expect(routeProtection.ProtectedRoute).toBeDefined()
    expect(routeProtection.PermissionGuard).toBeDefined()
    expect(routeProtection.RoleGuard).toBeDefined()

    const themeToggle = await import('@/components/layout/theme-toggle')
    expect(themeToggle.ThemeToggle).toBeDefined()
  })
})
