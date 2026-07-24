'use client'

import { useState } from 'react'
import { Copy, Eye, Filter, ThumbsDown, ThumbsUp } from 'lucide-react'
import { Panel, PanelHeader, SectionLabel, StatusBadge, TechButton, MetricRow, ReviewDisclaimer } from '@/components/ade/primitives'
import { findings, type Finding } from '@/lib/ade-data'
import {
  reportAssetUrl,
  submitStudioReviewFeedback,
  type EngineMode,
  type StudioReportDetail,
  type StudioReviewerAction,
} from '@/lib/ade-api'
import { cn } from '@/lib/utils'

interface StudioFinding extends Finding {
  coordinates?: number[] | null
  patchScale?: string | number | null
  scoreBreakdown?: Record<string, unknown> | null
  largestFeatureDeviations?: Array<Record<string, unknown>> | null
  previewUrl?: string | null
  metricLabel?: string
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
  const [selectedId, setSelectedId] = useState(displayFindings[1]?.id ?? displayFindings[0]?.id ?? '')
  const [note, setNote] = useState('')
  const [submittingAction, setSubmittingAction] = useState<StudioReviewerAction | null>(null)
  const [savedActions, setSavedActions] = useState<Record<string, StudioReviewerAction>>({})
  const [feedbackError, setFeedbackError] = useState<string | null>(null)
  const selected = displayFindings.find((f) => f.id === selectedId) ?? displayFindings[0]
  const selectedFeedbackKey = selected
    ? feedbackKey(selectedReport?.report_name, selected.id)
    : ''
  const savedAction = selected ? savedActions[selectedFeedbackKey] : undefined

