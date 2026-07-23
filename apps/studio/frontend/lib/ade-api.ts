export type EngineMode = 'connected' | 'mock'

export interface StudioHealth {
  status: string
  engine: string
  version: string
  mode: string
  label: string
  supported_workflows: string[]
  human_review_required: boolean
}

export interface StudioSummary {
  mode: string
  label: string
  reports_dir: string
  run_index_path: string
  dashboard_dir: string
  feedback_path: string
  run_count: number
  report_count: number
  temporal_report_count?: number
  latest_temporal_report?: StudioReport | null
  temporal_report_warnings?: string[]
  feedback_count: number
  latest_run: StudioRun | null
  latest_report: StudioReport | null
  latest_run_id?: string | null
  latest_report_name?: string | null
  latest_report_json_path?: string | null
  latest_report_html_path?: string | null
  candidate_anomaly_count?: number
  candidate_concept_count?: number
  input_type?: string | null
  input_directory?: string | null
  number_of_images?: number
  number_of_patches?: number
  advanced_evidence_available?: Record<string, boolean>
  human_review_required: boolean
  no_cloud_upload: boolean
}

export interface StudioRun {
  run_id?: string
  generated_at?: string
  input_path?: string
  markdown_report_path?: string
  json_report_path?: string
  number_of_candidate_anomalies?: number
  number_of_candidate_unknown_concepts?: number
  human_review_required?: boolean
  modality?: string
}

export type StudioRunStatus = 'queued' | 'running' | 'succeeded' | 'failed'
export type StudioRunJobType = 'image_folder_analysis' | 'temporal_analysis'

export interface StudioRunJob {
  job_id: string
  job_type: StudioRunJobType
  status: StudioRunStatus
  created_at: string
  started_at: string | null
  finished_at: string | null
  input_summary: Record<string, unknown>
  output_report_paths: string[]
  output_artifact_paths: string[]
  error_message: string | null
  warnings: string[]
  human_review_required: boolean
}

export interface ImageFolderRunRequest {
  input_path: string
  output_name?: string
  config_path?: string
  run_label?: string
}

export interface TemporalRunRequest {
  manifest_path: string
  output_name?: string
  strategy: 'adjacent_difference' | 'baseline_difference'
  run_label?: string
  patch_size?: number
  top_k?: number
  patch_top_k?: number
}

export interface StudioRunErrorResponse {
  detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>
}

export interface StudioReport {
  name: string
  path: string
  markdown_path?: string | null
  html_path?: string | null
  run_id?: string
  generated_at?: string
  candidate_anomaly_count: number
  candidate_concept_count: number
  candidate_event_count?: number
  type?: 'standard' | 'temporal'
  sequence_id?: string | null
  dataset_name?: string | null
  observation_count?: number | null
  human_review_required: boolean
  modality?: string
}

export interface StudioAnalysisResult {
  status?: string
  message?: string
  run_id?: string
  workflow: 'visual'
  input_path: string
  number_of_images?: number
  number_of_patches?: number
  markdown_report_path: string
  json_report_path: string
  html_report_path?: string | null
  candidate_anomaly_count: number
  candidate_concept_count: number
  human_review_required: boolean
  validated: boolean
}

export interface StudioCandidateAnomaly {
  anomaly_id?: string | null
  source_image_path?: string | null
  coordinates?: number[] | null
  patch_scale?: string | number | null
  novelty_score?: number | null
  evidence_note?: string | null
  score_breakdown?: Record<string, unknown> | null
  largest_feature_deviations?: Array<Record<string, unknown>> | null
  preview_asset_path?: string | null
  preview_asset_name?: string | null
}

export interface StudioReportDetail {
  report_name: string
  report_type?: 'standard' | 'temporal'
  run_id?: string | null
  generated_at?: string | null
  input_directory?: string | null
  input_type?: string | null
  number_of_images: number
  number_of_patches: number
  candidate_anomaly_count: number
  candidate_concept_count: number
  novelty_strategy?: string | null
  human_review_required: boolean
  candidate_anomalies: StudioCandidateAnomaly[]
  candidate_concepts: Array<Record<string, unknown>>
  candidate_event_count?: number
  candidate_temporal_change_events?: StudioTemporalChangeEvent[]
  temporal_sequence_summary?: StudioTemporalSequenceSummary
  temporal_artifact_provenance?: StudioTemporalArtifactProvenance
  temporal_warnings?: string[]
  temporal_limitations?: string[]
  advanced_evidence?: Record<string, Record<string, unknown>>
  advanced_evidence_available?: Record<string, boolean>
  markdown_report_path?: string | null
  json_report_path?: string | null
  html_report_path?: string | null
  raw_report?: Record<string, unknown>
}

export interface StudioTemporalSequenceSummary {
  sequence_id?: string
  dataset_name?: string
  dataset_version?: string
  scene_id?: string | null
  entity_id?: string | null
  observation_count?: number
  ordering_mode?: string
  range_start?: string
  range_end?: string
  strategy?: string
  max_change_score?: number
  mean_adjacent_change_score?: number
  strongest_observation_pair?: string[]
}

export interface StudioTemporalArtifactProvenance {
  artifact_path?: string
  artifact_fingerprint?: string
  manifest_fingerprint?: string
  feature_backend?: string
}

