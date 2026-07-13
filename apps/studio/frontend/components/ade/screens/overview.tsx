'use client'

import { Panel, PanelHeader, StatusBadge, SectionLabel } from '@/components/ade/primitives'
import { findings, timeline, type ScreenId } from '@/lib/ade-data'
import { cn } from '@/lib/utils'

const toneText: Record<string, string> = {
  anomaly: 'text-anomaly',
  operational: 'text-operational',
  concept: 'text-concept',
  muted: 'text-faint',
}
const toneBorder: Record<string, string> = {
  anomaly: 'border-l-anomaly',
  operational: 'border-l-operational',
  concept: 'border-l-concept',
  muted: 'border-l-border-strong',
}

export function OverviewScreen({ onNavigate }: { onNavigate: (id: ScreenId) => void }) {
  const recent = findings.slice(0, 5)

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      {/* header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-primary">
            Mission Control
          </p>
          <h1 className="mt-1 text-xl font-semibold tracking-tight text-foreground">
            Manufacturing QC Pipeline
          </h1>
        </div>
        <div className="flex items-center gap-5">
          <HeaderStat label="Precision" value="0.847" delta="+1.2%" />
          <HeaderStat label="Recall" value="0.912" delta="+0.4%" />
          <StatusBadge tone="operational" dot>
            Local Engine Ready
          </StatusBadge>
        </div>
      </div>

      {/* asymmetric cockpit grid */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 xl:grid-cols-[248px_minmax(0,1fr)_312px]">
        {/* LEFT - local engine context */}
        <div className="flex min-h-0 flex-col gap-4 overflow-y-auto xl:pr-0.5">
          <Panel className="p-4">
            <SectionLabel>Local execution</SectionLabel>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-mono text-2xl leading-none text-foreground">ACTIVE</span>
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-primary">
                Idle
              </span>
            </div>
            <p className="mt-2 font-mono text-[11px] text-faint">Uptime 47h 12m · isolated</p>
          </Panel>

          <Panel className="p-4">
            <SectionLabel>Active datasets</SectionLabel>
            <div className="mt-2 flex items-baseline justify-between">
              <span className="font-mono text-2xl leading-none text-foreground">04</span>
              <span className="font-mono text-[11px] text-faint">8.4 GB</span>
            </div>
          </Panel>

          <Panel className="flex-1 p-4">
            <SectionLabel>Candidate findings</SectionLabel>
            <ul className="mt-3 flex flex-col gap-2.5">
              <FindingCount tone="anomaly" label="Candidate Anomalies" value="12" />
              <FindingCount tone="concept" label="Candidate Concepts" value="05" />
              <FindingCount tone="pattern" label="Possible Patterns" value="03" />
            </ul>
          </Panel>

          <Panel className="p-4">
            <div className="flex items-center justify-between">
              <SectionLabel>Human review</SectionLabel>
              <span className="font-mono text-[11px] text-pattern">7 pending</span>
            </div>
            <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-raised">
              <span className="block h-full w-[77%] rounded-full bg-operational" />
            </div>
            <p className="mt-2 font-mono text-[11px] text-faint">23 verified · 30 total</p>
          </Panel>
        </div>

        {/* CENTER — discovery field (dominant) */}
        <div className="flex min-h-0 flex-col gap-4">
          <Panel className="flex min-h-0 flex-1 flex-col">
            <PanelHeader
              title="Discovery Field · Topological Projection"
              accent="anomaly"
              action={
                <span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.13em] text-faint">
                  <span className="size-1.5 animate-pulse rounded-full bg-operational" />
                  Local run telemetry
                </span>
              }
            />
            <div className="relative min-h-[260px] flex-1 overflow-hidden">
              <DiscoveryField />
            </div>
            <div className="grid grid-cols-3 divide-x divide-border border-t border-border">
              <FieldStat label="Nodes" value="20" tone="muted" />
              <FieldStat label="Clusters" value="03" tone="concept" />
              <FieldStat label="Drift warn" value="01" tone="pattern" />
            </div>
          </Panel>

          {/* recent candidate findings */}
          <Panel className="shrink-0">
            <PanelHeader
              title="Recent Candidate Findings"
              action={
                <button
                  type="button"
                  onClick={() => onNavigate('findings')}
                  className="font-mono text-[10px] uppercase tracking-[0.13em] text-primary hover:underline"
                >
                  Review all →
                </button>
              }
            />
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-border text-left font-mono text-[10px] uppercase tracking-[0.13em] text-faint">
                  <th className="px-4 py-2 font-normal">Finding</th>
                  <th className="px-4 py-2 font-normal">Type</th>
                  <th className="px-4 py-2 text-right font-normal">Novelty</th>
                  <th className="px-4 py-2 text-right font-normal">Conf.</th>
                  <th className="px-4 py-2 font-normal">Status</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((f) => (
                  <tr
                    key={f.id}
                    className="cursor-pointer border-b border-border last:border-b-0 hover:bg-card"
                    onClick={() => onNavigate('findings')}
                  >
                    <td className="px-4 py-2.5 text-foreground">{f.title}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge tone={f.kind}>{formatFindingKind(f.kind)}</StatusBadge>
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-foreground">
                      {f.novelty.toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular-nums text-muted-foreground">
                      {f.confidence.toFixed(2)}
                    </td>
                    <td className="px-4 py-2.5">
                      <ReviewPill status={f.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>

        {/* RIGHT — evidence feed */}
        <div className="flex min-h-0 flex-col gap-4 overflow-y-auto">
          <Panel className="flex min-h-0 flex-1 flex-col">
            <PanelHeader title="Evidence Feed" accent="concept" />
            <ul className="flex-1 overflow-y-auto">
              {timeline.map((event) => (
                <li
                  key={event.id}
                  className={cn(
                    'border-b border-border border-l-2 px-4 py-3 last:border-b-0',
                    toneBorder[event.tone],
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] tabular-nums text-faint">
                      {event.time}
                    </span>
                    <span
                      className={cn(
                        'font-mono text-[10px] uppercase tracking-[0.13em]',
                        toneText[event.tone],
                      )}
                    >
                      {event.label}
                    </span>
                  </div>
                  <p className="mt-1 text-[13px] text-foreground">{event.detail}</p>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel className="shrink-0">
            <PanelHeader title="Local Run Benchmarks" />
            <div className="grid grid-cols-2 divide-x divide-border">
              <BenchCell label="Precision" value="0.847" delta="+1.2%" />
              <BenchCell label="Recall" value="0.912" delta="+0.4%" />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */

function HeaderStat({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <div className="hidden text-right sm:block">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{label}</p>
      <p className="font-mono text-sm tabular-nums text-foreground">
        {value} <span className="text-operational">{delta}</span>
      </p>
    </div>
  )
}

function FindingCount({
  tone,
  label,
  value,
}: {
  tone: 'anomaly' | 'concept' | 'pattern'
  label: string
  value: string
}) {
  const dot = { anomaly: 'bg-anomaly', concept: 'bg-concept', pattern: 'bg-pattern' }[tone]
  return (
    <li className="flex items-center justify-between">
      <span className="flex items-center gap-2.5 text-[13px] text-muted-foreground">
        <span className={cn('size-1.5 rounded-full', dot)} />
        {label}
      </span>
      <span className="font-mono text-base tabular-nums text-foreground">{value}</span>
    </li>
  )
}

function FieldStat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone: 'anomaly' | 'concept' | 'pattern' | 'muted'
}) {
  const text = {
    anomaly: 'text-anomaly',
    concept: 'text-concept',
    pattern: 'text-pattern',
    muted: 'text-foreground',
  }[tone]
  return (
    <div className="flex items-center justify-between px-4 py-2.5">
      <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-faint">{label}</span>
      <span className={cn('font-mono text-base tabular-nums', text)}>{value}</span>
    </div>
  )
}

function BenchCell({ label, value, delta }: { label: string; value: string; delta: string }) {
  return (
    <div className="p-4">
      <SectionLabel>{label}</SectionLabel>
      <p className="mt-1.5 font-mono text-2xl tabular-nums text-foreground">{value}</p>
      <p className="font-mono text-[11px] text-operational">{delta}</p>
    </div>
  )
}

export function ReviewPill({ status }: { status: string }) {
  const map: Record<
    string,
    { tone: 'anomaly' | 'operational' | 'critical' | 'pattern' | 'muted'; label: string }
  > = {
    pending: { tone: 'muted', label: 'Pending' },
    useful: { tone: 'operational', label: 'Useful' },
    'not-useful': { tone: 'critical', label: 'Not useful' },
    'needs-review': { tone: 'pattern', label: 'Needs review' },
    reviewed: { tone: 'anomaly', label: 'Reviewed' },
  }
  const cfg = map[status] ?? map.pending
  return <StatusBadge tone={cfg.tone}>{cfg.label}</StatusBadge>
}

function formatFindingKind(kind: string) {
  const labels: Record<string, string> = {
    anomaly: 'Candidate anomaly',
    concept: 'Candidate concept',
    pattern: 'Possible pattern',
  }
  return labels[kind] ?? kind
}

/* ------------------------------------------------------------------ */
/* Discovery Field — topological projection with nodes + scan sweep    */
/* ------------------------------------------------------------------ */

function DiscoveryField() {
  // deterministic scatter of faint background nodes
  const scatter = Array.from({ length: 16 }, (_, i) => {
    const x = ((i * 37) % 92) + 4
    const y = ((i * 53) % 86) + 7
    return { x, y, key: i }
  })

  return (
    <div className="ade-grid absolute inset-0">
      <svg className="absolute inset-0 h-full w-full" aria-hidden preserveAspectRatio="none">
        {/* connection lines between primary nodes */}
        <line x1="26%" y1="28%" x2="56%" y2="54%" stroke="oklch(1 0 0 / 16%)" strokeWidth="1" strokeDasharray="3 4" />
        <line x1="56%" y1="54%" x2="42%" y2="82%" stroke="oklch(1 0 0 / 16%)" strokeWidth="1" strokeDasharray="3 4" />
        <line x1="56%" y1="54%" x2="80%" y2="34%" stroke="oklch(1 0 0 / 12%)" strokeWidth="1" strokeDasharray="3 4" />
      </svg>

      {/* faint background candidates */}
      {scatter.map((p) => (
        <span
          key={p.key}
          className="absolute size-1 rounded-full bg-muted-foreground/25"
          style={{ left: `${p.x}%`, top: `${p.y}%` }}
        />
      ))}

      {/* cluster ring */}
      <div
        className="absolute -translate-x-1/2 -translate-y-1/2"
        style={{ left: '56%', top: '54%' }}
      >
        <span className="block size-16 rounded-full border border-concept/40 bg-concept/5" />
        <span className="absolute inset-0 m-auto size-2.5 rounded-full bg-concept" />
        <span className="absolute left-1/2 top-full mt-1 -translate-x-1/2 whitespace-nowrap font-mono text-[10px] tracking-[0.1em] text-concept">
          CLUSTER_D3
        </span>
      </div>

      <FieldMarker left="26%" top="28%" tone="anomaly" label="NODE_A7" />
      <FieldMarker left="42%" top="82%" tone="pattern" label="DRIFT_WARN_Q2" glow />
      <FieldMarker left="80%" top="34%" tone="anomaly" label="NODE_B3" small />

      {/* scan sweep */}
      <div className="pointer-events-none absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-transparent via-primary/[0.06] to-transparent [animation:ade-sweep_6s_linear_infinite]" />

      <style jsx>{`
        @keyframes ade-sweep {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(1400%);
          }
        }
      `}</style>
    </div>
  )
}

function FieldMarker({
  left,
  top,
  tone,
  label,
  glow,
  small,
}: {
  left: string
  top: string
  tone: 'anomaly' | 'concept' | 'pattern'
  label: string
  glow?: boolean
  small?: boolean
}) {
  const bg = { anomaly: 'bg-anomaly', concept: 'bg-concept', pattern: 'bg-pattern' }[tone]
  const text = { anomaly: 'text-anomaly', concept: 'text-concept', pattern: 'text-pattern' }[tone]
  return (
    <div className="absolute -translate-x-1/2 -translate-y-1/2 text-center" style={{ left, top }}>
      <span
        className={cn(
          'mx-auto block rounded-full',
          bg,
          small ? 'size-2' : 'size-2.5',
          glow && 'shadow-[0_0_12px_2px_var(--pattern)]',
        )}
      />
      <span
        className={cn(
          'mt-1.5 block whitespace-nowrap font-mono text-[10px] tracking-[0.1em]',
          text,
        )}
      >
        {label}
      </span>
    </div>
  )
}
