'use client'

import { calculatePasswordStrength } from '@/lib/validations'
import { cn } from '@/lib/cn'

export function PasswordStrengthMeter({ password }: { password: string }) {
  const strength = calculatePasswordStrength(password)

  if (!password) return null

  return (
    <div className="space-y-1.5" aria-live="polite">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">Password strength</span>
        <span
          className={cn(
            'text-xs font-medium',
            strength.score <= 1 && 'text-destructive',
            strength.score === 2 && 'text-warning',
            strength.score === 3 && 'text-yellow-600',
            strength.score === 4 && 'text-success',
          )}
        >
          {strength.label}
        </span>
      </div>
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className={cn(
              'h-1.5 flex-1 rounded-full transition-colors',
              level <= strength.score ? strength.color : 'bg-muted',
            )}
          />
        ))}
      </div>
      <ul className="space-y-0.5 text-xs text-muted-foreground">
        <PasswordRule label="At least 12 characters" passed={password.length >= 12} />
        <PasswordRule
          label="Contains lowercase + uppercase"
          passed={/[a-z]/.test(password) && /[A-Z]/.test(password)}
        />
        <PasswordRule label="Contains a number" passed={/[0-9]/.test(password)} />
        <PasswordRule
          label="Contains a special character"
          passed={/[^a-zA-Z0-9]/.test(password)}
        />
      </ul>
    </div>
  )
}

function PasswordRule({ label, passed }: { label: string; passed: boolean }) {
  return (
    <li className={cn('flex items-center gap-1.5', passed && 'text-success')}>
      <span aria-hidden="true">{passed ? '✓' : '○'}</span>
      <span>{label}</span>
    </li>
  )
}
