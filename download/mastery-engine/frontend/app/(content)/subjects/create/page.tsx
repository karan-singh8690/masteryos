'use client'

import * as React from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { toast } from 'sonner'

import { useCreateSubject } from '@/hooks/use-content'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/forms/form'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

const createSubjectSchema = z.object({
  code: z.string().min(1, 'Code is required').max(50, 'Code is too long'),
  name: z.string().min(1, 'Name is required').max(200, 'Name is too long'),
  slug: z
    .string()
    .min(1, 'Slug is required')
    .max(100, 'Slug is too long')
    .regex(/^[a-z0-9-]+$/, 'Slug must be lowercase letters, numbers, and hyphens'),
  description: z.string().optional(),
})

type CreateSubjectFormData = z.infer<typeof createSubjectSchema>

export default function CreateSubjectPage() {
  const router = useRouter()
  const createMutation = useCreateSubject()

  const form = useForm<CreateSubjectFormData>({
    resolver: zodResolver(createSubjectSchema),
    defaultValues: {
      code: '',
      name: '',
      slug: '',
      description: '',
    },
  })

  const onSubmit = async (data: CreateSubjectFormData) => {
    try {
      await createMutation.mutateAsync({
        code: data.code,
        name: data.name,
        slug: data.slug,
        description: data.description || undefined,
      })
      toast.success('Subject created successfully!')
      router.push('/content/subjects')
    } catch {
      toast.error('Failed to create subject. Please try again.')
    }
  }

  // Auto-generate slug from name
  React.useEffect(() => {
    const subscription = form.watch((value, { name }) => {
      if (name === 'name' && value.name) {
        const slug = value.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
        form.setValue('slug', slug)
      }
    })
    return () => subscription.unsubscribe()
  }, [form])

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <Link href="/content/subjects" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Back to subjects
        </Link>
        <h1 className="mt-2 text-2xl font-bold tracking-tight">Create subject</h1>
        <p className="text-sm text-muted-foreground">Create a new curriculum subject</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Subject details</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4" noValidate>
              <FormField
                control={form.control}
                name="code"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Code</FormLabel>
                    <FormControl>
                      <Input placeholder="PY-INT" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Python Interview Prep" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="slug"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Slug</FormLabel>
                    <FormControl>
                      <Input placeholder="python-interview-prep" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description (optional)</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="A comprehensive Python interview preparation course..."
                        rows={4}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" asChild>
                  <Link href="/content/subjects">Cancel</Link>
                </Button>
                <Button
                  type="submit"
                  loading={createMutation.isPending}
                  disabled={createMutation.isPending}
                >
                  Create subject
                </Button>
              </div>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}
