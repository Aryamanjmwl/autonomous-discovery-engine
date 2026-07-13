'use client'

import { Cpu, Lock, Play, Square } from 'lucide-react'

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

export function ExecutionStrip() {
  return (
    <footer className="flex h-10 shrink-0 items-center gap-5 border-t border-border bg-panel px-4">
      <div className="flex items-center gap-2">
        <Cpu className="size-3.5 text-primary" />
        <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
          Local run telemetry
        </span>
      </div>

      {/* live signal bars */}
      <div className="hidden items-end gap-0.5 sm:flex" aria-hidden>
        {[3, 6, 4, 8, 5, 7, 4].map((h, i) => (
          <span
            key={i}
            className="w-0.5 rounded-full bg-primary/60"
            style={{
              height: `${h + 2}px`,
              animation: `ade-pulse 1.2s ${i * 0.12}s ease-in-out infinite alternate`,
            }}
          />
        ))}
      </div>

      <TelemetryItem label="Uptime" className="hidden md:block">
        47h 12m
      </TelemetryItem>

      <div className="hidden items-center lg:flex">
        <TelemetryItem label="Run">run_847_q4</TelemetryItem>
        <span className="ml-3 h-1 w-24 overflow-hidden rounded-full bg-raised">
          <span className="block h-full w-[64%] rounded-full bg-primary" />
        </span>
        <span className="ml-2 font-mono text-[11px] tabular-nums text-primary">64%</span>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.13em] text-pattern">
          <Lock className="size-3" />
          Local-only
        </span>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-[4px] border border-border bg-card/60 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
        >
          <Square className="size-3" />
          Halt
        </button>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 rounded-[4px] border border-primary/55 bg-primary/10 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-primary transition-colors hover:bg-primary/[0.18]"
        >
          <Play className="size-3" />
          Resume
        </button>
      </div>

      <style jsx>{`
        @keyframes ade-pulse {
          from {
            opacity: 0.35;
            transform: scaleY(0.6);
          }
          to {
            opacity: 1;
            transform: scaleY(1.15);
          }
        }
      `}</style>
    </footer>
  )
}
