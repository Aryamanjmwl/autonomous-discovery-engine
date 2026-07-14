'use client'

import { TrendingUp, TrendingDown } from 'lucide-react'
import { ScreenHeader } from '@/components/ade/screen-header'
import { Panel, PanelHeader, KpiCard, SectionLabel } from '@/components/ade/primitives'
import type { EngineMode } from '@/lib/ade-api'
import { cn } from '@/lib/utils'

const BENCH_RUNS = [
  { id: 'mock_visual_04', workflow: 'visual', rows: 'demo set', runtime: 'local', precision: 0.847, recall: 0.912 },
  { id: 'mock_visual_03', workflow: 'visual', rows: 'demo set', runtime: 'local', precision: 0.835, recall: 0.908 },
  { id: 'mock_tabular_02', workflow: 'tabular', rows: 'demo csv', runtime: 'local', precision: 0.802, recall: 0.889 },
  { id: 'mock_series_01', workflow: 'time-series', rows: 'demo csv', runtime: 'local', precision: 0.791, recall: 0.874 },
]

const TREND = [0.79, 0.8, 0.802, 0.812, 0.83, 0.835, 0.847]

export function BenchmarksScreen({ engineMode }: { engineMode: EngineMode }) {
  const connected = engineMode === 'connected'
  const max = Math.max(...TREND)
  const min = Math.min(...TREND)

  return (
    <div className="flex flex-col gap-6">
      <ScreenHeader
        eyebrow="Performance"
        title="Benchmarks"
        description={
          connected
            ? 'Benchmark artifacts are shown only when they are available from local ADE outputs.'
            : 'Mock Preview benchmark values are demo-only fallback content.'
        }
      />

      {connected ? (
        <Panel className="p-5">
          <PanelHeader title="Benchmark artifacts" />
          <p className="mt-4 text-sm text-muted-foreground">
            Not available from current report. Run the local benchmark script to generate benchmark artifacts.
          </p>
        </Panel>
      ) : (
        <>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Precision" value="0.847" hint="+1.2% vs prev" hintTone="operational" />
        <KpiCard label="Recall" value="0.912" hint="+0.4% vs prev" hintTone="operational" />
        <KpiCard label="Avg runtime" value="4m 32s" hint="-8s vs prev" hintTone="operational" />
        <KpiCard label="Throughput" value="3.1k" hint="rows/sec" hintTone="anomaly" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Panel className="xl:col-span-2">
          <PanelHeader title="Precision trend · last 7 runs" />
          <div className="ade-grid flex h-64 items-end gap-3 p-4">
            {TREND.map((v, i) => {
              const h = ((v - min) / (max - min || 1)) * 80 + 15
              return (
                <div key={i} className="flex flex-1 flex-col items-center gap-2">
                  <div className="flex w-full flex-1 items-end">
                    <div
                      className={cn('w-full rounded-t-sm', i === TREND.length - 1 ? 'bg-primary' : 'bg-primary/40')}
                      style={{ height: `${h}%` }}
                    />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground">{v.toFixed(2)}</span>
                </div>
              )
            })}
          </div>
        </Panel>

        <Panel className="p-4">
          <SectionLabel>Dataset summary</SectionLabel>
          <div className="mt-3 flex flex-col gap-3">
            <SummaryRow label="Active datasets" value="04" />
            <SummaryRow label="Total size" value="8.4 GB" />
            <SummaryRow label="Total rows" value="3.11M" />
            <SummaryRow label="Avg null rate" value="0.3%" />
            <SummaryRow label="Formats" value="Mock Preview" />
          </div>
        </Panel>
      </div>

      <Panel>
        <PanelHeader title="Benchmark runs" />
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground">
              <th className="px-4 py-2 font-normal">Run</th>
              <th className="px-4 py-2 font-normal">Workflow</th>
              <th className="px-4 py-2 font-normal">Rows</th>
              <th className="px-4 py-2 font-normal">Runtime</th>
              <th className="px-4 py-2 font-normal">Precision</th>
              <th className="px-4 py-2 font-normal">Recall</th>
            </tr>
          </thead>
          <tbody>
            {BENCH_RUNS.map((r, i) => (
              <tr key={r.id} className="border-b border-border last:border-b-0">
                <td className="px-4 py-3 font-mono text-foreground">{r.id}</td>
                <td className="px-4 py-3 font-mono text-xs uppercase tracking-[0.1em] text-muted-foreground">
                  {r.workflow}
                </td>
                <td className="px-4 py-3 font-mono text-muted-foreground">{r.rows}</td>
                <td className="px-4 py-3 font-mono text-muted-foreground">{r.runtime}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex items-center gap-1.5 font-mono text-foreground">
                    {r.precision.toFixed(3)}
                    {i === 0 ? (
                      <TrendingUp className="size-3.5 text-operational" />
                    ) : (
                      <TrendingDown className="size-3.5 text-muted-foreground" />
                    )}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-muted-foreground">{r.recall.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>
        </>
      )}
    </div>
  )
}

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border pb-2 text-sm last:border-b-0 last:pb-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-mono text-foreground">{value}</span>
    </div>
  )
}
