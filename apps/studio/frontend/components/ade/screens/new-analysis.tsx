'use client'

import { useState } from 'react'
import { Folder, Eye, Grid3x3, AudioWaveform, Lock, ChevronDown, FileText, type LucideIcon } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, SectionLabel, TechButton } from '@/components/ade/primitives'
import { projects, validationRows, type ScreenId } from '@/lib/ade-data'
import { cn } from '@/lib/utils'

type Workflow = 'visual' | 'tabular' | 'time-series'

const WORKFLOWS: { id: Workflow; label: string; icon: LucideIcon }[] = [
  { id: 'visual', label: 'Visual', icon: Eye },
  { id: 'tabular', label: 'Tabular', icon: Grid3x3 },
  { id: 'time-series', label: 'Series', icon: AudioWaveform },
]

const PRESETS = [
  'High-sensitivity candidate anomaly review with cluster grouping (Threshold: 0.82σ).',
  'Balanced discovery with candidate concept extraction (Threshold: 1.10σ).',
  'Conservative possible pattern scan, low false-positive (Threshold: 1.60σ).',
]

const ARTIFACTS = [
  { name: 'Candidate Anomalies', size: '12 KB · JSON/MD' },
  { name: 'Candidate Concepts', size: '48 KB · JSON/MD' },
  { name: 'Evidence Bundles', size: '2.4 MB · JSON/MD' },
  { name: 'Discovery Report', size: '312 KB · JSON/MD' },
]

export function NewAnalysisScreen({
  activeProject,
  onProjectChange,
  onNavigate,
}: {
  activeProject: string
  onProjectChange: (name: string) => void
  onNavigate: (id: ScreenId) => void
}) {
  const [workflow, setWorkflow] = useState<Workflow>('tabular')
  const [preset, setPreset] = useState(PRESETS[0])
  const [dataset, setDataset] = useState('/data/manufacturing/qc_sensor_2024.parquet')

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="New Analysis"
        title="Configure Local Analysis"
        description="Configure mock discovery parameters for local execution."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        {/* Config column */}
        <div className="flex flex-col gap-5">
          <div>
            <SectionLabel>Project</SectionLabel>
            <div className="relative mt-2">
              <select
                value={activeProject}
                onChange={(e) => onProjectChange(e.target.value)}
                aria-label="Project"
                className="h-11 w-full appearance-none rounded-md border border-border bg-card px-3 pr-9 font-mono text-sm text-foreground focus:border-primary/50 focus:outline-none"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            </div>
          </div>

          <div>
            <SectionLabel>Dataset source</SectionLabel>
            <div className="mt-2 flex items-center gap-3 rounded-md border border-border bg-card p-3">
              <Folder className="size-4 shrink-0 text-muted-foreground" />
              <input
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
                aria-label="Dataset path"
                className="min-w-0 flex-1 bg-transparent font-mono text-sm text-foreground focus:outline-none"
              />
              <button className="shrink-0 font-mono text-xs uppercase tracking-[0.1em] text-primary hover:underline">
                Browse
              </button>
            </div>
          </div>

          <div>
            <SectionLabel>Adapter workflow</SectionLabel>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {WORKFLOWS.map((w) => {
                const Icon = w.icon
                const active = workflow === w.id
                return (
                  <button
                    key={w.id}
                    type="button"
                    onClick={() => setWorkflow(w.id)}
                    aria-pressed={active}
                    className={cn(
                      'flex flex-col items-center gap-2 rounded-md border px-2 py-4 transition-colors',
                      active
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-card text-muted-foreground hover:text-foreground',
                    )}
                  >
                    <Icon className="size-5" />
                    <span className="font-mono text-[11px] uppercase tracking-[0.1em]">{w.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <SectionLabel>Review presets</SectionLabel>
            <div className="relative mt-2">
              <select
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                aria-label="Detection preset"
                className="h-auto w-full appearance-none rounded-md border border-border bg-card px-3 py-3 pr-9 text-sm leading-relaxed text-foreground focus:border-primary/50 focus:outline-none"
              >
                {PRESETS.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-4 size-4 text-muted-foreground" />
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-md border border-pattern/40 bg-pattern/10 p-3">
            <Lock className="mt-0.5 size-4 shrink-0 text-pattern" />
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.12em] text-pattern">Local-only execution</p>
              <p className="mt-1 text-xs leading-relaxed text-pattern/90">
                All processing is represented as a local workflow. No data leaves this workspace.
              </p>
            </div>
          </div>

          <TechButton variant="primary" className="h-11 w-full" onClick={() => onNavigate('runs')}>
            Run local analysis
          </TechButton>
        </div>

        {/* Preview column */}
        <div className="flex flex-col gap-6">
          <Panel>
            <PanelHeader title="Dataset validation preview" />
            <div className="p-4">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <PreviewStat label="Rows" value="847,293" />
                <PreviewStat label="Dimensions" value="42" />
                <PreviewStat label="Null rate" value="0.3%" />
                <PreviewStat label="Format" value="PARQUET" />
              </div>
              <div className="mt-4 flex flex-col divide-y divide-border">
                {validationRows.map((row) => (
                  <div key={row.name} className="grid grid-cols-[1fr_auto] items-center gap-4 py-3">
                    <div className="flex items-center gap-4">
                      <span className="font-mono text-sm text-foreground">{row.name}</span>
                      <span className="font-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
                        {row.type}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="hidden h-1 w-40 overflow-hidden rounded-full bg-muted sm:block">
                        <span className="block h-full rounded-full bg-primary/70" style={{ width: `${row.fill}%` }} />
                      </span>
                      <span className="font-mono text-xs text-operational">{row.valid}% Valid</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Expected output artifacts" />
            <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
              {ARTIFACTS.map((a) => (
                <div key={a.name} className="flex items-center gap-3 rounded-md border border-border bg-card p-4">
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{a.name}</p>
                    <p className="font-mono text-xs text-muted-foreground">{a.size}</p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

function PreviewStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-xl text-foreground">{value}</p>
    </div>
  )
}
