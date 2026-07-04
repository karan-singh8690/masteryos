# Theme System

> Light / Dark / System theme with `next-themes`.

## Implementation

### Provider

```tsx
// providers/index.tsx
import { ThemeProvider } from '@/providers/theme-provider'

<ThemeProvider
  attribute="class"
  defaultTheme="system"
  enableSystem
  disableTransitionOnChange
>
  {children}
</ThemeProvider>
```

### Toggle

```tsx
// components/layout/theme-toggle.tsx
import { useTheme } from 'next-themes'

const { theme, setTheme } = useTheme()
// theme: 'light' | 'dark' | 'system'
// setTheme('dark')
```

### CSS Variables

Theme colors are defined as CSS variables in `styles/globals.css`:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 222 47% 11%;
  --primary: 221 83% 53%;
  /* ... */
}

.dark {
  --background: 222 47% 11%;
  --foreground: 210 40% 98%;
  --primary: 217 91% 60%;
  /* ... */
}
```

Tailwind reads these via the config:

```js
colors: {
  background: 'hsl(var(--background))',
  foreground: 'hsl(var(--foreground))',
  primary: { DEFAULT: 'hsl(var(--primary))' },
  // ...
}
```

## Persistence

Theme is persisted by `next-themes` in `localStorage` under the key `theme`.

## System Preference

When `theme === 'system'`, `next-themes` uses `prefers-color-scheme` media query.

## Dark Mode Support

All components support dark mode automatically via CSS variables. No manual dark mode classes needed.

## Hydration

`next-themes` handles SSR hydration with `suppressHydrationWarning` on `<html>`:

```tsx
<html lang="en" suppressHydrationWarning>
```

## Theme Toggle Component

The theme toggle is a dropdown with three options:

- Light ☀️
- Dark 🌙
- System 🖥️

Available in the header (authenticated) and auth layout.
