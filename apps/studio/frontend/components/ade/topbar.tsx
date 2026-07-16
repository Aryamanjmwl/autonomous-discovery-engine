'use client'

import { ChevronDown, RefreshCw } from 'lucide-react'
import { projects } from '@/lib/ade-data'
import type { EngineMode, StudioHealth, StudioSummary } from '@/lib/ade-api'

export function Topbar({
  project,
  onProjectChange,
  engineMode,
  health,
  summary,
  isRefreshing,
  onRefresh,
}: {
  project: string
  onProjectChange: (name: string) => void
  engineMode: EngineMode
  health: StudioHealth | null
  summary: StudioSummary | null
  isRefreshing: boolean
  onRefresh: () => void
}) {
  const connected = engineMode === 'connected'
  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border bg-panel/80 px-4 backdrop-blur">
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
            {connected ? 'Local workspace' : 'Mock preview'}
          </p>
          <p className="truncate font-mono text-[13px] text-foreground">
            {connected
              ? summary?.latest_report_name || 'No local run yet'
              : 'Backend unavailable · demo data shown'}
          </p>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="flex items-center gap-2.5 border-l border-border pl-3">
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.16em] text-faint sm:inline">
            {connected ? 'Workspace' : 'Project'}
          </span>
          {connected ? (
            <span className="rounded-[4px] border border-border bg-card/60 px-3 py-1.5 font-mono text-[12px] text-foreground">
              ADE Local Engine
            </span>
          ) : (
            <div className="relative">
              <select
                value={project}
                onChange={(e) => onProjectChange(e.target.value)}
                aria-label="Select project"
                className="h-8 appearance-none rounded-[4px] border border-border bg-card/60 pl-3 pr-8 font-mono text-[12px] text-foreground hover:border-border-strong focus:border-primary/50 focus:outline-none"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2 top-1/2 size-3.5 -translate-y-1/2 text-faint" />
            </div>
          )}
        </div>

        {/* Local engine status */}
        <div className="hidden items-center gap-2 border-l border-border pl-3 md:flex">
          <span className="relative flex size-1.5">
            {connected ? (
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-operational opacity-60" />
            ) : null}
            <span
              className={
                connected
                  ? 'relative inline-flex size-1.5 rounded-full bg-operational'
                  : 'relative inline-flex size-1.5 rounded-full bg-pattern'
              }
            />
          </span>
          <span
            className={
              connected
                ? 'font-mono text-[10px] uppercase tracking-[0.13em] text-operational'
                : 'font-mono text-[10px] uppercase tracking-[0.13em] text-pattern'
            }
          >
            {connected ? 'Engine Connected' : 'Mock Preview'}
          </span>
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={isRefreshing}
          aria-label={isRefreshing ? 'Refreshing local ADE data' : 'Refresh local ADE data'}
          className="inline-flex h-8 items-center gap-2 rounded-[4px] border border-border bg-card/60 px-3 font-mono text-[10px] uppercase tracking-[0.13em] text-muted-foreground hover:border-border-strong hover:text-foreground"
        >
          <RefreshCw className={`size-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Refreshing' : 'Refresh'}
        </button>

        <span className="hidden border-l border-border pl-3 font-mono text-[10px] uppercase tracking-[0.13em] text-faint lg:inline">
          {health?.version ? `v${health.version}` : 'v0.1.0'} · {summary?.label?.toLowerCase() || 'technical preview'}
        </span>
      </div>
    </header>
  )
}
