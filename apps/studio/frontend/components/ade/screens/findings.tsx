'use client'

import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Eye, Download, Filter } from 'lucide-react'
import { Panel, PanelHeader, SectionLabel, StatusBadge, TechButton, MetricRow, ReviewDisclaimer } from '@/components/ade/primitives'
import { findings, type Finding, type ReviewStatus } from '@/lib/ade-data'
import { cn } from '@/lib/utils'

export function FindingsScreen() {
  const [reviews, setReviews] = useState<Record<string, ReviewStatus>>(
    Object.fromEntries(findings.map((f) => [f.id, f.status])),
  )
  const [selectedId, setSelectedId] = useState(findings[1].id)
  const selected = findings.find((f) => f.id === selectedId) ?? findings[0]
  const selectedStatus = reviews[selected.id]

  const setVerdict = (status: ReviewStatus) =>
    setReviews((prev) => ({ ...prev, [selected.id]: status }))

  return (
    <div className="grid h-full grid-cols-1 gap-6 xl:grid-cols-[minmax(0,300px)_1fr_minmax(0,280px)]">
      {/* Candidate list */}
      <Panel className="flex flex-col">
        <PanelHeader
          title={`Candidates (${findings.length})`}
          action={<Filter className="size-4 text-muted-foreground" />}
        />
        <ul className="flex-1 overflow-y-auto">
          {findings.map((f) => {
            const status = reviews[f.id]
            const isSel = f.id === selectedId
            return (
              <li key={f.id}>
                <button
                  type="button"
                  onClick={() => setSelectedId(f.id)}
                  className={cn(
                    'flex w-full flex-col gap-2 border-b border-border px-4 py-3 text-left transition-colors last:border-b-0',
                    isSel ? 'bg-primary/10 ring-1 ring-inset ring-primary/40' : 'hover:bg-card',
                  )}
                >
                  <div className="flex items-center justify-between">
                    <StatusBadge tone={f.kind}>{formatFindingKind(f.kind)}</StatusBadge>
                    <span className="font-mono text-xs text-muted-foreground">N: {f.novelty.toFixed(2)}</span>
                  </div>
                  <span className="text-sm font-medium text-foreground">{f.title}</span>
                  <VerdictLabel status={status} />
                </button>
              </li>
            )
          })}
        </ul>
      </Panel>

      {/* Evidence detail */}
      <div className="flex flex-col gap-6">
        <div>
          <div className="flex items-center gap-3">
            <StatusBadge tone={selected.kind}>{formatFindingKind(selected.kind)}</StatusBadge>
            <span className="font-mono text-xs text-muted-foreground">Novelty {selected.novelty.toFixed(2)}</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{selected.title}</h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            First detected: {selected.firstDetected} · Run ID: {selected.runId}
          </p>
        </div>

        <ReviewDisclaimer />

        {/* Evidence chart */}
        <Panel>
          <PanelHeader title="Evidence preview · signal window" />
          <div className="ade-grid relative h-64 w-full overflow-hidden rounded-b-lg p-4">
            <EvidenceSparkline seed={selected.id} />
          </div>
        </Panel>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Panel className="p-4">
            <SectionLabel>Statistical evidence</SectionLabel>
            <div className="mt-2 divide-y divide-border">
              <MetricRow label="Confidence score" value={selected.confidence.toFixed(2)} valueClassName="text-anomaly" />
              <MetricRow label="Deviation (σ)" value={selected.deviation} />
              <MetricRow label="Cluster density" value={selected.clusterDensity.toFixed(2)} />
              <MetricRow label="Novelty score" value={selected.novelty.toFixed(2)} />
            </div>
          </Panel>
          <Panel className="p-4">
            <SectionLabel>Impact analysis</SectionLabel>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{selected.impact}</p>
          </Panel>
        </div>
      </div>

      {/* Review actions */}
      <Panel className="flex flex-col p-4 xl:h-fit">
        <SectionLabel>Review actions</SectionLabel>
        <div className="mt-3 flex flex-col gap-2">
          <TechButton
            variant="secondary"
            active={selectedStatus === 'useful'}
            aria-pressed={selectedStatus === 'useful'}
            onClick={() => setVerdict('useful')}
            className={cn('justify-start', selectedStatus === 'useful' && 'border-operational text-operational')}
          >
            <ThumbsUp className="size-3.5" /> Useful
          </TechButton>
          <TechButton
            variant="secondary"
            active={selectedStatus === 'not-useful'}
            aria-pressed={selectedStatus === 'not-useful'}
            onClick={() => setVerdict('not-useful')}
            className={cn('justify-start', selectedStatus === 'not-useful' && 'border-critical text-critical')}
          >
            <ThumbsDown className="size-3.5" /> Not useful
          </TechButton>
          <TechButton
            variant="secondary"
            active={selectedStatus === 'needs-review'}
            aria-pressed={selectedStatus === 'needs-review'}
            onClick={() => setVerdict('needs-review')}
            className={cn('justify-start', selectedStatus === 'needs-review' && 'border-pattern text-pattern')}
          >
            <Eye className="size-3.5" /> Needs review
          </TechButton>
        </div>

        <div className="my-4 h-px bg-border" />

        <TechButton variant="secondary" className="justify-start">
          <Download className="size-3.5" /> Export data
        </TechButton>

        <div className="my-4 h-px bg-border" />

        <SectionLabel>Analysis metadata</SectionLabel>
        <dl className="mt-3 flex flex-col gap-3">
          <MetaItem label="Run ID" value={selected.runId} />
          <MetaItem label="Detector" value={selected.detector} />
          <MetaItem label="Source" value={selected.source} />
        </dl>
      </Panel>
    </div>
  )
}

