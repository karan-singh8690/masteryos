'use client'

import * as React from 'react'

import { Header } from '@/components/layout/header'
import { Sidebar } from '@/components/layout/sidebar'

interface AppLayoutProps {
  children: React.ReactNode
}

/**
 * Authenticated app layout with sidebar + header.
 *
 * Used for all authenticated pages (dashboard, profile, security, etc.).
 */
export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">
        <Sidebar />
      </div>

      {/* Main content area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main
          className="flex-1 overflow-y-auto bg-muted/30 p-4 md:p-6"
          id="main-content"
          tabIndex={-1}
        >
          {children}
        </main>
      </div>
    </div>
  )
}
