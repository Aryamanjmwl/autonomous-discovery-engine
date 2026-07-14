// Mock fallback data for ADE Studio when the local backend is unavailable.
// Connected mode uses the local ADE engine through NEXT_PUBLIC_ADE_API_URL.

export type ScreenId =
  | 'overview'
  | 'projects'
  | 'new-analysis'
  | 'runs'
  | 'findings'
  | 'reports'
  | 'benchmarks'
  | 'feedback'
  | 'settings'

export type FindingKind = 'anomaly' | 'concept' | 'pattern'
export type ReviewStatus = 'pending' | 'useful' | 'not-useful' | 'needs-review' | 'reviewed'

export interface Project {
  id: string
  name: string
  dataset: string
  runs: number
  findings: number
  lastRun: string
  status: 'active' | 'idle'
}

export interface Finding {
  id: string
  title: string
  kind: FindingKind
  novelty: number
  confidence: number
  deviation: string
  clusterDensity: number
  status: ReviewStatus
  runId: string
  detector: string
  source: string
  firstDetected: string
  impact: string
}

export interface RunRecord {
  id: string
  project: string
  workflow: 'visual' | 'tabular' | 'time-series'
  stage: string
  progress: number
  findings: number
  startedAt: string
  status: 'running' | 'complete' | 'queued'
}

export interface ReportRecord {
  id: string
  title: string
  project: string
  date: string
  runId: string
  findings: number
  critical: number
  noveltyAvg: number
  confidence: number
  reviewed: number
  summary: string
  hash: string
}

export interface FeedbackEntry {
  id: string
  finding: string
  verdict: 'useful' | 'not-useful' | 'needs-review'
  reviewer: string
  note: string
  time: string
}

export interface TimelineEvent {
  id: string
  time: string
  label: string
  detail: string
  tone: 'anomaly' | 'operational' | 'concept' | 'muted'
}

export const projects: Project[] = [
  {
    id: 'mfg-qc',
    name: 'Manufacturing QC Pipeline',
    dataset: 'qc_sensor_2024.parquet',
    runs: 18,
    findings: 42,
    lastRun: '2024-12-08',
    status: 'active',
  },
  {
    id: 'grid-telemetry',
    name: 'Grid Telemetry Monitor',
    dataset: 'grid_stream_q4.parquet',
    runs: 11,
    findings: 27,
    lastRun: '2024-12-05',
    status: 'idle',
  },
  {
    id: 'vibration-lab',
    name: 'Vibration Analysis Lab',
    dataset: 'rotor_vibe_set.parquet',
    runs: 9,
    findings: 15,
    lastRun: '2024-11-28',
    status: 'idle',
  },
  {
    id: 'thermal-bench',
    name: 'Thermal Barrier Benchmark',
    dataset: 'thermal_unit_b.parquet',
    runs: 6,
    findings: 12,
    lastRun: '2024-11-20',
    status: 'idle',
  },
]

