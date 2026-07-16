'use client'

import { useState } from 'react'
import { Folder, Eye, Grid3x3, AudioWaveform, Lock, ChevronDown, FileText, type LucideIcon } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, SectionLabel, TechButton } from '@/components/ade/primitives'
import { projects, type ScreenId } from '@/lib/ade-data'
import { runStudioAnalysis, type EngineMode, type StudioAnalysisResult } from '@/lib/ade-api'
import { cn } from '@/lib/utils'

type Workflow = 'visual' | 'tabular' | 'time-series'

const WORKFLOWS: { id: Workflow; label: string; icon: LucideIcon }[] = [
  { id: 'visual', label: 'Visual', icon: Eye },
  { id: 'tabular', label: 'Tabular', icon: Grid3x3 },
  { id: 'time-series', label: 'Series', icon: AudioWaveform },
]

const ARTIFACTS = [
  { name: 'Markdown report', size: 'Expected artifact' },
  { name: 'JSON report', size: 'Expected artifact' },
  { name: 'HTML report', size: 'Expected artifact' },
  { name: 'Candidate findings', size: 'Requires human review' },
]

export function NewAnalysisScreen({
  activeProject,
  onProjectChange,
  onNavigate,
  engineMode,
  onAnalysisComplete,
}: {
  activeProject: string
  onProjectChange: (name: string) => void
  onNavigate: (id: ScreenId) => void
  engineMode: EngineMode
  onAnalysisComplete: (result: StudioAnalysisResult) => void
}) {
  const [workflow, setWorkflow] = useState<Workflow>('visual')
  const [dataset, setDataset] = useState('data/raw/demo_images')
  const [outputName, setOutputName] = useState('studio_report.md')
  const [result, setResult] = useState<StudioAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const connected = engineMode === 'connected'
  const canRun = connected && workflow === 'visual' && dataset.trim().length > 0 && !isRunning

  async function runAnalysis() {
    if (!canRun) return
    setIsRunning(true)
    setError(null)
    setResult(null)
    try {
      const nextResult = await runStudioAnalysis({
        input_path: dataset.trim(),
        workflow,
        output_name: outputName.trim() || undefined,
      })
      setResult(nextResult)
      onAnalysisComplete(nextResult)
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : 'Local analysis failed.')
    } finally {
      setIsRunning(false)
    }
  }

  function clearForm() {
    setWorkflow('visual')
    setDataset('')
    setOutputName('studio_report.md')
    setResult(null)
    setError(null)
  }

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="New Analysis"
        title="Configure Local Analysis"
        description="Run the local ADE visual/image-folder workflow through the connected engine."
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,380px)_1fr]">
        {/* Config column */}
        <div className="flex flex-col gap-5">
          <div>
            <SectionLabel>{connected ? 'Workspace' : 'Project'}</SectionLabel>
            {connected ? (
              <div className="mt-2 rounded-md border border-border bg-card px-3 py-3 font-mono text-sm text-foreground">
                ADE Local Engine
              </div>
            ) : (
              <div className="relative mt-2">
                <select
                  value={activeProject}
                  onChange={(e) => onProjectChange(e.target.value)}
                  aria-label="Project"
                  className="h-11 w-full appearance-none rounded-md border border-border bg-card px-3 pr-9 font-mono text-sm text-foreground focus:border-primary/50 focus:outline-none"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.name}>
                      {p.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              </div>
            )}
          </div>

          <div>
            <SectionLabel>Local input path</SectionLabel>
            <div className="mt-2 flex items-center gap-3 rounded-md border border-border bg-card p-3">
              <Folder className="size-4 shrink-0 text-muted-foreground" />
              <input
                value={dataset}
                onChange={(e) => setDataset(e.target.value)}
                aria-label="Dataset path"
                className="min-w-0 flex-1 bg-transparent font-mono text-sm text-foreground focus:outline-none"
              />
            </div>
            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Browser upload is not implemented yet. Enter a local folder path that the backend can read.
            </p>
          </div>

          <div>
            <SectionLabel>Output report name</SectionLabel>
            <div className="mt-2 flex items-center gap-3 rounded-md border border-border bg-card p-3">
              <FileText className="size-4 shrink-0 text-muted-foreground" />
              <input
                value={outputName}
                onChange={(e) => setOutputName(e.target.value)}
                aria-label="Output report name"
                className="min-w-0 flex-1 bg-transparent font-mono text-sm text-foreground focus:outline-none"
              />
            </div>
          </div>

          <div>
            <SectionLabel>Adapter workflow</SectionLabel>
            <div className="mt-2 grid grid-cols-3 gap-2">
              {WORKFLOWS.map((w) => {
                const Icon = w.icon
                const active = workflow === w.id
                const enabled = w.id === 'visual'
                return (
                  <button
                    key={w.id}
                    type="button"
                    onClick={() => setWorkflow(w.id)}
                    aria-pressed={active}
                    disabled={!enabled}
                    className={cn(
                      'flex flex-col items-center gap-2 rounded-md border px-2 py-4 transition-colors',
                      active
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-card text-muted-foreground hover:text-foreground',
                      !enabled && 'cursor-not-allowed opacity-55 hover:text-muted-foreground',
                    )}
                  >
                    <Icon className="size-5" />
                    <span className="font-mono text-[11px] uppercase tracking-[0.1em]">{w.label}</span>
                    {!enabled ? (
                      <span className="font-mono text-[9px] uppercase tracking-[0.1em] text-faint">
                        Foundation
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="flex items-start gap-3 rounded-md border border-pattern/40 bg-pattern/10 p-3">
            <Lock className="mt-0.5 size-4 shrink-0 text-pattern" />
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.12em] text-pattern">Local-only execution</p>
              <p className="mt-1 text-xs leading-relaxed text-pattern/90">
                All processing is represented as a local workflow. No data leaves this workspace.
              </p>
            </div>
          </div>

          {!connected ? (
            <div className="rounded-md border border-pattern/40 bg-pattern/10 p-3 text-xs leading-relaxed text-pattern">
              Backend unavailable. Start the local API to run connected analysis.
            </div>
          ) : null}

          {error ? (
            <div className="rounded-md border border-critical/40 bg-critical/10 p-3 text-xs leading-relaxed text-critical">
              {error}
            </div>
          ) : null}

          <TechButton
            variant="primary"
            className="h-11 w-full"
            onClick={runAnalysis}
            disabled={!canRun}
          >
            {isRunning ? 'Running local analysis...' : 'Run local analysis'}
          </TechButton>
          <TechButton variant="secondary" className="h-10 w-full" onClick={clearForm} disabled={isRunning}>
            Clear form
          </TechButton>
          {result ? (
            <div className="rounded-md border border-operational/40 bg-operational/10 p-3 text-xs leading-relaxed text-operational">
              {result.message || 'Local analysis complete.'}
            </div>
          ) : null}

          {result ? (
            <TechButton variant="secondary" className="h-10 w-full" onClick={() => onNavigate('reports')}>
              View generated report
            </TechButton>
          ) : null}
        </div>

        {/* Preview column */}
        <div className="flex flex-col gap-6">
          <Panel>
            <PanelHeader title="Dataset validation preview" />
            <div className="p-4">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <PreviewStat label="Input type" value={workflow === 'visual' ? 'Image folder' : 'Foundation'} />
                <PreviewStat label="Path" value={dataset.trim() || 'Not available from current report'} />
                <PreviewStat label="Workflow" value={workflow} />
                <PreviewStat
                  label="Run status"
                  value={connected && workflow === 'visual' ? 'Ready locally' : 'Not available'}
                />
              </div>
              <div className="mt-4 rounded-md border border-border bg-card p-4">
                <SectionLabel>Expected artifacts</SectionLabel>
                <div className="mt-3 grid gap-2 text-sm text-muted-foreground">
                  <div>Markdown report</div>
                  <div>JSON report</div>
                  <div>HTML report</div>
                  <div>Candidate findings requiring human review</div>
                </div>
              </div>
              {result ? (
                <div className="mt-4 rounded-md border border-operational/40 bg-operational/10 p-4">
                  <p className="font-mono text-xs uppercase tracking-[0.12em] text-operational">
                    Local analysis complete.
                  </p>
                  <div className="mt-3 grid gap-2 font-mono text-xs text-foreground">
                    <ResultRow label="Run ID" value={result.run_id} />
                    <ResultRow label="Input" value={result.input_path} />
                    <ResultRow label="Images" value={String(result.number_of_images ?? 'Not available')} />
                    <ResultRow label="Patches" value={String(result.number_of_patches ?? 'Not available')} />
                    <ResultRow label="Markdown" value={result.markdown_report_path} />
                    <ResultRow label="JSON" value={result.json_report_path} />
                    <ResultRow label="HTML" value={result.html_report_path} />
                    <ResultRow
                      label="Candidates"
                      value={`${result.candidate_anomaly_count} anomalies · ${result.candidate_concept_count} concepts`}
                    />
                    <ResultRow
                      label="Human review"
                      value={result.human_review_required ? 'Required' : 'Not available from current report'}
                    />
                  </div>
                </div>
              ) : null}
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Expected output artifacts" />
            <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-2">
              {(result ? resultArtifacts(result) : ARTIFACTS).map((a) => (
                <div key={a.name} className="flex items-center gap-3 rounded-md border border-border bg-card p-4">
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{a.name}</p>
                    <p className="font-mono text-xs text-muted-foreground">{a.size}</p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
      </div>
    </div>
  )
}

function resultArtifacts(result: StudioAnalysisResult) {
  return [
    { name: 'Markdown report', size: result.markdown_report_path },
    { name: 'JSON report', size: result.json_report_path },
    { name: 'HTML report', size: result.html_report_path || 'HTML export unavailable' },
    {
      name: 'Candidate findings',
      size: `${result.candidate_anomaly_count} anomalies · ${result.candidate_concept_count} concepts`,
    },
  ]
}

function PreviewStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-card p-3">
      <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">{label}</p>
      <p className="mt-1 font-mono text-xl text-foreground">{value}</p>
    </div>
  )
}

function ResultRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="grid grid-cols-[100px_1fr] gap-3">
      <span className="uppercase tracking-[0.12em] text-muted-foreground">{label}</span>
      <span className="break-all">{value || 'Not available from current report'}</span>
    </div>
  )
}
