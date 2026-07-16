'use client'

import { useState } from 'react'
import { ThumbsUp, ThumbsDown, Eye, Check } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, KpiCard, StatusBadge, TechButton } from '@/components/ade/primitives'
import { feedbackEntries, type FeedbackEntry } from '@/lib/ade-data'
import type { StudioData } from '@/lib/ade-api'

export function FeedbackScreen({ studioData }: { studioData: StudioData }) {
  const [note, setNote] = useState('')
  const [recorded, setRecorded] = useState(false)
  const connected = studioData.mode === 'connected'

  const usefulCount = feedbackEntries.filter((f) => f.verdict === 'useful').length
  const notUsefulCount = feedbackEntries.filter((f) => f.verdict === 'not-useful').length
  const needsReviewCount = feedbackEntries.filter((f) => f.verdict === 'needs-review').length

  const submit = () => {
    setRecorded(true)
    setNote('')
    window.setTimeout(() => setRecorded(false), 2500)
  }

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Human-in-the-loop"
        title="Feedback"
        description="Inspect local feedback support. Candidate findings require human review and nothing is uploaded."
      />

      {connected ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <KpiCard
              label="Feedback records"
              value={studioData.summary?.feedback_count ?? 0}
              hint="Local JSONL store"
              hintTone="operational"
            />
            <KpiCard
              label="Store"
              value="Local"
              hint={studioData.summary?.feedback_path || 'Not available from current report'}
              hintTone="pattern"
            />
            <KpiCard
              label="Review"
              value="Required"
              hint="Human review"
              hintTone="pattern"
            />
          </div>
          <Panel className="p-5">
            <PanelHeader title="Feedback workflow" />
            <p className="mt-4 text-sm text-muted-foreground">
              Studio feedback editing is not implemented in this Technical Preview. The local JSONL
              store remains the source for reviewer labels, and detailed entries should be reviewed
              with the ADE CLI until the Studio backend exposes a dedicated feedback endpoint.
            </p>
          </Panel>
        </>
      ) : (
      <>
      <div className="grid grid-cols-3 gap-4">
        <KpiCard label="Useful" value={usefulCount} hint="Confirmed findings" hintTone="operational" />
        <KpiCard label="Not useful" value={notUsefulCount} hint="Dismissed" hintTone="critical" />
        <KpiCard label="Needs review" value={needsReviewCount} hint="Escalated" hintTone="pattern" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_minmax(0,340px)]">
        <Panel>
          <PanelHeader title="Feedback history" />
          <ul>
            {feedbackEntries.map((entry) => (
              <li key={entry.id} className="border-b border-border p-4 last:border-b-0">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-foreground">{entry.finding}</span>
                  <VerdictBadge verdict={entry.verdict} />
                </div>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{entry.note}</p>
                <div className="mt-2 flex items-center gap-3 font-mono text-[11px] text-muted-foreground">
                  <span>{entry.reviewer}</span>
                  <span>·</span>
                  <span>{entry.time}</span>
                </div>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel className="flex h-fit flex-col p-4">
          <PanelHeader title="Record feedback" className="-mx-4 -mt-4 mb-4 px-4" />
          <p className="text-sm text-muted-foreground">
            Selected finding: <span className="text-foreground">Pressure Oscillation Z-9</span>
          </p>

          <div className="mt-3 flex gap-2">
            <TechButton variant="secondary" className="flex-1 border-operational/50 text-operational">
              <ThumbsUp className="size-3.5" /> Useful
            </TechButton>
            <TechButton variant="secondary" className="flex-1">
              <ThumbsDown className="size-3.5" /> No
            </TechButton>
            <TechButton variant="secondary" className="flex-1">
              <Eye className="size-3.5" /> Review
            </TechButton>
          </div>

          <label htmlFor="fb-note" className="mt-4 font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
            Reviewer note
          </label>
          <textarea
            id="fb-note"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            placeholder="Add validation context for this candidate finding..."
            className="mt-2 w-full resize-none rounded-md border border-border bg-card p-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary/50 focus:outline-none"
          />

          <TechButton variant="primary" className="mt-3 w-full" onClick={submit}>
            {recorded ? (
              <>
                <Check className="size-3.5" /> Feedback recorded
              </>
            ) : (
              'Submit feedback'
            )}
          </TechButton>

          {recorded ? (
            <p className="mt-2 text-center font-mono text-[11px] text-operational">
              Feedback recorded locally.
            </p>
          ) : null}
        </Panel>
      </div>
      </>
      )}
    </div>
  )
}

function VerdictBadge({ verdict }: { verdict: FeedbackEntry['verdict'] }) {
  const map = {
    useful: { tone: 'operational' as const, label: 'Useful' },
    'not-useful': { tone: 'critical' as const, label: 'Not useful' },
    'needs-review': { tone: 'pattern' as const, label: 'Needs review' },
  }
  const cfg = map[verdict]
  return <StatusBadge tone={cfg.tone}>{cfg.label}</StatusBadge>
}
