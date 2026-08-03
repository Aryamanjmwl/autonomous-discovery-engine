'use client'

import { useEffect, useState } from 'react'
import { AlertTriangle, FileText, RefreshCw } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, StatusBadge, TechButton } from '@/components/ade/primitives'
import type { ScreenId } from '@/lib/ade-data'
import {
  cancelStudioRun,
  getStudioRun,
  type EngineMode,
  type StudioRunJob,
  type StudioRunStatus,
} from '@/lib/ade-api'
import { cn } from '@/lib/utils'

export function RunsScreen({
  runsFromApi,
  engineMode,
  onNavigate,
  onRefresh,
}: {
  runsFromApi: StudioRunJob[]
  engineMode: EngineMode
  onNavigate: (id: ScreenId) => void
  onRefresh: (reportName?: string) => void
}) {
  const connected = engineMode === 'connected'
  const [selectedId, setSelectedId] = useState(runsFromApi[0]?.job_id ?? '')
  const [detail, setDetail] = useState<StudioRunJob | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const selected = detail?.job_id === selectedId
    ? detail
    : runsFromApi.find((run) => run.job_id === selectedId) ?? runsFromApi[0]

  useEffect(() => {
    if (!selectedId && runsFromApi[0]) setSelectedId(runsFromApi[0].job_id)
  }, [runsFromApi, selectedId])

  useEffect(() => {
    if (!connected || !runsFromApi.some((run) => run.status === 'queued' || run.status === 'running')) {
      return
    }
    const timer = window.setInterval(() => onRefresh(), 2000)
    return () => window.clearInterval(timer)
  }, [connected, onRefresh, runsFromApi])

  async function selectJob(jobId: string) {
    setSelectedId(jobId)
    setDetailError(null)
    try {
      setDetail(await getStudioRun(jobId))
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : 'Unable to load local job detail.')
    }
  }

  async function cancelJob(jobId: string) {
    setCancelling(true)
    setDetailError(null)
    try {
      setDetail(await cancelStudioRun(jobId))
      onRefresh()
    } catch (error) {
      setDetailError(error instanceof Error ? error.message : 'Unable to cancel local job.')
    } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Execution"
        title="Local Run Jobs"
        description="Review durable job state and validated outputs from this local ADE Studio backend."
        actions={
          <TechButton variant="secondary" onClick={onRefresh} disabled={!connected}>
            <RefreshCw className="size-3.5" />
            Refresh jobs and reports
          </TechButton>
        }
      />

      <p className="text-sm text-muted-foreground">
        Run history is stored locally and survives normal backend restarts.
      </p>

      {!connected ? (
        <Panel className="p-5 text-sm text-muted-foreground">
          Connect to the local ADE backend to view Studio run jobs.
        </Panel>
      ) : runsFromApi.length === 0 ? (
        <Panel className="p-5 text-sm text-muted-foreground">
          No Studio runs have been started in this local session.
        </Panel>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,320px)_1fr]">
          <Panel>
            <PanelHeader title={`Jobs (${runsFromApi.length})`} />
            <ul>
              {runsFromApi.map((run) => (
                <li key={run.job_id}>
                  <button
                    type="button"
                    onClick={() => void selectJob(run.job_id)}
                    className={cn(
                      'flex w-full flex-col gap-2 border-b border-border px-4 py-3 text-left transition-colors last:border-b-0',
                      run.job_id === selected?.job_id ? 'bg-primary/10' : 'hover:bg-card',
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="truncate font-mono text-sm text-foreground">
                        {shortJobId(run.job_id)}
                      </span>
                      <RunStatusBadge status={run.status} />
                    </div>
                    <span className="font-mono text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
                      {jobTypeLabel(run.job_type)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </Panel>

          {selected ? (
            <JobDetail
              job={selected}
              cancelling={cancelling}
              onCancel={cancelJob}
              onNavigate={onNavigate}
              onRefresh={onRefresh}
            />
          ) : null}
        </div>
      )}

      {detailError ? (
        <div role="alert" className="rounded-md border border-critical/40 bg-critical/10 p-4 text-sm text-critical">
          {detailError}
        </div>
      ) : null}
    </div>
  )
}

function JobDetail({
  job,
  cancelling,
  onCancel,
  onNavigate,
  onRefresh,
}: {
  job: StudioRunJob
  cancelling: boolean
  onCancel: (jobId: string) => Promise<void>
  onNavigate: (id: ScreenId) => void
  onRefresh: (reportName?: string) => void
}) {
  const reportName = jsonReportName(job.output_report_paths)
  return (
    <div className="flex flex-col gap-6">
      <Panel className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="break-all font-mono text-sm text-foreground">{job.job_id}</p>
            <p className="text-sm text-muted-foreground">{jobTypeLabel(job.job_type)}</p>
          </div>
          <RunStatusBadge status={job.status} />
        </div>
        {job.status === 'queued' || job.status === 'running' ? (
          <TechButton
            variant="secondary"
            className="mt-4"
            disabled={cancelling || job.cancellation_requested}
            onClick={() => void onCancel(job.job_id)}
          >
            {job.cancellation_requested
              ? 'Cancellation requested'
              : cancelling
                ? 'Cancelling…'
                : 'Cancel job'}
          </TechButton>
        ) : null}
        <dl className="mt-5 grid gap-3 font-mono text-xs md:grid-cols-2">
          <RunMeta label="Created" value={formatTime(job.created_at)} />
          <RunMeta label="Started" value={formatTime(job.started_at)} />
          <RunMeta label="Finished" value={formatTime(job.finished_at)} />
          <RunMeta label="Human review" value={job.human_review_required ? 'Required' : 'Not indicated'} />
        </dl>
      </Panel>

      <Panel>
        <PanelHeader title="Input summary" />
        <dl className="grid gap-3 p-4 font-mono text-xs">
          {Object.entries(job.input_summary).map(([key, value]) => (
            <RunMeta key={key} label={key.replaceAll('_', ' ')} value={formatValue(value)} />
          ))}
        </dl>
      </Panel>

      {job.error_message ? (
        <div role="alert" className="flex items-start gap-2 rounded-md border border-critical/40 bg-critical/10 p-4 text-sm text-critical">
          <AlertTriangle className="mt-0.5 size-4 shrink-0" />
          <span>{job.error_message}</span>
        </div>
      ) : null}

      <OutputPanel title="Warnings" values={job.warnings} emptyText="No warnings were recorded for this job." />
      <OutputPanel
        title="Output reports"
        values={job.output_report_paths}
        emptyText="No validated report paths were recorded for this job."
      />
      <OutputPanel
        title="Output artifacts"
        values={job.output_artifact_paths}
        emptyText="No artifact paths were recorded for this job."
      />

      {job.status === 'succeeded' ? (
        <div className="rounded-md border border-operational/40 bg-operational/10 p-4 text-sm text-operational">
          <p>Run completed. Outputs are review-prioritization signals and require human review.</p>
          {!reportName ? (
            <p className="mt-2">Run completed. Open the Reports screen to view generated reports.</p>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2">
            <TechButton
              variant="secondary"
              onClick={() => {
                onRefresh(reportName)
                onNavigate('reports')
              }}
            >
              {reportName ? 'Open in Reports' : 'Open Reports'}
            </TechButton>
            <TechButton variant="secondary" onClick={onRefresh}>
              Refresh report list
            </TechButton>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function OutputPanel({
  title,
  values,
  emptyText,
}: {
  title: string
  values: string[]
  emptyText: string
}) {
  return (
    <Panel>
      <PanelHeader title={title} />
      {values.length ? (
        <ul className="p-4">
          {values.map((value) => (
            <li key={value} className="flex gap-3 border-b border-border py-2 last:border-b-0">
              <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <span className="break-all font-mono text-xs text-foreground">{value}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="p-4 text-sm text-muted-foreground">{emptyText}</p>
      )}
    </Panel>
  )
}

function RunStatusBadge({ status }: { status: StudioRunStatus }) {
  if (status === 'succeeded') return <StatusBadge tone="operational" dot>Succeeded</StatusBadge>
  if (status === 'failed') return <StatusBadge tone="critical" dot>Failed</StatusBadge>
  if (status === 'running') return <StatusBadge tone="anomaly" dot>Running</StatusBadge>
  if (status === 'cancelled') return <StatusBadge tone="muted" dot>Cancelled</StatusBadge>
  return <StatusBadge tone="muted" dot>Queued</StatusBadge>
}

function RunMeta({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid grid-cols-[110px_1fr] gap-3">
      <dt className="uppercase tracking-[0.12em] text-faint">{label}</dt>
      <dd className="break-all text-foreground">{value}</dd>
    </div>
  )
}

function shortJobId(jobId: string) {
  return jobId.length > 22 ? `${jobId.slice(0, 19)}…` : jobId
}

function jobTypeLabel(jobType: StudioRunJob['job_type']) {
  return jobType === 'image_folder_analysis' ? 'Image folder analysis' : 'Temporal analysis'
}

function formatTime(value: string | null) {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'Not provided'
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function jsonReportName(paths: string[]) {
  const jsonPath = paths.find((path) => path.toLowerCase().endsWith('.json'))
  if (!jsonPath) return undefined
  return jsonPath.replaceAll('\\', '/').split('/').pop() || undefined
}
