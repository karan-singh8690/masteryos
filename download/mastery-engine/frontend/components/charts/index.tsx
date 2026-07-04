'use client'

import * as React from 'react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from 'recharts'

import { cn } from '@/lib/cn'

// ============================================================
// Trend Chart (mastery/memory over time)
// ============================================================

export interface TrendChartProps {
  data: { date: string; value: number; label?: string }[]
  title: string
  color?: string
  height?: number
  valueFormat?: (value: number) => string
}

export function TrendChart({
  data,
  title,
  color = '#3b82f6',
  height = 200,
  valueFormat = (v) => `${Math.round(v)}%`,
}: TrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data available
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">{title}</h4>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} aria-label={title}>
          <defs>
            <linearGradient id={`gradient-${title}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => valueFormat(v)}
            domain={[0, 100]}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--popover))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '0.5rem',
              fontSize: '12px',
            }}
            formatter={(value: number) => [valueFormat(value), title]}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke={color}
            fill={`url(#gradient-${title})`}
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============================================================
// Bar Chart (weekly activity)
// ============================================================

export interface BarChartProps {
  data: { label: string; value: number }[]
  title: string
  color?: string
  height?: number
}

export function ActivityBarChart({
  data,
  title,
  color = '#3b82f6',
  height = 200,
}: BarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-sm text-muted-foreground" style={{ height }}>
        No data available
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium">{title}</h4>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} aria-label={title}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--popover))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '0.5rem',
              fontSize: '12px',
            }}
          />
          <Bar dataKey="value" fill={color} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ============================================================
// Mastery Donut (overall mastery percentage)
// ============================================================

export interface MasteryDonutProps {
  value: number // 0-100
  label?: string
  size?: number
}

export function MasteryDonut({ value, label = 'Mastery', size = 160 }: MasteryDonutProps) {
  const data = [
    { name: 'Mastered', value: value, color: '#22c55e' },
    { name: 'Remaining', value: 100 - value, color: 'hsl(var(--muted))' },
  ]

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={size * 0.35}
            outerRadius={size * 0.45}
            startAngle={90}
            endAngle={-270}
            dataKey="value"
            stroke="none"
          >
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.color} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute flex flex-col items-center">
        <span className="text-2xl font-bold">{Math.round(value)}%</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    </div>
  )
}

// ============================================================
// Mini Sparkline
// ============================================================

export interface SparklineProps {
  data: number[]
  color?: string
  height?: number
  className?: string
}

export function Sparkline({ data, color = '#3b82f6', height = 40, className }: SparklineProps) {
  const chartData = data.map((value, index) => ({ index, value }))

  if (!data || data.length === 0) return null

  return (
    <ResponsiveContainer width="100%" height={height} className={className}>
      <LineChart data={chartData}>
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
