# Design System

> 24+ reusable, accessible, dark-mode-ready components.

## Components

| Component | File | Purpose |
|---|---|---|
| Button | `components/ui/button.tsx` | Primary action button (7 variants, 5 sizes) |
| Input | `components/ui/input.tsx` | Text input with left/right icons + error state |
| PasswordInput | `components/ui/input.tsx` | Password input with show/hide toggle |
| Textarea | `components/ui/textarea.tsx` | Multi-line text input |
| Label | `components/ui/label.tsx` | Form label |
| Checkbox | `components/ui/checkbox.tsx` | Checkbox |
| RadioGroup | `components/ui/radio-group.tsx` | Radio button group |
| Select | `components/ui/select.tsx` | Dropdown select |
| Switch | `components/ui/switch.tsx` | Toggle switch |
| Dialog | `components/ui/dialog.tsx` | Modal dialog |
| Sheet | `components/ui/sheet.tsx` | Slide-out panel |
| Tabs | `components/ui/tabs.tsx` | Tab navigation |
| Tooltip | `components/ui/tooltip.tsx` | Hover tooltip |
| Badge | `components/ui/badge.tsx` | Status badge (6 variants) |
| Avatar | `components/ui/avatar.tsx` | User avatar with fallback initials |
| Alert | `components/ui/alert.tsx` | Alert message (5 variants) |
| Card | `components/ui/card.tsx` | Content card |
| Skeleton | `components/ui/skeleton.tsx` | Loading placeholder |
| Spinner | `components/ui/spinner.tsx` | Loading spinner (5 sizes) |
| Toaster | `components/ui/toaster.tsx` | Toast notifications |
| EmptyState | `components/ui/empty-state.tsx` | Empty state placeholder |
| ErrorState | `components/ui/error-state.tsx` | Error state with retry |
| Progress | `components/ui/progress.tsx` | Progress bar |
| Breadcrumb | `components/ui/breadcrumb.tsx` | Breadcrumb navigation |
| Pagination | `components/ui/pagination.tsx` | Pagination controls |
| Separator | `components/ui/separator.tsx` | Visual separator |
| DropdownMenu | `components/ui/dropdown-menu.tsx` | Dropdown menu |

## Component Principles

1. **Accessibility**: ARIA labels, keyboard navigation, focus management
2. **Dark mode**: All components support dark mode via CSS variables
3. **Variants**: Using `class-variance-authority` for type-safe variants
4. **Forward refs**: All components forward refs
5. **TypeScript**: Strict types, no `any`
6. **Composable**: Components can be composed (e.g., `asChild` pattern)

## Button Example

```tsx
import { Button } from '@/components/ui/button'

<Button variant="primary" size="lg" loading={isLoading} onClick={handleClick}>
  Click me
</Button>
```

## Form Components

Form components use React Hook Form + Zod:

```tsx
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from '@/components/forms/form'
import { Input } from '@/components/ui/input'

<Form {...form}>
  <FormField
    control={form.control}
    name="email"
    render={({ field }) => (
      <FormItem>
        <FormLabel>Email</FormLabel>
        <FormControl>
          <Input type="email" {...field} />
        </FormControl>
        <FormMessage />
      </FormItem>
    )}
  />
</Form>
```
