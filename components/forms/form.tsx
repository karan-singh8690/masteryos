'use client'

import * as React from 'react'
import {
  Controller,
  type ControllerProps,
  type FieldPath,
  type FieldValues,
  FormProvider,
  useFormContext,
  useFormState,
} from 'react-hook-form'

import { cn } from '@/lib/cn'
import { Label } from '@/components/ui/label'

// Re-export FormProvider
const Form = FormProvider

// ============================================================
// FormField (Controller wrapper)
// ============================================================

interface FormFieldContextValue {
  name: string
}

const FormFieldContext = React.createContext<FormFieldContextValue>(
  {} as FormFieldContextValue,
)

const FormField = <
  TFieldValues extends FieldValues,
  TName extends FieldPath<TFieldValues>,
>({
  ...props
}: ControllerProps<TFieldValues, TName>) => {
  return (
    <FormFieldContext.Provider value={{ name: props.name }}>
      <Controller {...props} />
    </FormFieldContext.Provider>
  )
}

// ============================================================
// FormItem (context for label + error)
// ============================================================

const useFormField = () => {
  const fieldContext = React.useContext(FormFieldContext)
  const { getFieldState } = useFormContext()
  const formState = useFormState({ name: fieldContext.name })
  const fieldState = getFieldState(fieldContext.name, formState)

  if (!fieldContext) {
    throw new Error('useFormField should be used within <FormField>')
  }

  const { id } = fieldState

  return {
    id,
    name: fieldContext.name,
    formItemId: `${id}-form-item`,
    formDescriptionId: `${id}-form-item-description`,
    formMessageId: `${id}-form-item-message`,
    ...fieldState,
  }
}

const FormItemContext = React.createContext<ReturnType<typeof useFormField>>(
  {} as ReturnType<typeof useFormField>,
)

const FormItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    return (
      <div ref={ref} className={cn('space-y-2', className)} {...props} />
    )
  },
)
FormItem.displayName = 'FormItem'

// ============================================================
// FormLabel
// ============================================================

const FormLabel = React.forwardRef<
  React.ElementRef<typeof Label>,
  React.ComponentPropsWithoutRef<typeof Label>
>(({ className, ...props }, ref) => {
  const { error, formItemId } = useFormField()

  return (
    <Label
      ref={ref}
      className={cn(error && 'text-destructive', className)}
      htmlFor={formItemId}
      {...props}
    />
  )
})
FormLabel.displayName = 'FormLabel'

// ============================================================
// FormControl
// ============================================================

const FormControl = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ ...props }, ref) => {
  const { error, formItemId, formDescriptionId, formMessageId } = useFormField()

  return (
    <div
      ref={ref}
      id={formItemId}
      aria-describedby={
        !error
          ? `${formDescriptionId}`
          : `${formDescriptionId} ${formMessageId}`
      }
      aria-invalid={!!error}
      {...props}
    />
  )
})
FormControl.displayName = 'FormControl'

// ============================================================
// FormDescription
// ============================================================

const FormDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => {
  const { formDescriptionId } = useFormField()

  return (
    <p
      ref={ref}
      id={formDescriptionId}
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
    />
  )
})
FormDescription.displayName = 'FormDescription'

// ============================================================
// FormMessage (displays field error)
// ============================================================

const FormMessage = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, children, ...props }, ref) => {
  const { error, formMessageId } = useFormField()
  const body = error ? String(error?.message) : children

  if (!body) {
    return null
  }

  return (
    <p
      ref={ref}
      id={formMessageId}
      role="alert"
      className={cn('text-sm font-medium text-destructive', className)}
      {...props}
    >
      {body}
    </p>
  )
})
FormMessage.displayName = 'FormMessage'

// ============================================================
// Field error mapping (server → client)
// ============================================================

/**
 * Maps server-side validation errors to React Hook Form field errors.
 *
 * Usage:
 *   try {
 *     await onSubmit(data)
 *   } catch (error) {
 *     if (error instanceof ApiError && error.fieldErrors) {
 *       mapServerErrorsToForm(error.fieldErrors, setError)
 *     }
 *   }
 */
export function mapServerErrorsToForm<T extends FieldValues>(
  fieldErrors: Record<string, string[]>,
  setError: (
    name: FieldPath<T>,
    error: { type: string; message: string },
  ) => void,
) {
  for (const [field, messages] of Object.entries(fieldErrors)) {
    if (messages.length > 0) {
      setError(field as FieldPath<T>, {
        type: 'server',
        message: messages[0]!,
      })
    }
  }
}

export {
  Form,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
  FormField,
  useFormField,
}
