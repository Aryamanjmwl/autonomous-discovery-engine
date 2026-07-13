'use client'

import { Database, ArrowRight } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, StatusBadge, TechButton } from '@/components/ade/primitives'
import { projects, type ScreenId } from '@/lib/ade-data'

export function ProjectsScreen({
  activeProject,
  onSelectProject,
  onNavigate,
}: {
  activeProject: string
  onSelectProject: (name: string) => void
  onNavigate: (id: ScreenId) => void
}) {
  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Workspace"
        title="Projects"
        description="Local discovery projects. Each project scopes datasets, runs, and candidate findings within the local workspace."
        actions={<TechButton variant="primary" onClick={() => onNavigate('new-analysis')}>New analysis</TechButton>}
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {projects.map((p) => {
          const isActive = p.name === activeProject
          return (
            <Panel key={p.id} className="p-5">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex size-9 items-center justify-center rounded-md border border-border bg-card">
                    <Database className="size-4 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-sm font-medium text-foreground">{p.name}</h3>
                    <p className="font-mono text-xs text-muted-foreground">{p.dataset}</p>
                  </div>
                </div>
                <StatusBadge tone={p.status === 'active' ? 'operational' : 'muted'} dot>
                  {p.status}
                </StatusBadge>
              </div>

              <div className="mt-5 grid grid-cols-3 gap-3">
                <Stat label="Runs" value={String(p.runs)} />
                <Stat label="Findings" value={String(p.findings)} />
                <Stat label="Last run" value={p.lastRun} mono />
              </div>

              <div className="mt-5 flex items-center gap-2">
                <TechButton
                  variant="secondary"
                  active={isActive}
                  onClick={() => onSelectProject(p.name)}
                >
                  {isActive ? 'Selected' : 'Select'}
                </TechButton>
                <TechButton variant="ghost" onClick={() => onNavigate('runs')}>
                  View runs <ArrowRight className="size-3.5" />
                </TechButton>
              </div>
            </Panel>
          )
        })}
      </div>
    </div>
  )
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className={mono ? 'mt-1 font-mono text-xs text-foreground' : 'mt-1 font-mono text-lg text-foreground'}>
        {value}
      </p>
    </div>
  )
}
