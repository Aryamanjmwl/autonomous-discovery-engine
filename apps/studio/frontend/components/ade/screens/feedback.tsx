'use client'

import { ScreenHeader } from '@/components/ade/screen-header'
import { KpiCard, Panel, PanelHeader, TechButton } from '@/components/ade/primitives'
import type { StudioData } from '@/lib/ade-api'
import type { ScreenId } from '@/lib/ade-data'

export function FeedbackScreen({
  studioData,
  onNavigate,
}: {
  studioData: StudioData
  onNavigate: (id: ScreenId) => void
}) {
  const connected = studioData.mode === 'connected'

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Local review"
        title="Feedback"
        description="Review local feedback storage without treating candidate findings as scientifically confirmed."
      />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KpiCard
          label="Feedback records"
          value={connected ? studioData.summary?.feedback_count ?? 0 : 'Unavailable'}
          hint={connected ? 'Local JSONL store' : 'Local backend disconnected'}
          hintTone={connected ? 'operational' : 'pattern'}
        />
        <KpiCard
          label="Store"
          value={connected ? 'Local' : 'Unavailable'}
          hint={studioData.summary?.feedback_path || 'Connect to inspect the configured path'}
          hintTone="pattern"
        />
        <KpiCard
          label="Review"
          value="Required"
          hint="Candidate findings require human review"
          hintTone="pattern"
        />
      </div>

      <Panel className="p-5">
        <PanelHeader title="Local reviewer workflow" />
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
          Open a candidate anomaly, candidate concept, or candidate temporal change on the
          Findings screen to mark it useful, not useful, or needing review. Saved actions append
          to the existing local feedback JSONL store.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Feedback is review-oriented state. It does not scientifically confirm a finding and is
          not a replacement for human interpretation.
        </p>
        <TechButton
          variant="primary"
          className="mt-4"
          onClick={() => onNavigate('findings')}
          disabled={!connected}
        >
          Review candidate findings
        </TechButton>
      </Panel>
    </div>
  )
}
