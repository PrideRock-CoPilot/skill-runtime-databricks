import type { ReactNode } from "react";

interface SectionHeadingProps {
  kicker: string;
  title: string;
  subtitle?: string;
  meta?: ReactNode;
  actions?: ReactNode;
}

interface OverviewCardProps {
  label: string;
  value: string;
  detail: string;
  tone?: "accent" | "calm" | "strong";
}

interface EmptyStateProps {
  title: string;
  detail: string;
  compact?: boolean;
}

export function SectionHeading({ kicker, title, subtitle, meta, actions }: SectionHeadingProps) {
  return (
    <div className="panel-header">
      <div>
        <p className="panel-kicker">{kicker}</p>
        <h2>{title}</h2>
        {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
      </div>
      {meta || actions ? (
        <div className="panel-actions">
          {meta}
          {actions}
        </div>
      ) : null}
    </div>
  );
}

export function OverviewCard({ label, value, detail, tone = "accent" }: OverviewCardProps) {
  return (
    <article className={`overview-card ${tone}`}>
      <span className="overview-label">{label}</span>
      <strong className="overview-value">{value}</strong>
      <p className="overview-detail">{detail}</p>
    </article>
  );
}

export function EmptyState({ title, detail, compact = false }: EmptyStateProps) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`.trim()}>
      <strong>{title}</strong>
      <p>{detail}</p>
    </div>
  );
}