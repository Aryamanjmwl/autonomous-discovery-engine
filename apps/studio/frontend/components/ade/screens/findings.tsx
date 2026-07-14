'use client'

import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Eye, Download, Filter } from 'lucide-react'
import { Panel, PanelHeader, SectionLabel, StatusBadge, TechButton, MetricRow, ReviewDisclaimer } from '@/components/ade/primitives'
import { findings, type Finding, type ReviewStatus } from '@/lib/ade-data'
import { reportAssetUrl, type EngineMode, type StudioReportDetail } from '@/lib/ade-api'
import { cn } from '@/lib/utils'

interface StudioFinding extends Finding {
  coordinates?: number[] | null
  patchScale?: string | number | null
  scoreBreakdown?: Record<string, unknown> | null
  largestFeatureDeviations?: Array<Record<string, unknown>> | null
  previewUrl?: string | null
}

export function FindingsScreen({
  selectedReport,
  engineMode,
}: {
  selectedReport: StudioReportDetail | null
  engineMode: EngineMode
}) {
  const connected = engineMode === 'connected'
  const displayFindings = reportFindings(selectedReport, connected)
  const [reviews, setReviews] = useState<Record<string, ReviewStatus>>(
    Object.fromEntries(displayFindings.map((f) => [f.id, f.status])),
  )
  const [selectedId, setSelectedId] = useState(displayFindings[1]?.id ?? displayFindings[0]?.id ?? '')
  const selected = displayFindings.find((f) => f.id === selectedId) ?? displayFindings[0]
  const selectedStatus = selected ? reviews[selected.id] ?? 'pending' : 'pending'

  const setVerdict = (status: ReviewStatus) =>
    selected ? setReviews((prev) => ({ ...prev, [selected.id]: status })) : undefined

  if (!selected) {
    return (
      <Panel className="p-5">
        <PanelHeader title="Candidates (0)" />
        <p className="mt-4 text-sm text-muted-foreground">
          Not available from current report. Generate or select a local ADE JSON report with candidate findings.
        </p>
      </Panel>
    )
  }

  return (
    <div className="grid h-full grid-cols-1 gap-6 xl:grid-cols-[minmax(0,300px)_1fr_minmax(0,280px)]">
      {/* Candidate list */}
      <Panel className="flex flex-col">
        <PanelHeader
          title={`Candidates (${displayFindings.length})`}
          action={<Filter className="size-4 text-muted-foreground" />}
        />
        <ul className="flex-1 overflow-y-auto">
          {displayFindings.map((f) => {
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
                    <span className="font-mono text-xs text-muted-foreground">N: {formatScore(f.novelty)}</span>
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
            <span className="font-mono text-xs text-muted-foreground">Novelty {formatScore(selected.novelty)}</span>
          </div>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">{selected.title}</h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            First detected: {selected.firstDetected} · Run ID: {selected.runId}
          </p>
        </div>

        <ReviewDisclaimer />

        <Panel>
          <PanelHeader title="Evidence preview" />
          <div className="relative min-h-48 w-full overflow-hidden rounded-b-lg p-4">
            <EvidencePreview
              previewUrl={selected.previewUrl}
              source={selected.source}
              connected={connected}
            />
          </div>
        </Panel>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Panel className="p-4">
            <SectionLabel>Statistical evidence</SectionLabel>
            <div className="mt-2 divide-y divide-border">
              <MetricRow label="Confidence score" value={formatScore(selected.confidence)} valueClassName="text-anomaly" />
              <MetricRow label="Coordinates" value={formatCoordinates(selected.coordinates)} />
              <MetricRow label="Patch scale" value={formatValue(selected.patchScale)} />
              <MetricRow label="Novelty score" value={formatScore(selected.novelty)} />
            </div>
          </Panel>
          <Panel className="p-4">
            <SectionLabel>Evidence note</SectionLabel>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{selected.impact}</p>
            <div className="mt-4 divide-y divide-border">
              <MetricRow label="Score breakdown" value={formatObject(selected.scoreBreakdown)} />
              <MetricRow
                label="Feature deviations"
                value={formatFeatureDeviations(selected.largestFeatureDeviations)}
              />
            </div>
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
          <MetaItem label="Report" value={selected.detector} />
          <MetaItem label="Source" value={selected.source} />
        </dl>
      </Panel>
    </div>
  )
}

function reportFindings(report: StudioReportDetail | null, connected: boolean): StudioFinding[] {
  if (!report) return connected ? [] : findings
  const anomalies = report.candidate_anomalies || []
  const concepts = report.candidate_concepts || []
  const anomalyFindings = anomalies.slice(0, 12).map((item, index) =>
    findingFromReportItem(item, index, 'anomaly', report),
  )
  const conceptFindings = concepts.slice(0, 8).map((item, index) =>
    findingFromReportItem(item, index, 'concept', report),
  )
  const reportRows = [...anomalyFindings, ...conceptFindings].filter(Boolean) as StudioFinding[]
  return reportRows.length > 0 ? reportRows : connected ? [] : findings
}

function findingFromReportItem(
  item: unknown,
  index: number,
  kind: 'anomaly' | 'concept',
  report: StudioReportDetail,
): StudioFinding | null {
  if (!item || typeof item !== 'object') return null
  const row = item as Record<string, unknown>
  const id = stringValue(row.anomaly_id || row.concept_id, `${kind}-${index + 1}`)
  const novelty = numberValue(row.novelty_score || row.average_novelty || row.average_novelty_score, -1)
  const confidence = numberValue(row.confidence_score, -1)
  const previewAssetName = stringValue(row.preview_asset_name, '')
  return {
    id,
    title: kind === 'concept' ? `Candidate concept ${id}` : `Candidate anomaly ${id}`,
    kind,
    novelty,
    confidence,
    deviation: formatCoordinates(row.coordinates),
    clusterDensity: numberValue(row.consistency_score || row.cluster_consistency, -1),
    status: 'pending',
    runId: stringValue(row.run_id, report.run_id || 'Not available from current report'),
    detector: report.report_name,
    source: firstStringValue(
      row.source_image_path,
      row.source_path,
      row.image_path,
      row.patch_image_path,
      row.evidence_path,
      row.asset_path,
      'Not available from current report',
    ),
    firstDetected: stringValue(row.generated_at, report.generated_at || 'Not available from current report'),
    impact: stringValue(
      row.evidence_note || row.reason || row.summary || row.possible_pattern,
      'Candidate finding from the selected ADE report. Requires human review.',
    ),
    coordinates: Array.isArray(row.coordinates) ? row.coordinates.filter(isNumber) : null,
    patchScale: (row.patch_scale as string | number | null) ?? null,
    scoreBreakdown: objectValue(row.score_breakdown),
    largestFeatureDeviations: Array.isArray(row.largest_feature_deviations)
      ? (row.largest_feature_deviations as Array<Record<string, unknown>>)
      : null,
    previewUrl: reportAssetUrl(previewAssetName),
  }
}

function stringValue(value: unknown, fallback: string) {
  return typeof value === 'string' && value.length > 0 ? value : fallback
}

function firstStringValue(...values: unknown[]) {
  const fallback = values[values.length - 1]
  for (const value of values.slice(0, -1)) {
    if (typeof value === 'string' && value.length > 0) return value
  }
  return typeof fallback === 'string' ? fallback : 'Not available from current report'
}

function numberValue(value: unknown, fallback = 0) {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function objectValue(value: unknown) {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function isNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function formatScore(value: number) {
  return value >= 0 ? value.toFixed(2) : 'Not available'
}

function formatValue(value: string | number | null | undefined) {
  return value === null || value === undefined || value === ''
    ? 'Not available'
    : String(value)
}

function formatCoordinates(value: unknown) {
  return Array.isArray(value) && value.length > 0
    ? value.join(', ')
    : 'Not available from current report'
}

function formatObject(value: Record<string, unknown> | null | undefined) {
  if (!value) return 'Not available from current report'
  return Object.entries(value)
    .map(([key, item]) => `${key}: ${String(item)}`)
    .join(' · ')
}

function formatFeatureDeviations(value: Array<Record<string, unknown>> | null | undefined) {
  if (!value || value.length === 0) return 'Not available from current report'
  return value
    .slice(0, 3)
    .map((item) => {
      const feature = stringValue(item.feature, 'feature')
      const deviation = numberValue(item.deviation, -1)
      return `${feature}: ${formatScore(deviation)}`
    })
    .join(' · ')
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

function EvidencePreview({
  previewUrl,
  source,
  connected,
}: {
  previewUrl?: string | null
  source: string
  connected: boolean
}) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-md border border-border bg-card p-4 text-center">
      {previewUrl ? (
        <img
          src={previewUrl}
          alt={`Preview asset for ${source}`}
          className="max-h-72 max-w-full rounded border border-border object-contain"
        />
      ) : (
        <p className="text-sm text-muted-foreground">
          {connected
            ? 'Preview asset is not available for this candidate.'
            : 'Mock Preview evidence is available only in fallback mode.'}
        </p>
      )}
    </div>
  )
}
