'use client'

import { useState } from 'react'
import { CheckCircle2, Loader2, Clock, AlertTriangle, FileText } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, SectionLabel, StatusBadge } from '@/components/ade/primitives'
import { runs, runLogLines } from '@/lib/ade-data'
import { cn } from '@/lib/utils'

const STAGES = [
  'Load & validate',
  'Feature extraction',
  'Novelty detection',
  'Candidate clustering',
  'Evidence extraction',
  'Report generation',
]

export function RunsScreen() {
  const [selectedId, setSelectedId] = useState(runs[0].id)
  const selected = runs.find((r) => r.id === selectedId) ?? runs[0]
  const currentStageIndex = Math.min(
    Math.floor((selected.progress / 100) * STAGES.length),
    STAGES.length - 1,
  )

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Execution"
        title="Run Status"
        description="Review local discovery runs, current stage, local run telemetry, and generated artifacts."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,300px)_1fr]">
        {/* Run list */}
        <Panel>
          <PanelHeader title={`Runs (${runs.length})`} />
          <ul>
            {runs.map((r) => (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(r.id)}
                  className={cn(
                    'flex w-full flex-col gap-2 border-b border-border px-4 py-3 text-left transition-colors last:border-b-0',
                    r.id === selectedId ? 'bg-primary/10' : 'hover:bg-card',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-foreground">{r.id}</span>
                    <RunStatusBadge status={r.status} />
                  </div>
                  <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                    <span className="uppercase tracking-[0.1em]">{r.workflow}</span>
                    <span>{r.startedAt}</span>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </Panel>

        {/* Run detail */}
        <div className="flex flex-col gap-6">
          <Panel className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-mono text-sm text-foreground">{selected.id}</p>
                <p className="text-sm text-muted-foreground">{selected.project}</p>
              </div>
              <RunStatusBadge status={selected.status} />
            </div>

            <div className="mt-5">
              <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                <span>Stage: {selected.stage}</span>
                <span>{selected.progress}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
                <div
                  className={cn(
                    'h-full rounded-full transition-all',
                    selected.status === 'complete' ? 'bg-operational' : 'bg-primary',
                  )}
                  style={{ width: `${selected.progress}%` }}
                />
              </div>
            </div>

            {/* Stage stepper */}
            <ol className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
              {STAGES.map((stage, i) => {
                const done = selected.status === 'complete' || i < currentStageIndex
                const active = selected.status !== 'complete' && i === currentStageIndex && selected.progress > 0
                return (
                  <li
                    key={stage}
                    className={cn(
                      'flex items-center gap-2 rounded-md border px-3 py-2 font-mono text-[11px]',
                      done
                        ? 'border-operational/40 text-operational'
                        : active
                          ? 'border-primary/50 text-primary'
                          : 'border-border text-muted-foreground',
                    )}
                  >
                    {done ? (
                      <CheckCircle2 className="size-3.5" />
                    ) : active ? (
                      <Loader2 className="size-3.5 animate-spin" />
                    ) : (
                      <Clock className="size-3.5" />
                    )}
                    <span className="truncate">{stage}</span>
                  </li>
                )
              })}
            </ol>
          </Panel>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <Panel>
              <PanelHeader title="Logs preview" />
              <div className="max-h-64 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
                {runLogLines.map((line, i) => (
                  <p key={i} className="whitespace-pre-wrap text-muted-foreground">
                    <span className="text-primary/70">{line.slice(0, 10)}</span>
                    {line.slice(10)}
                  </p>
                ))}
                {selected.status === 'running' ? (
                  <p className="mt-1 flex items-center gap-2 text-primary">
                    <Loader2 className="size-3 animate-spin" /> streaming…
                  </p>
                ) : null}
              </div>
            </Panel>

            <div className="flex flex-col gap-6">
              <Panel>
                <PanelHeader title="Warnings" />
                <div className="flex items-start gap-2 p-4">
                  <AlertTriangle className="mt-0.5 size-4 shrink-0 text-pattern" />
                  <p className="text-sm text-muted-foreground">
                    3 candidate findings flagged as{' '}
                    <span className="text-pattern">requires human review</span> before local use.
                  </p>
                </div>
              </Panel>

              <Panel>
                <PanelHeader title="Generated artifacts" />
                <ul className="p-4">
                  {['candidate_anomalies.json', 'candidate_concepts.json', 'discovery_report.md'].map((f) => (
                    <li
                      key={f}
                      className="flex items-center gap-3 border-b border-border py-2 last:border-b-0"
                    >
                      <FileText className="size-4 text-muted-foreground" />
                      <span className="font-mono text-xs text-foreground">{f}</span>
                      {selected.status === 'complete' ? (
                        <StatusBadge tone="operational" className="ml-auto">Ready</StatusBadge>
                      ) : (
                        <StatusBadge tone="muted" className="ml-auto">Pending</StatusBadge>
                      )}
                    </li>
                  ))}
                </ul>
              </Panel>
            </div>
          </div>

          {selected.status === 'complete' ? (
            <div className="flex items-center gap-2 rounded-md border border-operational/40 bg-operational/10 px-4 py-3">
              <CheckCircle2 className="size-4 text-operational" />
              <p className="text-sm text-operational">
                Run complete · {selected.findings} candidate findings · report generated.
              </p>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function RunStatusBadge({ status }: { status: string }) {
  if (status === 'complete') return <StatusBadge tone="operational" dot>Complete</StatusBadge>
  if (status === 'running') return <StatusBadge tone="anomaly" dot>Running</StatusBadge>
  return <StatusBadge tone="muted" dot>Queued</StatusBadge>
}
