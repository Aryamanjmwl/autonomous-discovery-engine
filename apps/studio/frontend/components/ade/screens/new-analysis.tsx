'use client'

import { useState } from 'react'
import { FileClock, Folder, Lock, Settings2 } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, SectionLabel, TechButton } from '@/components/ade/primitives'
import type { ScreenId } from '@/lib/ade-data'
import {
  createImageFolderRun,
  createTemporalRun,
  type EngineMode,
  type StudioRunJob,
} from '@/lib/ade-api'

type SubmitKind = 'image' | 'temporal' | null
type TemporalStrategy = 'adjacent_difference' | 'baseline_difference'

export function NewAnalysisScreen({
  onNavigate,
  engineMode,
  onRunComplete,
}: {
  onNavigate: (id: ScreenId) => void
  engineMode: EngineMode
  onRunComplete: (job: StudioRunJob) => void
}) {
  const connected = engineMode === 'connected'
  const [imagePath, setImagePath] = useState('')
  const [imageLabel, setImageLabel] = useState('')
  const [configPath, setConfigPath] = useState('')
  const [manifestPath, setManifestPath] = useState('')
  const [temporalLabel, setTemporalLabel] = useState('')
  const [strategy, setStrategy] = useState<TemporalStrategy>('adjacent_difference')
  const [patchSize, setPatchSize] = useState('')
  const [submitting, setSubmitting] = useState<SubmitKind>(null)
  const [job, setJob] = useState<StudioRunJob | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function submitImageRun() {
    if (!connected || !imagePath.trim() || submitting) return
    setSubmitting('image')
    setError(null)
    setJob(null)
    try {
      const nextJob = await createImageFolderRun({
        input_path: imagePath.trim(),
        config_path: configPath.trim() || undefined,
        run_label: imageLabel.trim() || undefined,
      })
      finish(nextJob)
    } catch (nextError) {
      setError(errorMessage(nextError, 'Image-folder local run failed.'))
    } finally {
      setSubmitting(null)
    }
  }

  async function submitTemporalRun() {
    if (!connected || !manifestPath.trim() || submitting) return
    setSubmitting('temporal')
    setError(null)
    setJob(null)
    const parsedPatchSize = patchSize.trim() ? Number(patchSize) : undefined
    if (parsedPatchSize !== undefined && (!Number.isInteger(parsedPatchSize) || parsedPatchSize < 1)) {
      setError('Patch size must be a positive whole number.')
      setSubmitting(null)
      return
    }
    try {
      const nextJob = await createTemporalRun({
        manifest_path: manifestPath.trim(),
        strategy,
        run_label: temporalLabel.trim() || undefined,
        patch_size: parsedPatchSize,
      })
      finish(nextJob)
    } catch (nextError) {
      setError(errorMessage(nextError, 'Temporal local run failed.'))
    } finally {
      setSubmitting(null)
    }
  }

  function finish(nextJob: StudioRunJob) {
    setJob(nextJob)
    onRunComplete(nextJob)
    if (nextJob.status === 'failed') {
      setError(nextJob.error_message || 'The local run failed without an error message.')
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Run"
        title="Start a Local Run"
        description="Start image-folder or temporal analysis through the local ADE Studio backend."
      />

      <div className="flex items-start gap-3 rounded-md border border-pattern/40 bg-pattern/10 p-4">
        <Lock className="mt-0.5 size-4 shrink-0 text-pattern" />
        <div className="text-sm leading-relaxed text-pattern">
          <p className="font-mono text-xs uppercase tracking-[0.12em]">Local workspace only</p>
          <p className="mt-1">
            Enter paths that already exist on the machine running the ADE Studio backend.
            Browser upload and server filesystem browsing are not available in this Technical Preview.
          </p>
        </div>
      </div>

      {!connected ? (
        <div className="rounded-md border border-critical/40 bg-critical/10 p-4 text-sm text-critical">
          The local ADE backend is unavailable. Start it before submitting a local run.
        </div>
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <RunFormPanel title="Image folder analysis">
          <PathField
            label="Local image folder path"
            value={imagePath}
            onChange={setImagePath}
            placeholder="data/raw/demo_images"
            icon="folder"
          />
          <TextField label="Optional run label" value={imageLabel} onChange={setImageLabel} />
          <PathField
            label="Optional config path"
            value={configPath}
            onChange={setConfigPath}
            placeholder="configs/default.yaml"
            icon="settings"
          />
          <TechButton
            variant="primary"
            className="w-full"
            onClick={() => void submitImageRun()}
            disabled={!connected || !imagePath.trim() || submitting !== null}
          >
            {submitting === 'image' ? 'Submitting local run…' : 'Run image-folder analysis'}
          </TechButton>
        </RunFormPanel>

        <RunFormPanel title="Temporal analysis">
          <PathField
            label="Local temporal manifest path"
            value={manifestPath}
            onChange={setManifestPath}
            placeholder="data/raw/temporal_demo/scene/manifest.json"
            icon="manifest"
          />
          <div>
            <SectionLabel>Strategy</SectionLabel>
            <select
              value={strategy}
              onChange={(event) => setStrategy(event.target.value as TemporalStrategy)}
              aria-label="Temporal strategy"
              className="mt-2 h-11 w-full rounded-md border border-border bg-card px-3 font-mono text-sm text-foreground focus:border-primary/50 focus:outline-none"
            >
              <option value="adjacent_difference">adjacent_difference</option>
              <option value="baseline_difference">baseline_difference</option>
            </select>
          </div>
          <TextField label="Optional run label" value={temporalLabel} onChange={setTemporalLabel} />
          <TextField
            label="Optional patch size"
            value={patchSize}
            onChange={setPatchSize}
            inputMode="numeric"
          />
          <TechButton
            variant="primary"
            className="w-full"
            onClick={() => void submitTemporalRun()}
            disabled={!connected || !manifestPath.trim() || submitting !== null}
          >
            {submitting === 'temporal' ? 'Submitting local run…' : 'Run temporal analysis'}
          </TechButton>
        </RunFormPanel>
      </div>

      {error ? (
        <div role="alert" className="rounded-md border border-critical/40 bg-critical/10 p-4 text-sm text-critical">
          {error}
        </div>
      ) : null}

      {job && job.status === 'succeeded' ? (
        <div className="rounded-md border border-operational/40 bg-operational/10 p-4 text-sm text-operational">
          <p>Local run completed. Generated outputs remain candidate findings and require human review.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <TechButton variant="secondary" onClick={() => onNavigate('reports')}>
              Open Reports
            </TechButton>
            <TechButton variant="secondary" onClick={() => onNavigate('runs')}>
              View job details
            </TechButton>
          </div>
        </div>
      ) : null}
    </div>
  )
}

function RunFormPanel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Panel>
      <PanelHeader title={title} />
      <div className="flex flex-col gap-5 p-5">{children}</div>
    </Panel>
  )
}

function PathField({
  label,
  value,
  onChange,
  placeholder,
  icon,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder: string
  icon: 'folder' | 'settings' | 'manifest'
}) {
  const Icon = icon === 'folder' ? Folder : icon === 'settings' ? Settings2 : FileClock
  return (
    <div>
      <SectionLabel>{label}</SectionLabel>
      <div className="mt-2 flex items-center gap-3 rounded-md border border-border bg-card p-3">
        <Icon className="size-4 shrink-0 text-muted-foreground" />
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder={placeholder}
          aria-label={label}
          className="min-w-0 flex-1 bg-transparent font-mono text-sm text-foreground placeholder:text-faint focus:outline-none"
        />
      </div>
    </div>
  )
}

function TextField({
  label,
  value,
  onChange,
  inputMode,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  inputMode?: 'numeric'
}) {
  return (
    <div>
      <SectionLabel>{label}</SectionLabel>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        inputMode={inputMode}
        aria-label={label}
        className="mt-2 h-11 w-full rounded-md border border-border bg-card px-3 font-mono text-sm text-foreground focus:border-primary/50 focus:outline-none"
      />
    </div>
  )
}

function errorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback
}