export const findings: Finding[] = [
  {
    id: 'f-thermal-7',
    title: 'Thermal Drift Cluster #7',
    kind: 'anomaly',
    novelty: 0.89,
    confidence: 0.91,
    deviation: '3.8σ',
    clusterDensity: 0.18,
    status: 'pending',
    runId: '88721-A',
    detector: 'novelty_v4',
    source: 'sensor_q4.pq',
    firstDetected: '2024-12-08 13:58:44',
    impact:
      'Sustained thermal drift detected in Unit B channels correlates with pre-failure symptoms noted in manual maintenance logs.',
  },
  {
    id: 'f-pressure-z9',
    title: 'Pressure Oscillation Z-9',
    kind: 'anomaly',
    novelty: 0.92,
    confidence: 0.94,
    deviation: '4.2σ',
    clusterDensity: 0.12,
    status: 'needs-review',
    runId: '88721-A',
    detector: 'novelty_v4',
    source: 'sensor_q4.pq',
    firstDetected: '2024-12-08 14:24:01',
    impact:
      'Detected pressure oscillations in sensor series Z-9 correlate with a 3.4% rise in cavitation risk markers within the primary cooling loop.',
  },
  {
    id: 'f-corr-b12',
    title: 'Sensor Correlation B-12',
    kind: 'concept',
    novelty: 0.74,
    confidence: 0.68,
    deviation: '2.1σ',
    clusterDensity: 0.31,
    status: 'reviewed',
    runId: '88721-A',
    detector: 'concept_v2',
    source: 'sensor_q4.pq',
    firstDetected: '2024-12-08 14:02:18',
    impact:
      'Possible latent correlation between thermal and pressure subsystems suggests a shared upstream driver worth manual investigation.',
  },
  {
    id: 'f-voltage-seq',
    title: 'Voltage Spike Sequence',
    kind: 'pattern',
    novelty: 0.81,
    confidence: 0.77,
    deviation: '3.0σ',
    clusterDensity: 0.22,
    status: 'pending',
    runId: '88721-A',
    detector: 'pattern_v3',
    source: 'sensor_q4.pq',
    firstDetected: '2024-12-08 13:41:55',
    impact:
      'Repeating voltage spike pattern observed ahead of thermal excursions; this is a possible pattern precursor that requires human review.',
  },
  {
    id: 'f-freq-gamma',
    title: 'Frequency Shift Gamma',
    kind: 'anomaly',
    novelty: 0.68,
    confidence: 0.72,
    deviation: '2.4σ',
    clusterDensity: 0.27,
    status: 'useful',
    runId: '88721-A',
    detector: 'novelty_v4',
    source: 'sensor_q4.pq',
    firstDetected: '2024-12-08 12:55:07',
    impact:
      'Frequency-domain shift flagged in Unit B rotor channel; overlaps with a known maintenance window.',
  },
  {
    id: 'f-baseline-shift',
    title: 'Baseline Shift Delta',
    kind: 'concept',
    novelty: 0.63,
    confidence: 0.6,
    deviation: '1.9σ',
    clusterDensity: 0.34,
    status: 'pending',
    runId: '88721-A',
    detector: 'concept_v2',
    source: 'sensor_q4.pq',
    firstDetected: '2024-12-08 12:30:41',
    impact:
      'A slow baseline shift concept across b1–b4 channels that may represent normal seasonal recalibration.',
  },
]

export const runs: RunRecord[] = [
  {
    id: 'run_847_q4',
    project: 'Manufacturing QC Pipeline',
    workflow: 'tabular',
    stage: 'Candidate clustering',
    progress: 64,
    findings: 9,
    startedAt: '2024-12-08 14:12',
    status: 'running',
  },
  {
    id: 'run_846_q4',
    project: 'Manufacturing QC Pipeline',
    workflow: 'tabular',
    stage: 'Report generation',
    progress: 100,
    findings: 12,
    startedAt: '2024-12-08 09:20',
    status: 'complete',
  },
  {
    id: 'run_882_grid',
    project: 'Grid Telemetry Monitor',
    workflow: 'time-series',
    stage: 'Queued',
    progress: 0,
    findings: 0,
    startedAt: '2024-12-08 15:02',
    status: 'queued',
  },
  {
    id: 'run_845_vibe',
    project: 'Vibration Analysis Lab',
    workflow: 'visual',
    stage: 'Evidence extraction',
    progress: 100,
    findings: 9,
    startedAt: '2024-12-05 11:44',
    status: 'complete',
  },
]

export const reports: ReportRecord[] = [
  {
    id: 'rpt-4',
    title: 'Candidate Anomaly Report #4',
    project: 'Manufacturing QC Pipeline',
    date: '2024-12-08',
    runId: 'run_847_q4',
    findings: 12,
    critical: 3,
    noveltyAvg: 0.74,
    confidence: 0.68,
    reviewed: 7,
    summary:
      'Primary manufacturing QC pipeline execution was analyzed over a 48-hour window. ADE identified 12 distinct candidate anomalies concentrated in the Unit B thermal subsystem.\n\nStatistical novelty scores across candidate findings suggest a possible sustained drift pattern (avg 4.2σ) which aligns with manual maintenance logs regarding Unit B pre-failure symptoms. Suggested review focus is sensor recalibration context and thermal barrier inspection. All findings require human review before local use.',
    hash: '8a7c2...f822',
  },
  {
    id: 'rpt-3',
    title: 'Quarterly Performance Drift',
    project: 'Manufacturing QC Pipeline',
    date: '2024-12-01',
    runId: 'run_812_q4',
    findings: 48,
    critical: 5,
    noveltyAvg: 0.71,
    confidence: 0.7,
    reviewed: 44,
    summary:
      'Aggregate quarterly review across 4 datasets. Candidate concepts indicate a slow performance drift concentrated in end-of-shift windows. Findings compiled from standard QC pipeline cycles and flagged for maintenance planning.',
    hash: 'c31a9...0b74',
  },
  {
    id: 'rpt-2',
    title: 'Vibration Analysis Review',
    project: 'Vibration Analysis Lab',
    date: '2024-11-20',
    runId: 'run_780_vibe',
    findings: 9,
    critical: 1,
    noveltyAvg: 0.66,
    confidence: 0.73,
    reviewed: 9,
    summary:
      'Visual workflow review of rotor vibration spectra. One possible pattern precursor identified near resonance band; remaining candidates are within the expected local review envelope.',
    hash: 'de55b...41a0',
  },
  {
    id: 'rpt-1',
    title: 'Pressure Baseline Summary',
    project: 'Grid Telemetry Monitor',
    date: '2024-11-12',
    runId: 'run_701_grid',
    findings: 21,
    critical: 2,
    noveltyAvg: 0.69,
    confidence: 0.65,
    reviewed: 18,
    summary:
      'Baseline pressure characterization across grid telemetry streams. Candidate anomalies clustered around load transitions; recommended follow-up on two high-novelty candidates.',
    hash: '7f0e1...9cc3',
  },
]