function formatFindingKind(kind: string) {
  const labels: Record<string, string> = {
    anomaly: 'Candidate anomaly',
    concept: 'Candidate concept',
    pattern: 'Possible pattern',
  }
  return labels[kind] ?? kind
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-mono text-sm text-foreground">{value}</dd>
    </div>
  )
}

function VerdictLabel({ status }: { status: ReviewStatus }) {
  const map: Record<ReviewStatus, { label: string; className: string }> = {
    pending: { label: 'Pending', className: 'text-muted-foreground' },
    useful: { label: 'Useful', className: 'text-operational' },
    'not-useful': { label: 'Not useful', className: 'text-critical' },
    'needs-review': { label: 'Flagged · needs review', className: 'text-pattern' },
    reviewed: { label: 'Reviewed', className: 'text-anomaly' },
  }
  const cfg = map[status]
  return (
    <span className={cn('font-mono text-[10px] uppercase tracking-[0.12em]', cfg.className)}>{cfg.label}</span>
  )
}

// Deterministic pseudo-random sparkline so evidence looks like a real signal window.
function EvidenceSparkline({ seed }: { seed: string }) {
  const n = 60
  let s = 0
  for (let i = 0; i < seed.length; i++) s += seed.charCodeAt(i)
  const points = Array.from({ length: n }, (_, i) => {
    const noise = Math.sin(i * 0.6 + s) * 0.5 + Math.sin(i * 0.17 + s * 0.3) * 0.3
    const spike = i > n * 0.55 && i < n * 0.7 ? 0.8 : 0
    const y = 50 - (noise + spike) * 26
    return `${(i / (n - 1)) * 100},${Math.max(6, Math.min(94, y))}`
  }).join(' ')

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full">
      <polyline points={points} fill="none" stroke="oklch(0.78 0.15 210)" strokeWidth="0.8" vectorEffect="non-scaling-stroke" />
      <rect x="55" y="0" width="15" height="100" fill="oklch(0.66 0.2 25 / 12%)" />
    </svg>
  )
}