  async function saveFeedback(action: StudioReviewerAction) {
    if (!connected || !selected || !selectedReport?.report_name || submittingAction) return
    setSubmittingAction(action)
    setFeedbackError(null)
    try {
      const response = await submitStudioReviewFeedback({
        report_name: selectedReport.report_name,
        finding_id: selected.id,
        finding_type: selectedReport.report_type === 'temporal'
          ? 'temporal_candidate'
          : 'visual_candidate',
        reviewer_action: action,
        note: note.trim() || undefined,
      })
      setSavedActions((current) => ({
        ...current,
        [feedbackKey(selectedReport.report_name, selected.id)]: response.reviewer_action,
      }))
      setNote('')
    } catch (error) {
      setFeedbackError(error instanceof Error ? error.message : 'Local review feedback failed.')
    } finally {
      setSubmittingAction(null)
    }
  }

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
                    <span className="font-mono text-xs text-muted-foreground">
                      {f.metricLabel || 'Novelty'}: {formatScore(f.novelty)}
                    </span>
                  </div>
                  <span className="text-sm font-medium text-foreground">{f.title}</span>
                  <VerdictLabel
                    status={f.status}
                    savedAction={savedActions[feedbackKey(selectedReport?.report_name, f.id)]}
                  />
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
            <span className="font-mono text-xs text-muted-foreground">
              {selected.metricLabel || 'Novelty'} {formatScore(selected.novelty)}
            </span>
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
              <MetricRow label={`${selected.metricLabel || 'Novelty'} score`} value={formatScore(selected.novelty)} />
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
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Save local review feedback against this stable candidate ID. Reviewer actions support
          review prioritization and do not scientifically confirm a candidate finding.
        </p>
        <label
          htmlFor="review-note"
          className="mt-4 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground"
        >
          Optional reviewer note
        </label>
        <textarea
          id="review-note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          rows={3}
          maxLength={2000}
          disabled={!connected || submittingAction !== null}
          className="mt-2 w-full resize-none rounded-md border border-border bg-card p-3 text-sm text-foreground focus:border-primary/50 focus:outline-none disabled:opacity-50"
        />
        <div className="mt-3 grid gap-2">
          <TechButton
            variant="secondary"
            className="justify-start border-operational/50 text-operational"
            onClick={() => void saveFeedback('useful')}
            disabled={!connected || submittingAction !== null}
          >
            <ThumbsUp className="size-3.5" />
            {submittingAction === 'useful' ? 'Saving…' : 'Mark useful'}
          </TechButton>
          <TechButton
            variant="secondary"
            className="justify-start border-critical/50 text-critical"
            onClick={() => void saveFeedback('not_useful')}
            disabled={!connected || submittingAction !== null}
          >
            <ThumbsDown className="size-3.5" />
            {submittingAction === 'not_useful' ? 'Saving…' : 'Mark not useful'}
          </TechButton>
          <TechButton
            variant="secondary"
            className="justify-start"
            onClick={() => void saveFeedback('needs_review')}
            disabled={!connected || submittingAction !== null}
          >
            <Eye className="size-3.5" />
            {submittingAction === 'needs_review' ? 'Saving…' : 'Needs review'}
          </TechButton>
        </div>
        {savedAction ? (
          <p className="mt-3 font-mono text-xs text-operational">
            Saved locally: {reviewActionLabel(savedAction)}.
          </p>
        ) : null}
        {feedbackError ? (
          <p role="alert" className="mt-3 text-sm text-critical">{feedbackError}</p>
        ) : null}
        <TechButton
          variant="secondary"
          className="mt-3 justify-start"
          onClick={() => copyText(selected.source)}
          disabled={!selected.source || selected.source === 'Not available from current report'}
        >
          <Copy className="size-3.5" /> Copy source path
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
  if (report.report_type === 'temporal') {
    return (report.candidate_temporal_change_events || []).map((event, index) => {
      const patches = event.patch_evidence || []
      const firstPatch = patches[0]
      const patchNotes = patches.map((patch) =>
        `patch (${patch.x}, ${patch.y}, ${patch.width}, ${patch.height}) ${patch.source_observation_id} → ${patch.target_observation_id}`,
      )
      return {
        id: event.event_id || `candidate-change-${index + 1}`,
        title: `Candidate temporal change ${event.event_id || index + 1}`,
        kind: 'pattern',
        novelty: numberValue(event.change_score, -1),
        confidence: -1,
        deviation: firstPatch ? formatCoordinates([firstPatch.x, firstPatch.y, firstPatch.width, firstPatch.height]) : 'Not available from current report',
        clusterDensity: -1,
        status: 'pending',
        runId: report.temporal_sequence_summary?.sequence_id || 'Not available from current report',
        detector: report.report_name,
        source: `${event.source_observation_id || '?'} → ${event.target_observation_id || '?'}`,
        firstDetected: `${report.temporal_sequence_summary?.range_start || '?'} → ${report.temporal_sequence_summary?.range_end || '?'}`,
        impact: [
          event.possible_interpretation || 'Possible movement/growth/damage/change',
          ...patches.map((patch) => patch.evidence_note).filter(Boolean),
          ...patchNotes,
          'Requires human review.',
        ].join(' · '),
        coordinates: firstPatch ? [firstPatch.x, firstPatch.y, firstPatch.width, firstPatch.height].filter(isNumber) : null,
        patchScale: firstPatch?.patch_scale || null,
        scoreBreakdown: {
          rank: event.rank,
          source_observation_id: event.source_observation_id,
          target_observation_id: event.target_observation_id,
        },
        largestFeatureDeviations: null,
        previewUrl: null,
        metricLabel: 'Change',
      }
    })
  }
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

function VerdictLabel({
  status,
  savedAction,
}: {
  status: Finding['status']
  savedAction?: StudioReviewerAction
}) {
  if (savedAction) {
    return (
      <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-operational">
        {reviewActionLabel(savedAction)}
      </span>
    )
  }
  const map: Record<Finding['status'], { label: string; className: string }> = {
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

function reviewActionLabel(action: StudioReviewerAction) {
  if (action === 'useful') return 'Reviewer-marked useful'
  if (action === 'not_useful') return 'Reviewer-marked not useful'
  return 'Needs review'
}

function feedbackKey(reportName: string | undefined, findingId: string) {
  return `${reportName || 'no-report'}::${findingId}`
}

function copyText(value?: string | null) {
  if (!value || typeof navigator === 'undefined' || !navigator.clipboard) return
  void navigator.clipboard.writeText(value)
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
