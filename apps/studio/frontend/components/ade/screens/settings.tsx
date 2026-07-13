'use client'

import { Cpu, HardDrive, ShieldCheck, TriangleAlert, CloudOff } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, SectionLabel, StatusBadge } from '@/components/ade/primitives'

const STORAGE_PATHS = [
  { label: 'Datasets', path: '/var/ade/datasets/' },
  { label: 'Run artifacts', path: '/var/ade/runs/' },
  { label: 'Reports', path: '/var/ade/reports/' },
  { label: 'Feedback store', path: '/var/ade/feedback.jsonl' },
]

const LIMITATIONS = [
  'Candidate findings are unverified and require human review before any local use.',
  'This Studio foundation uses mock data and does not run analysis by itself.',
  'ADE v0.1.0 Technical Preview interfaces and output schemas may change.',
  'No cloud sync, telemetry, or remote model inference is performed.',
]

export function SettingsScreen() {
  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="System"
        title="Settings & About"
        description="Local configuration and engine status for the ADE Studio UI foundation."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel className="p-5">
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-md border border-primary/50 bg-primary/10">
              <span className="size-3 rounded-full bg-primary" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">ADE Studio</h2>
              <p className="font-mono text-xs text-muted-foreground">Autonomous Discovery Engine</p>
            </div>
          </div>
          <div className="mt-5 flex flex-col gap-3">
            <Row label="Version" value="v0.1.0" />
            <Row label="Build" value="ade_engine_v0.1.0_L" />
            <Row
              label="Stage"
              value={<StatusBadge tone="pattern">ADE v0.1.0 Technical Preview</StatusBadge>}
            />
          </div>
        </Panel>

        <Panel className="p-5">
          <SectionLabel>Engine status</SectionLabel>
          <div className="mt-4 flex flex-col gap-4">
            <StatusLine icon={Cpu} label="Local execution" value="Active · Idle" tone="operational" />
            <StatusLine icon={HardDrive} label="Local storage" value="8.4 GB / 64 GB" tone="anomaly" />
            <StatusLine icon={ShieldCheck} label="Workspace integrity" value="Local" tone="operational" />
            <StatusLine icon={CloudOff} label="Network" value="Offline · Local-only" tone="pattern" />
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelHeader title="Local storage paths" />
        <ul className="p-4">
          {STORAGE_PATHS.map((s) => (
            <li key={s.path} className="flex items-center justify-between border-b border-border py-2.5 last:border-b-0">
              <span className="text-sm text-muted-foreground">{s.label}</span>
              <span className="font-mono text-xs text-foreground">{s.path}</span>
            </li>
          ))}
        </ul>
      </Panel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Panel className="p-5">
          <div className="flex items-center gap-2">
            <TriangleAlert className="size-4 text-pattern" />
            <SectionLabel>Limitations</SectionLabel>
          </div>
          <ul className="mt-3 flex flex-col gap-2.5">
            {LIMITATIONS.map((l, i) => (
              <li key={i} className="flex items-start gap-2 text-sm leading-relaxed text-muted-foreground">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-muted-foreground" aria-hidden />
                {l}
              </li>
            ))}
          </ul>
        </Panel>

        <Panel className="p-5">
          <div className="flex items-center gap-2">
            <CloudOff className="size-4 text-primary" />
            <SectionLabel>No cloud · local-only</SectionLabel>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            ADE Studio runs entirely in the local execution workspace. Datasets, runs, candidate
            findings, reports, and feedback never leave this machine. There is no authentication,
            no remote database, and no external API — the engine performs discovery on-device and
            writes all artifacts to local storage.
          </p>
          <div className="mt-4 flex items-center gap-2 rounded-md border border-operational/40 bg-operational/10 px-3 py-2">
            <ShieldCheck className="size-4 text-operational" />
            <span className="text-xs text-operational">No data leaves this local workspace.</span>
          </div>
        </Panel>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2.5 text-sm last:border-b-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono text-foreground">{value}</span>
    </div>
  )
}

function StatusLine({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string
  tone: 'operational' | 'anomaly' | 'pattern'
}) {
  const toneClass = { operational: 'text-operational', anomaly: 'text-anomaly', pattern: 'text-pattern' }[tone]
  return (
    <div className="flex items-center gap-3">
      <Icon className="size-4 text-muted-foreground" />
      <span className="flex-1 text-sm text-muted-foreground">{label}</span>
      <span className={`font-mono text-xs ${toneClass}`}>{value}</span>
    </div>
  )
}
