'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { CreditCard, Download } from 'lucide-react'

const INVOICES = [
  { id: 'INV-001', date: '2026-07-01', amount: '$19.00', status: 'paid' },
  { id: 'INV-002', date: '2026-06-01', amount: '$19.00', status: 'paid' },
  { id: 'INV-003', date: '2026-05-01', amount: '$19.00', status: 'paid' },
]

export default function BillingPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">Billing</h1>
      <Card>
        <CardHeader><CardTitle>Current Plan</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-2xl font-bold">Pro</p>
              <p className="text-sm text-muted-foreground">$19/month · Renews on 2026-08-01</p>
            </div>
            <Button variant="outline">Change Plan</Button>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><CreditCard className="h-5 w-5" /> Payment Method</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm">Visa ending in 4242</p>
          <p className="text-xs text-muted-foreground">Expires 12/2027</p>
          <Button variant="outline" className="mt-4">Update Card</Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Usage This Month</CardTitle></CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex justify-between text-sm"><span>Questions answered</span><span className="font-mono">247 / Unlimited</span></div>
            <div className="flex justify-between text-sm"><span>AI explanations</span><span className="font-mono">89 / 500</span></div>
            <div className="flex justify-between text-sm"><span>Study sessions</span><span className="font-mono">32</span></div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Invoices</CardTitle></CardHeader>
        <CardContent>
          <table className="w-full">
            <thead><tr className="border-b text-left text-sm text-muted-foreground">
              <th className="py-2">Invoice</th><th>Date</th><th>Amount</th><th>Status</th><th></th>
            </tr></thead>
            <tbody>
              {INVOICES.map((inv) => (
                <tr key={inv.id} className="border-b">
                  <td className="py-3 font-mono text-sm">{inv.id}</td>
                  <td className="text-sm">{inv.date}</td>
                  <td className="text-sm">{inv.amount}</td>
                  <td><Badge variant="secondary" className="bg-teal-600 text-white">{inv.status}</Badge></td>
                  <td><Button variant="ghost" size="icon"><Download className="h-4 w-4" /></Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
