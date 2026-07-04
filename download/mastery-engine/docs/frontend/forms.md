# Forms

> React Hook Form + Zod + server error mapping.

## Architecture

```
Zod schema → React Hook Form resolver → Form components → Server validation
```

1. Define Zod schema (client-side validation)
2. Use `zodResolver` with React Hook Form
3. Render with `Form` components
4. On submit, API call to backend
5. On error, map server errors back to form fields

## Form Components

```tsx
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage, FormDescription } from '@/components/forms/form'

<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl>
            <Input type="email" {...field} />
          </FormControl>
          <FormDescription>We'll never share your email.</FormDescription>
          <FormMessage />
        </FormItem>
      )}
    />
  </form>
</Form>
```

## Zod Schemas

All schemas defined in `lib/validations.ts`:

- `loginSchema`
- `registerSchema` (with password strength)
- `forgotPasswordSchema`
- `resetPasswordSchema`
- `changePasswordSchema`
- `verifyEmailSchema`
- `mfaVerifySchema`
- `mfaEnableSchema`
- `mfaDisableSchema`
- `mfaRecoverySchema`
- `updateProfileSchema`

## Password Strength

```tsx
import { PasswordStrengthMeter } from '@/components/forms/password-strength-meter'

<PasswordInput {...field} />
<PasswordStrengthMeter password={password} />
```

Shows:
- Strength meter (4 bars: weak → strong)
- Rule checklist (lowercase, uppercase, number, special, length)

## Server Error Mapping

When the backend returns field errors:

```typescript
try {
  await onSubmit(data)
} catch (error) {
  if (error instanceof ApiError && error.fieldErrors) {
    mapServerErrorsToForm(error.fieldErrors, form.setError)
  }
}
```

## Loading States

```tsx
<Button type="submit" loading={form.formState.isSubmitting}>
  Submit
</Button>
```

The `loading` prop shows a spinner + disables the button.
