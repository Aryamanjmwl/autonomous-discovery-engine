'use client'

import {
  LayoutDashboard,
  FolderGit2,
  PlusSquare,
  Activity,
  Radar,
  FileText,
  Gauge,
  MessageSquareText,
  Settings,
  type LucideIcon,
} from 'lucide-react'
import type { ScreenId } from '@/lib/ade-data'
import { cn } from '@/lib/utils'

type NavItem = { id: ScreenId; label: string; icon: LucideIcon }

const NAV_GROUPS: { label: string; items: NavItem[] }[] = [
  {
    label: 'Discovery',
    items: [
      { id: 'overview', label: 'Overview', icon: LayoutDashboard },
      { id: 'projects', label: 'Projects', icon: FolderGit2 },
      { id: 'new-analysis', label: 'New Analysis', icon: PlusSquare },
      { id: 'runs', label: 'Runs', icon: Activity },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { id: 'findings', label: 'Findings', icon: Radar },
      { id: 'reports', label: 'Reports', icon: FileText },
      { id: 'benchmarks', label: 'Benchmarks', icon: Gauge },
      { id: 'feedback', label: 'Feedback', icon: MessageSquareText },
    ],
  },
  {
    label: 'System',
    items: [{ id: 'settings', label: 'Settings', icon: Settings }],
  },
]

export function Sidebar({
  active,
  onNavigate,
}: {
  active: ScreenId
  onNavigate: (id: ScreenId) => void
}) {
  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-panel">
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-4">
        <div className="flex size-7 items-center justify-center rounded-[4px] border border-border-strong bg-card">
          <span className="size-2 rounded-[1px] bg-primary shadow-[0_0_8px_0_var(--primary)]" />
        </div>
        <div className="leading-none">
          <span className="font-mono text-[13px] font-semibold tracking-[0.14em] text-foreground">
            ADE
          </span>
          <span className="ml-1 font-mono text-[13px] tracking-[0.14em] text-faint">STUDIO</span>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4" aria-label="Primary">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-5 last:mb-0">
            <p className="px-2 pb-2 font-mono text-[10px] uppercase tracking-[0.18em] text-faint">
              {group.label}
            </p>
            <ul className="flex flex-col gap-0.5">
              {group.items.map((item) => {
                const Icon = item.icon
                const isActive = active === item.id
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => onNavigate(item.id)}
                      aria-current={isActive ? 'page' : undefined}
                      className={cn(
                        'group relative flex w-full items-center gap-2.5 rounded-[4px] px-2.5 py-2 text-[13px] transition-colors',
                        isActive
                          ? 'bg-card text-foreground'
                          : 'text-muted-foreground hover:bg-card/60 hover:text-foreground',
                      )}
                    >
                      {isActive ? (
                        <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary" aria-hidden />
                      ) : null}
                      <Icon
                        className={cn(
                          'size-4 shrink-0',
                          isActive ? 'text-primary' : 'text-faint group-hover:text-foreground',
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-4 py-3.5">
        <div className="flex items-center justify-between">
          <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">Engine</p>
          <span className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full bg-operational shadow-[0_0_6px_0_var(--operational)]" />
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-operational">
              Ready
            </span>
          </span>
        </div>
        <p className="mt-2 font-mono text-[11px] text-muted-foreground">ade_engine_v0.1.0_L</p>
        <p className="font-mono text-[10px] text-faint">Local execution workspace</p>
      </div>
    </aside>
  )
}
