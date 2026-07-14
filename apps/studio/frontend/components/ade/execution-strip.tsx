'use client'

import { Cpu, Lock } from 'lucide-react'
import type { StudioData } from '@/lib/ade-api'

function TelemetryItem({
  label,
  children,
  className,
}: {
  label: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={className}>
      <span className="mr-2 font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
        {label}
      </span>
      <span className="font-mono text-[11px] tabular-nums text-foreground">{children}</span>
    </div>
  )
}

export function ExecutionStrip({ studioData }: { studioData: StudioData }) {
  const connected = studioData.mode === 'connected'
  const latestRun = studioData.summary?.latest_run_id || studioData.summary?.latest_run?.run_id
  const latestReport = studioData.summary?.latest_report_name || studioData.summary?.latest_report?.name

  return (
    <footer className="flex h-10 shrink-0 items-center gap-5 border-t border-border bg-panel px-4">
      <div className="flex items-center gap-2">
        <Cpu className="size-3.5 text-primary" />
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
          Local run telemetry
        </span>
      </div>

      <TelemetryItem label="Mode" className="hidden md:block">
        {connected ? 'Engine Connected' : 'Mock Preview'}
      </TelemetryItem>

      <TelemetryItem label="Latest run" className="hidden lg:block">
        {connected ? latestRun || 'Not available from current report' : 'mock fallback'}
      </TelemetryItem>

      <TelemetryItem label="Latest report" className="hidden xl:block">
        {connected ? latestReport || 'Not available from current report' : 'mock fallback'}
      </TelemetryItem>

      <div className="ml-auto flex items-center gap-3">
        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.13em] text-pattern">
          <Lock className="size-3" />
          Local-only
        </span>
        <span className="font-mono text-[10px] uppercase tracking-[0.13em] text-operational">
          {connected ? 'Engine Connected' : 'Mock Preview'}
        </span>
      </div>
    </footer>
  )
}