export interface StudioTemporalPatchEvidence {
  source_observation_id?: string
  target_observation_id?: string
  x?: number
  y?: number
  width?: number
  height?: number
  patch_scale?: string
  change_score?: number
  evidence_note?: string
}

export interface StudioTemporalChangeEvent {
  event_id?: string
  rank?: number
  candidate_label?: string
  possible_interpretation?: string
  source_observation_id?: string
  target_observation_id?: string
  change_score?: number
  requires_human_review?: boolean
  patch_evidence?: StudioTemporalPatchEvidence[]
}

export interface StudioData {
  mode: EngineMode
  health: StudioHealth | null
  summary: StudioSummary | null
  runs: StudioRunJob[]
  reports: StudioReport[]
  selectedReport: StudioReportDetail | null
  error: string | null
}

const DEFAULT_API_URL = 'http://127.0.0.1:8765'
const REQUEST_TIMEOUT_MS = 15_000
const RUN_REQUEST_TIMEOUT_MS = 30 * 60_000

export function adeApiBaseUrl(): string {
  const configured = (process.env.NEXT_PUBLIC_ADE_API_URL || DEFAULT_API_URL).trim()
  let url: URL
  try {
    url = new URL(configured)
  } catch {
    throw new Error('NEXT_PUBLIC_ADE_API_URL must be a valid absolute URL.')
  }
  if (!['127.0.0.1', 'localhost', '::1'].includes(url.hostname)) {
    throw new Error('ADE Studio only connects to a localhost backend in this Technical Preview.')
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error('NEXT_PUBLIC_ADE_API_URL must use HTTP or HTTPS.')
  }
  return url.toString().replace(/\/$/, '')
}

export async function loadStudioData(reportName?: string): Promise<StudioData> {
  try {
    const [health, summary, runs, reports] = await Promise.all([
      request<StudioHealth>('/health'),
      request<StudioSummary>('/api/studio/summary'),
      listStudioRuns(),
      request<StudioReport[]>('/api/studio/reports'),
    ])
    const selectedName = reportName || reports[0]?.name
    const selectedReport = selectedName
      ? await request<StudioReportDetail>(`/api/studio/reports/${encodeURIComponent(selectedName)}`)
      : null
    return {
      mode: 'connected',
      health,
      summary,
      runs,
      reports,
      selectedReport,
      error: null,
    }
  } catch (error) {
    return {
      mode: 'mock',
      health: null,
      summary: null,
      runs: [],
      reports: [],
      selectedReport: null,
      error: error instanceof Error ? error.message : 'ADE Studio backend unavailable.',
    }
  }
}

export async function createImageFolderRun(
  payload: ImageFolderRunRequest,
): Promise<StudioRunJob> {
  return request<StudioRunJob>(
    '/api/studio/runs/image-folder',
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    },
    RUN_REQUEST_TIMEOUT_MS,
  )
}

export async function createTemporalRun(payload: TemporalRunRequest): Promise<StudioRunJob> {
  return request<StudioRunJob>(
    '/api/studio/runs/temporal',
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(payload),
    },
    RUN_REQUEST_TIMEOUT_MS,
  )
}

export async function listStudioRuns(): Promise<StudioRunJob[]> {
  return request<StudioRunJob[]>('/api/studio/runs')
}

export async function getStudioRun(jobId: string): Promise<StudioRunJob> {
  return request<StudioRunJob>(`/api/studio/runs/${encodeURIComponent(jobId)}`)
}

export async function runStudioAnalysis(payload: {
  input_path: string
  workflow: 'visual' | 'tabular' | 'time-series'
  output_name?: string
}): Promise<StudioAnalysisResult> {
  return request<StudioAnalysisResult>('/api/studio/analysis', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function reportAssetUrl(assetName?: string | null): string | null {
  if (!assetName) return null
  return `${adeApiBaseUrl()}/api/studio/report-assets/${encodeURIComponent(assetName)}`
}

export function reportHtmlUrl(reportName?: string | null): string | null {
  if (!reportName) return null
  return `${adeApiBaseUrl()}/api/studio/reports/${encodeURIComponent(reportName)}/html`
}

async function request<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const timeout = AbortSignal.timeout(timeoutMs)
  const response = await fetch(`${adeApiBaseUrl()}${path}`, {
    cache: 'no-store',
    signal: timeout,
    ...init,
  })
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      detail = formatApiErrorDetail(body, detail)
    } catch {
      // Keep HTTP status when the backend did not return JSON.
    }
    throw new Error(detail)
  }
  try {
    return (await response.json()) as T
  } catch {
    throw new Error(`ADE Studio backend returned invalid JSON for ${path}.`)
  }
}

function formatApiErrorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== 'object') {
    return fallback
  }
  const detail = (body as { detail?: unknown }).detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (item && typeof item === 'object') {
        const record = item as { loc?: unknown; msg?: unknown; message?: unknown }
        const location = Array.isArray(record.loc) ? record.loc.join('.') : undefined
        const message = typeof record.msg === 'string'
          ? record.msg
          : typeof record.message === 'string'
            ? record.message
            : JSON.stringify(item)
        return location ? `${location}: ${message}` : message
      }
      return String(item)
    })
    return messages.filter(Boolean).join('; ') || fallback
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string') {
      return message
    }
    return JSON.stringify(detail)
  }
  return fallback
}

