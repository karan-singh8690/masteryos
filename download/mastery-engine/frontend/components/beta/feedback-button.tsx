'use client'

import * as React from 'react'
import { MessageSquare, X, Star, Upload, Send } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/cn'

const FEEDBACK_CATEGORIES = [
  { value: 'bug', label: '🐛 Bug Report' },
  { value: 'feature_request', label: '💡 Feature Request' },
  { value: 'ui_ux', label: '🎨 UI/UX Feedback' },
  { value: 'content', label: '📚 Content Feedback' },
  { value: 'performance', label: '⚡ Performance Issue' },
  { value: 'other', label: '💬 Other' },
]

export function BetaFeedbackButton() {
  const [open, setOpen] = React.useState(false)
  const [rating, setRating] = React.useState(0)
  const [hoverRating, setHoverRating] = React.useState(0)
  const [category, setCategory] = React.useState('')
  const [comment, setComment] = React.useState('')
  const [submitting, setSubmitting] = React.useState(false)

  const handleSubmit = async () => {
    if (rating === 0) { toast.error('Please select a rating'); return }
    if (!category) { toast.error('Please select a category'); return }
    if (!comment.trim()) { toast.error('Please enter a comment'); return }

    setSubmitting(true)
    try {
      // Auto-capture context
      const userAgent = navigator.userAgent
      const browser = getBrowserName(userAgent)
      const platform = navigator.platform || 'unknown'
      const route = window.location.pathname
      const correlationId = document.querySelector('meta[name="correlation-id"]')?.getAttribute('content') || null

      await apiClient.post('/beta/feedback', {
        rating,
        category,
        comment,
        browser,
        platform,
        route,
        correlation_id: correlationId,
      })
      toast.success('Feedback submitted — thank you!')
      setOpen(false)
      setRating(0)
      setCategory('')
      setComment('')
    } catch {
      toast.error('Failed to submit feedback')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      {/* Floating feedback button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full bg-primary px-4 py-3 text-sm font-medium text-primary-foreground shadow-lg transition-transform hover:scale-105 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        aria-label="Submit feedback"
      >
        <MessageSquare className="h-4 w-4" aria-hidden="true" />
        <span className="hidden sm:inline">Feedback</span>
      </button>

      {/* Feedback dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Beta Feedback</DialogTitle>
            <DialogDescription>Help us improve the platform. Your feedback shapes the beta.</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Rating */}
            <div className="space-y-2">
              <Label>How would you rate your experience?</Label>
              <div className="flex gap-1" role="radiogroup" aria-label="Rating">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(0)}
                    className="focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
                    aria-label={`${star} star${star > 1 ? 's' : ''}`}
                    role="radio"
                    aria-checked={rating === star}
                  >
                    <Star
                      className={cn(
                        'h-7 w-7 transition-colors',
                        (hoverRating || rating) >= star
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-muted-foreground',
                      )}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Category */}
            <div className="space-y-2">
              <Label>Category</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger><SelectValue placeholder="Select category" /></SelectTrigger>
                <SelectContent>
                  {FEEDBACK_CATEGORIES.map((cat) => (
                    <SelectItem key={cat.value} value={cat.value}>{cat.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Comment */}
            <div className="space-y-2">
              <Label htmlFor="comment">Tell us more</Label>
              <Textarea
                id="comment"
                placeholder="What happened? What were you trying to do? What can we improve?"
                rows={4}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                maxLength={5000}
              />
              <p className="text-xs text-muted-foreground">{comment.length}/5000 characters</p>
            </div>

            {/* Auto-captured info notice */}
            <p className="text-xs text-muted-foreground">
              We automatically capture: browser, platform, current route, and correlation ID for troubleshooting.
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={handleSubmit} loading={submitting} disabled={submitting}>
              <Send className="mr-2 h-4 w-4" />
              Submit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

function getBrowserName(ua: string): string {
  if (ua.includes('Firefox/')) return 'Firefox'
  if (ua.includes('Chrome/')) return 'Chrome'
  if (ua.includes('Safari/')) return 'Safari'
  if (ua.includes('Edge/')) return 'Edge'
  return 'Unknown'
}
