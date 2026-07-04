'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Mail, MessageSquare, MapPin } from 'lucide-react'

export default function ContactPage() {
  return (
    <div className="container mx-auto px-4 py-20">
      <div className="mx-auto mb-16 max-w-2xl text-center">
        <h1 className="text-4xl font-extrabold tracking-tight">Contact Us</h1>
        <p className="mt-4 text-lg text-muted-foreground">We would love to hear from you.</p>
      </div>
      <div className="grid gap-8 md:grid-cols-2">
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><Mail className="h-5 w-5" /> Email</CardTitle></CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">General: hello@masteryos.com</p>
              <p className="text-sm text-muted-foreground">Support: support@masteryos.com</p>
              <p className="text-sm text-muted-foreground">Sales: sales@masteryos.com</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><MessageSquare className="h-5 w-5" /> Response Time</CardTitle></CardHeader>
            <CardContent><p className="text-sm text-muted-foreground">We respond to all inquiries within 24 hours during business days.</p></CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><MapPin className="h-5 w-5" /> Office</CardTitle></CardHeader>
            <CardContent><p className="text-sm text-muted-foreground">Remote-first · Global team</p></CardContent>
          </Card>
        </div>
        <Card>
          <CardHeader><CardTitle>Send us a message</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-4">
              <div><Label htmlFor="name">Name</Label><Input id="name" placeholder="Your name" /></div>
              <div><Label htmlFor="email">Email</Label><Input id="email" type="email" placeholder="you@example.com" /></div>
              <div><Label htmlFor="subject">Subject</Label><Input id="subject" placeholder="How can we help?" /></div>
              <div><Label htmlFor="message">Message</Label><Textarea id="message" rows={5} placeholder="Tell us more..." /></div>
              <Button className="w-full">Send Message</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