export const feedbackEntries: FeedbackEntry[] = [
  {
    id: 'fb-1',
    finding: 'Frequency Shift Gamma',
    verdict: 'useful',
    reviewer: 'local.reviewer',
    note: 'Confirmed against maintenance window logs. Retain for trend analysis.',
    time: '2024-12-08 15:10',
  },
  {
    id: 'fb-2',
    finding: 'Pressure Oscillation Z-9',
    verdict: 'needs-review',
    reviewer: 'local.reviewer',
    note: 'High novelty but overlaps sensor recalibration event — escalate to domain engineer.',
    time: '2024-12-08 14:58',
  },
  {
    id: 'fb-3',
    finding: 'Sensor Correlation B-12',
    verdict: 'useful',
    reviewer: 'local.reviewer',
    note: 'Correlation matches known upstream driver. Useful concept.',
    time: '2024-12-08 14:20',
  },
  {
    id: 'fb-4',
    finding: 'Baseline Shift Delta',
    verdict: 'not-useful',
    reviewer: 'local.reviewer',
    note: 'Explained by seasonal recalibration. Not actionable.',
    time: '2024-12-07 18:44',
  },
]

export const timeline: TimelineEvent[] = [
  {
    id: 't-1',
    time: '14:24:01',
    label: 'Candidate found',
    detail: 'Novel thermal drift in unit B-12',
    tone: 'anomaly',
  },
  {
    id: 't-2',
    time: '13:58:12',
    label: 'Run complete',
    detail: 'Standard QC pipeline cycle 882',
    tone: 'operational',
  },
  {
    id: 't-3',
    time: '12:44:56',
    label: 'Report generated',
    detail: 'Candidate anomaly trend review Q4',
    tone: 'concept',
  },
  {
    id: 't-4',
    time: '11:20:03',
    label: 'Manual audit',
    detail: 'Human review of Cluster #4',
    tone: 'muted',
  },
]

export const runLogLines: string[] = [
  '[14:12:02] engine: local workspace initialized',
  '[14:12:03] loader: reading qc_sensor_2024.parquet (847,293 rows / 42 dims)',
  '[14:12:09] validate: null rate 0.3% within tolerance',
  '[14:13:41] detect: novelty_v4 threshold 0.82σ',
  '[14:15:22] cluster: grouping candidate findings',
  '[14:16:05] candidate: thermal drift cluster flagged (N=0.89)',
  '[14:18:30] candidate: pressure oscillation flagged (N=0.92)',
  '[14:19:12] review: 3 candidates require human review',
]

export const validationRows = [
  { name: 'sensor_b1_v', type: 'FLOAT64', valid: 99.7, fill: 62 },
  { name: 'sensor_b2_v', type: 'FLOAT64', valid: 99.7, fill: 48 },
  { name: 'sensor_b3_v', type: 'FLOAT64', valid: 99.7, fill: 74 },
  { name: 'sensor_b4_v', type: 'FLOAT64', valid: 99.7, fill: 40 },
]

export function noveltyToneClass(kind: FindingKind) {
  switch (kind) {
    case 'anomaly':
      return 'anomaly'
    case 'concept':
      return 'concept'
    case 'pattern':
      return 'pattern'
  }
}
