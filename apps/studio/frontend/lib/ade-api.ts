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

export interface StudioReport {
  name: string
  path: string
  markdown_path?: string | null
  html_path?: string | null
  run_id?: string
  generated_at?: string
  candidate_anomaly_count: number
  candidate_concept_count: number
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
  markdown_report_path?: string | null
  json_report_path?: string | null
  html_report_path?: string | null
  raw_report?: Record<string, unknown>
}

export interface StudioData {
  mode: EngineMode
  health: StudioHealth | null
  summary: StudioSummary | null
  runs: StudioRun[]
  reports: StudioReport[]
  selectedReport: StudioReportDetail | null
  error: string | null
}

const DEFAULT_API_URL = 'http://127.0.0.1:8765'

export function adeApiBaseUrl() {
  return process.env.NEXT_PUBLIC_ADE_API_URL || DEFAULT_API_URL
}

export async function loadStudioData(reportName?: string): Promise<StudioData> {
  try {
    const [health, summary, runs, reports] = await Promise.all([
      request<StudioHealth>('/health'),
      request<StudioSummary>('/api/studio/summary'),
      request<StudioRun[]>('/api/studio/runs'),
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${adeApiBaseUrl()}${path}`, {
    cache: 'no-store',
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
  return (await response.json()) as T
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

