# Accessibility

> WCAG AA compliance, keyboard navigation, screen reader support.

## Principles

1. **Semantic HTML**: Use proper landmarks (`<nav>`, `<main>`, `<header>`, `<footer>`)
2. **ARIA labels**: All interactive elements have accessible names
3. **Keyboard navigation**: All functionality accessible via keyboard
4. **Focus management**: Visible focus indicators, focus trapping in modals
5. **Color contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
6. **Reduced motion**: Respect `prefers-reduced-motion`

## Implementation

### Focus Indicators

```css
*:focus-visible {
  outline: none;
  ring: 2px solid var(--ring);
  ring-offset: 2px;
}
```

### ARIA Labels

```tsx
<Button aria-label="Close menu">
  <XIcon aria-hidden="true" />
</Button>

<Button aria-label={`Notifications (${unreadCount} unread)`}>
  <Bell aria-hidden="true" />
  {unreadCount > 0 && <span aria-hidden="true">{unreadCount}</span>}
</Button>
```

### Keyboard Navigation

- All interactive elements are reachable via Tab
- Modals trap focus (Radix UI Dialog)
- Escape closes modals/dropdowns
- Enter/Space activates buttons

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

### Screen Reader

- Loading states use `role="status"` + `aria-live="polite"`
- Error states use `role="alert"`
- Form errors use `role="alert"` on error messages
- Decorative icons use `aria-hidden="true"`

### Color Contrast

- Use CSS variables for all colors (auto-adapts to dark mode)
- Minimum contrast: 4.5:1 (normal text), 3:1 (large text)
- Verified with WCAG AA standards

## Testing

Accessibility is tested via:
- Manual keyboard navigation testing
- Screen reader testing (NVDA, VoiceOver)
- Automated checks via Testing Library (ARIA roles, labels)
- E2E tests verify keyboard accessibility
