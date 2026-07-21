'use client'

import { useState } from 'react'
import { Copy, ExternalLink, ShieldCheck } from 'lucide-react'
import { Panel, KpiCard, StatusBadge, TechButton } from '@/components/ade/primitives'
import { reports, type ReportRecord } from '@/lib/ade-data'
import { reportHtmlUrl, type EngineMode, type StudioReport, type StudioReportDetail } from '@/lib/ade-api'
import { cn } from '@/lib/utils'

export function ReportsScreen({
  reportsFromApi,
  selectedReport,
  engineMode,
  onSelectReport,
}: {
  reportsFromApi: StudioReport[]
  selectedReport: StudioReportDetail | null
  engineMode: EngineMode
  onSelectReport: (reportName: string) => void
}) {
  const connected = engineMode === 'connected'
  const displayReports = connected ? reportsFromApi.map(toReportRecord) : reports
  const [selectedId, setSelectedId] = useState(displayReports[0]?.id ?? '')
  const selected = displayReports.find((r) => r.id === selectedId) ?? displayReports[0]
  const apiSelected = reportsFromApi.find((report) => report.name === selectedId)
  const reportDetail = connected ? selectedReport : null
  const noveltyAverage = average(
    reportDetail?.candidate_anomalies.map((item) => item.novelty_score ?? null) || [],
  )
  const conceptConfidenceAverage = average(
    reportDetail?.candidate_concepts.map((item) => numberValue(item.confidence_score)) || [],
  )
  const markdownPath = reportDetail?.markdown_report_path || apiSelected?.markdown_path
  const jsonPath = reportDetail?.json_report_path || apiSelected?.path
  const htmlPath = reportDetail?.html_report_path || apiSelected?.html_path
  const htmlUrl = reportHtmlUrl(reportDetail?.report_name || apiSelected?.name)

  return (
    <div className="grid h-full grid-cols-1 gap-6 lg:grid-cols-[minmax(0,300px)_1fr]">
      {/* Report list */}
      <Panel className="flex flex-col">
        <div className="border-b border-border p-3">
          <div className="rounded-md border border-border bg-card px-3 py-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.13em] text-faint">
              {connected ? 'Local report list' : 'Mock preview reports'}
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              {connected ? 'Loaded from the connected ADE backend.' : 'Demo-only fallback content.'}
            </p>
          </div>
        </div>
        {displayReports.length === 0 ? (
          <div className="p-4 text-sm text-muted-foreground">
            No local reports are available from the connected backend yet.
          </div>
        ) : (
        <ul className="flex-1 overflow-y-auto">
          {displayReports.map((r) => {
            const isSel = r.id === selectedId
            return (
              <li key={r.id}>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedId(r.id)
                    if (reportsFromApi.length > 0) onSelectReport(r.id)
                  }}
                  className={cn(
                    'flex w-full flex-col gap-2 border-b border-border px-4 py-3 text-left transition-colors last:border-b-0',
                    isSel ? 'bg-primary/10 ring-1 ring-inset ring-primary/40' : 'hover:bg-card',
                  )}
                >
                  <span className="text-sm font-medium text-foreground">{r.title}</span>
                  <div className="flex items-center justify-between font-mono text-[11px] text-muted-foreground">
                    <span>{r.date}</span>
                    <span>{r.findings} findings</span>
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
        )}
      </Panel>

      {/* Report detail */}
      {selected ? (
      <div className="flex flex-col gap-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <StatusBadge tone="anomaly">Report_draft</StatusBadge>
            <h1 className="mt-2 text-2xl font-semibold tracking-tight text-foreground">
              {reportDetail?.report_name || selected.title}
            </h1>
            <p className="mt-1 font-mono text-xs text-muted-foreground">
              {selected.project} · {reportDetail?.run_id || selected.runId}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <TechButton variant="secondary" onClick={() => copyText(markdownPath)} disabled={!markdownPath}>
              <Copy className="size-3.5" /> Markdown
            </TechButton>
            <TechButton variant="secondary" onClick={() => copyText(jsonPath)} disabled={!jsonPath}>
              <Copy className="size-3.5" /> JSON
            </TechButton>
            <TechButton variant="secondary" onClick={() => copyText(htmlPath)} disabled={!htmlPath}>
              <Copy className="size-3.5" /> HTML path
            </TechButton>
            <TechButton
              variant="primary"
              onClick={() => openReportHtml(htmlUrl)}
              disabled={!htmlPath || !htmlUrl}
            >
              <ExternalLink className="size-3.5" /> View HTML
            </TechButton>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <KpiCard
            label="Findings"
            value={reportDetail?.candidate_anomaly_count ?? selected.findings}
            hint={connected ? `${reportDetail?.candidate_concept_count ?? 0} concepts` : `${selected.critical} critical`}
            hintTone={connected ? 'concept' : 'critical'}
          />
          <KpiCard
            label="Novelty avg"
            value={connected ? formatAverage(noveltyAverage) : selected.noveltyAvg.toFixed(2)}
          />
          <KpiCard
            label="Concept confidence"
            value={connected ? formatAverage(conceptConfidenceAverage) : selected.confidence.toFixed(2)}
          />
          <KpiCard
            label="Status"
            value={apiSelected?.human_review_required || reportDetail?.human_review_required ? 'Review required' : 'Not available'}
            hint={connected ? 'Human review' : 'Reviewed'}
            hintTone={connected ? 'pattern' : 'operational'}
          />
        </div>

        <Panel className="p-5">
          <h2 className="text-lg font-semibold text-foreground">Evidence Summary</h2>
          <div className="mt-4 rounded-md border border-border bg-card p-5">
            {reportSummary(selected, selectedReport).split('\n\n').map((para, i) => (
              <p key={i} className={cn('text-sm leading-relaxed text-muted-foreground', i > 0 && 'mt-4')}>
                {para}
              </p>
            ))}
          </div>
        </Panel>

        {reportDetail?.advanced_evidence && Object.keys(reportDetail.advanced_evidence).length > 0 ? (
          <AdvancedEvidence evidence={reportDetail.advanced_evidence} />
        ) : null}

        {reportDetail ? (
          <Panel className="p-5">
            <h2 className="text-lg font-semibold text-foreground">Report Metadata</h2>
            <dl className="mt-4 grid gap-2 font-mono text-xs text-muted-foreground md:grid-cols-2">
              <ArtifactRow label="Run ID" value={reportDetail.run_id} />
              <ArtifactRow label="Generated" value={reportDetail.generated_at} />
              <ArtifactRow label="Input" value={reportDetail.input_directory} />
              <ArtifactRow label="Input type" value={reportDetail.input_type} />
              <ArtifactRow label="Images" value={String(reportDetail.number_of_images)} />
              <ArtifactRow label="Patches" value={String(reportDetail.number_of_patches)} />
              <ArtifactRow label="Novelty" value={reportDetail.novelty_strategy} />
              <ArtifactRow
                label="Review"
                value={reportDetail.human_review_required ? 'Requires human review' : 'Not available'}
              />
            </dl>
          </Panel>
        ) : null}

        {apiSelected || reportDetail ? (
          <Panel className="p-5">
            <h2 className="text-lg font-semibold text-foreground">Local Artifacts</h2>
            <dl className="mt-4 grid gap-2 font-mono text-xs text-muted-foreground">
              <ArtifactRow label="Markdown" value={markdownPath} />
              <ArtifactRow label="JSON" value={jsonPath} />
              <ArtifactRow label="HTML" value={htmlPath} />
            </dl>
          </Panel>
        ) : null}

        {!connected ? (
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
              Mock validation integrity
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3 rounded-md border border-border bg-card px-4 py-3">
              <ShieldCheck className="size-4 text-operational" />
              <span className="font-mono text-xs text-muted-foreground">
                Mock Preview · validation values are demo-only
              </span>
            </div>
          </div>
        ) : null}
      </div>
      ) : (
        <Panel className="p-5">
          <p className="text-sm text-muted-foreground">
            Not available from current report. Generate a local ADE report to populate this view.
          </p>
        </Panel>
      )}
    </div>
  )
}

function toReportRecord(report: StudioReport): ReportRecord {
  return {
    id: report.name,
    title: report.name,
    project: 'ADE Local Engine',
    date: report.generated_at || 'local report',
    runId: report.run_id || 'unknown-run',
    findings: report.candidate_anomaly_count,
    critical: 0,
    noveltyAvg: 0,
    confidence: 0,
    reviewed: 0,
    summary: 'Local ADE JSON report loaded from the connected backend. Candidate findings require human review.',
    hash: '',
  }
}

function reportSummary(selected: ReportRecord, report: StudioReportDetail | null) {
  if (!report) return selected.summary
  return [
    `This local ADE report contains ${report.candidate_anomaly_count} candidate anomalies and ${report.candidate_concept_count} candidate concepts.`,
    `Input: ${report.input_directory || 'Not available from current report'} · Images: ${report.number_of_images} · Patches: ${report.number_of_patches}.`,
    'Findings are review aids for local execution and require human review before any operational interpretation.',
  ].join('\n\n')
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function average(values: Array<number | null>) {
  const numeric = values.filter((value): value is number => value !== null)
  if (numeric.length === 0) return null
  return numeric.reduce((sum, value) => sum + value, 0) / numeric.length
}

function formatAverage(value: number | null) {
  return value === null ? 'Not available' : value.toFixed(2)
}

function copyText(value?: string | null) {
  if (!value || typeof navigator === 'undefined' || !navigator.clipboard) return
  void navigator.clipboard.writeText(value)
}

function openReportHtml(url?: string | null) {
  if (!url || typeof window === 'undefined') return
  window.open(url, '_blank', 'noopener,noreferrer')
}

function ArtifactRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="grid grid-cols-[90px_1fr] gap-3">
      <dt className="uppercase tracking-[0.12em] text-faint">{label}</dt>
      <dd className="overflow-wrap-anywhere text-foreground">{value || 'Not available'}</dd>
    </div>
  )
}

const advancedEvidenceLabels: Record<string, string> = {
  reference_scoring_summary: 'Optional Reference Scoring Evidence',
  spatial_anomaly_map_summary: 'Optional Spatial Anomaly Maps',
  calibration_summary: 'Optional Fitted Calibration',
  threshold_operating_point_summary: 'Optional Candidate Operating Points',
  benchmark_validation_summary: 'Optional Benchmark Validation Artifact',
}

function AdvancedEvidence({ evidence }: { evidence: Record<string, Record<string, unknown>> }) {
  return (
    <Panel className="p-5">
      <h2 className="text-lg font-semibold text-foreground">Advanced Evidence</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Optional review-prioritization signals from artifacts attached to this report. Requires human review.
      </p>
      <div className="mt-4 grid gap-3">
        {Object.entries(evidence).map(([key, summary]) => (
          <section key={key} className="rounded-md border border-border bg-card p-4">
            <h3 className="text-sm font-medium text-foreground">
              {advancedEvidenceLabels[key] || key}
            </h3>
            <dl className="mt-3 grid gap-2 font-mono text-xs text-muted-foreground">
              <ArtifactRow label="Artifact" value={stringValue(summary.artifact_path)} />
              <ArtifactRow label="Fingerprint" value={stringValue(summary.artifact_fingerprint)} />
              {'calibrated' in summary ? (
                <ArtifactRow label="Calibrated" value={summary.calibrated === true ? 'true' : 'false'} />
              ) : null}
              {'map_count' in summary ? (
                <ArtifactRow label="Maps" value={String(summary.map_count)} />
              ) : null}
              {'operating_point_count' in summary ? (
                <ArtifactRow label="Points" value={String(summary.operating_point_count)} />
              ) : null}
              {'dataset_name' in summary ? (
                <ArtifactRow label="Dataset" value={stringValue(summary.dataset_name)} />
              ) : null}
            </dl>
          </section>
        ))}
      </div>
    </Panel>
  )
}

function stringValue(value: unknown) {
  return typeof value === 'string' && value ? value : undefined
}
