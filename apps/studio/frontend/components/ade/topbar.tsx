'use client'

import { ChevronsRight, ChevronDown } from 'lucide-react'
import { projects } from '@/lib/ade-data'

export function Topbar({
  project,
  onProjectChange,
}: {
  project: string
  onProjectChange: (name: string) => void
}) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border bg-panel/80 px-4 backdrop-blur">
      {/* Command / search bar */}
      <div className="relative flex max-w-lg flex-1 items-center">
        <ChevronsRight className="pointer-events-none absolute left-3 size-3.5 text-primary" />
        <input
          type="text"
          placeholder="Search runs, reports, or evidence..."
          className="h-9 w-full rounded-[4px] border border-border bg-card/60 pl-9 pr-14 font-mono text-[13px] text-foreground placeholder:text-faint focus:border-primary/50 focus:bg-card focus:outline-none focus:ring-1 focus:ring-primary/30"
          aria-label="Command or search"
        />
        <kbd className="absolute right-3 rounded-[3px] border border-border bg-raised px-1.5 py-0.5 font-mono text-[10px] text-faint">
          ⌘K
        </kbd>
      </div>

      <div className="ml-auto flex items-center gap-3">
        {/* Project selector */}
        <div className="flex items-center gap-2.5 border-l border-border pl-3">
          <span className="hidden font-mono text-[10px] uppercase tracking-[0.16em] text-faint sm:inline">
            Project
          </span>
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
        </div>

        {/* Local engine status */}
        <div className="hidden items-center gap-2 border-l border-border pl-3 md:flex">
          <span className="relative flex size-1.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-operational opacity-60" />
            <span className="relative inline-flex size-1.5 rounded-full bg-operational" />
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.13em] text-operational">
            Local engine ready
          </span>
        </div>

        <span className="hidden border-l border-border pl-3 font-mono text-[10px] uppercase tracking-[0.13em] text-faint lg:inline">
          v0.1.0 · technical preview
        </span>
      </div>
    </header>
  )
}
