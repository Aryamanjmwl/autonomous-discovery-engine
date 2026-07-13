import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

/* ------------------------------------------------------------------ */
/* Panel — machined surface with hairline border + inset highlight     */
/* ------------------------------------------------------------------ */

export function Panel({
  children,
  className,
  as: Tag = 'section',
  flush = false,
}: {
  children: ReactNode
  className?: string
  as?: 'section' | 'div' | 'aside'
  /** removes the elevation shadow for nested/inner panels */
  flush?: boolean
}) {
  return (
    <Tag
      className={cn(
        'rounded-md border border-border bg-panel',
        !flush && 'ade-panel',
        className,
      )}
    >
      {children}
    </Tag>
  )
}

export function PanelHeader({
  title,
  action,
  className,
  accent,
}: {
  title: string
  action?: ReactNode
  className?: string
  accent?: Tone
}) {
  return (
    <div
      className={cn(
        'flex items-center justify-between border-b border-border px-4 py-2.5',
        className,
      )}
    >
      <div className="flex items-center gap-2.5">
        <span
          className={cn(
            'h-3 w-px',
            accent ? dotStyles[accent] : 'bg-border-strong',
          )}
          aria-hidden
        />
        <h2 className="font-mono text-[11px] uppercase tracking-[0.16em] text-faint">
          {title}
        </h2>
      </div>
      {action}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Section label                                                       */
/* ------------------------------------------------------------------ */

export function SectionLabel({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <p
      className={cn(
        'font-mono text-[11px] uppercase tracking-[0.16em] text-faint',
        className,
      )}
    >
      {children}
    </p>
  )
}

/* ------------------------------------------------------------------ */
/* Readout — instrument-style label / value                            */
/* ------------------------------------------------------------------ */

export function Readout({
  label,
  value,
  hint,
  hintTone = 'muted',
  className,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  hintTone?: 'muted' | 'anomaly' | 'operational' | 'critical' | 'pattern' | 'concept'
  className?: string
}) {
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">
        {label}
      </span>
      <span className="font-mono text-2xl leading-none tabular-nums text-foreground">
        {value}
      </span>
      {hint ? <span className={cn('font-mono text-[11px]', hintTones[hintTone])}>{hint}</span> : null}
    </div>
  )
}

const hintTones: Record<string, string> = {
  muted: 'text-muted-foreground',
  anomaly: 'text-anomaly',
  operational: 'text-operational',
  critical: 'text-critical',
  pattern: 'text-pattern',
  concept: 'text-concept',
}

/* ------------------------------------------------------------------ */
/* KPI card — flat instrument tile with a left accent rule             */
/* ------------------------------------------------------------------ */

export function KpiCard({
  label,
  value,
  hint,
  hintTone = 'muted',
  accent,
  className,
}: {
  label: string
  value: ReactNode
  hint?: ReactNode
  hintTone?: 'muted' | 'anomaly' | 'operational' | 'critical' | 'pattern' | 'concept'
  accent?: Tone
  className?: string
}) {
  return (
    <div
      className={cn(
        'ade-panel relative overflow-hidden rounded-md border border-border bg-panel px-4 py-3.5',
        className,
      )}
    >
      {accent ? (
        <span className={cn('absolute inset-y-0 left-0 w-0.5', dotStyles[accent])} aria-hidden />
      ) : null}
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-faint">{label}</p>
      <p className="mt-2 font-mono text-[28px] leading-none tabular-nums text-foreground">{value}</p>
      {hint ? <p className={cn('mt-2 font-mono text-[11px]', hintTones[hintTone])}>{hint}</p> : null}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Status badge                                                        */
/* ------------------------------------------------------------------ */

type Tone = 'anomaly' | 'concept' | 'pattern' | 'operational' | 'critical' | 'muted'

const toneStyles: Record<Tone, string> = {
  anomaly: 'border-anomaly/40 text-anomaly bg-anomaly/5',
  concept: 'border-concept/40 text-concept bg-concept/5',
  pattern: 'border-pattern/40 text-pattern bg-pattern/5',
  operational: 'border-operational/40 text-operational bg-operational/5',
  critical: 'border-critical/50 text-critical bg-critical/5',
  muted: 'border-border-strong text-muted-foreground bg-transparent',
}

const dotStyles: Record<Tone, string> = {
  anomaly: 'bg-anomaly',
  concept: 'bg-concept',
  pattern: 'bg-pattern',
  operational: 'bg-operational',
  critical: 'bg-critical',
  muted: 'bg-muted-foreground',
}

export function StatusBadge({
  children,
  tone = 'muted',
  dot = false,
  className,
}: {
  children: ReactNode
  tone?: Tone
  dot?: boolean
  className?: string
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[3px] border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.13em]',
        toneStyles[tone],
        className,
      )}
    >
      {dot ? <span className={cn('size-1.5 rounded-full', dotStyles[tone])} /> : null}
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* Technical button                                                    */
/* ------------------------------------------------------------------ */

export function TechButton({
  children,
  onClick,
  variant = 'secondary',
  active = false,
  className,
  type = 'button',
  disabled,
  'aria-pressed': ariaPressed,
}: {
  children: ReactNode
  onClick?: () => void
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  active?: boolean
  className?: string
  type?: 'button' | 'submit'
  disabled?: boolean
  'aria-pressed'?: boolean
}) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-[4px] px-3 py-2 font-mono text-[11px] uppercase tracking-[0.12em] transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-40 disabled:pointer-events-none'

  const variants = {
    // outlined cyan — a signal accent, not an oversized bright block
    primary: 'border border-primary/55 bg-primary/10 text-primary hover:bg-primary/[0.18] hover:border-primary/80',
    secondary: cn(
      'border bg-card/60 text-muted-foreground hover:text-foreground hover:border-border-strong',
      active ? 'border-primary/60 bg-primary/10 text-primary' : 'border-border',
    ),
    danger: 'border border-critical/50 bg-transparent text-critical hover:bg-critical/10',
    ghost: 'text-muted-foreground hover:text-foreground',
  }

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={ariaPressed}
      className={cn(base, variants[variant], className)}
    >
      {children}
    </button>
  )
}

/* ------------------------------------------------------------------ */
/* Metric row (label/value)                                            */
/* ------------------------------------------------------------------ */

export function MetricRow({
  label,
  value,
  valueClassName,
}: {
  label: string
  value: ReactNode
  valueClassName?: string
}) {
  return (
    <div className="flex items-center justify-between py-2 text-[13px]">
      <span className="text-muted-foreground">{label}</span>
      <span className={cn('font-mono tabular-nums text-foreground', valueClassName)}>{value}</span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Human review disclaimer                                             */
/* ------------------------------------------------------------------ */

export function ReviewDisclaimer({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex items-start gap-2.5 rounded-md border-l-2 border-l-pattern border-y border-r border-y-border border-r-border bg-pattern/[0.06] px-3.5 py-2.5',
        className,
      )}
    >
      <span className="mt-1 size-1.5 shrink-0 rounded-full bg-pattern" aria-hidden />
      <p className="text-[13px] leading-relaxed text-pattern/90">
        <span className="font-mono text-[11px] uppercase tracking-[0.13em] text-pattern">
          Requires human review —{' '}
        </span>
        candidate findings are generated by the local discovery engine and must be validated by a
        person before any local action.
      </p>
    </div>
  )
}
