import type { ReactNode } from "react";
import { Link, NavLink } from "react-router-dom";
import type { ClaimRecord, SpanRecord } from "./types";

const NAV = [
  ["/", "Case"],
  ["/documents", "Documents"],
  ["/contradictions", "Contradictions"],
  ["/investigate", "Investigate"],
  ["/evaluation", "Evaluation"],
] as const;

export function Shell({
  disclaimer,
  banner,
  children,
}: {
  disclaimer: string;
  banner: string | null;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-base text-ink">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:bg-raised focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <header className="border-b border-line bg-raised">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-3">
          <div>
            <p className="text-sm font-medium">EvidenceAI</p>
            <p className="text-xs text-muted">Gate 1 read interface</p>
          </div>
          <nav className="flex flex-wrap gap-2" aria-label="Primary">
            {NAV.map(([href, label]) => (
              <NavLink
                key={href}
                to={href}
                end={href === "/"}
                className={({ isActive }) =>
                  `rounded-sm border px-3 py-1 text-sm ${
                    isActive
                      ? "border-line-strong bg-overlay text-ink"
                      : "border-line-subtle text-muted"
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      {banner ? (
        <p className="border-b border-line bg-inset px-4 py-2 text-sm text-uncertain">{banner}</p>
      ) : null}
      <main id="main" className="mx-auto max-w-6xl px-4 py-6">
        {children}
      </main>
      <footer className="border-t border-line-subtle px-4 py-4 text-xs text-muted">
        {disclaimer}
      </footer>
    </div>
  );
}

export function Status({ state }: { state: string }) {
  const tone =
    state === "supported"
      ? "text-supported"
      : state === "contradicted"
        ? "text-contradicted"
        : "text-uncertain";
  return (
    <span className="inline-flex items-center gap-2 text-sm text-ink">
      <span className={tone} aria-hidden="true">
        {state === "supported" ? <CheckIcon /> : state === "contradicted" ? <CrossIcon /> : <DashIcon />}
      </span>
      <span>{state}</span>
    </span>
  );
}

export function Panel({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-sm border border-line bg-raised">
      <h2 className="border-b border-line-subtle px-4 py-2 text-sm font-medium">{title}</h2>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-sm border border-line bg-inset px-4 py-3 text-sm text-muted" role="status">
      {children}
    </p>
  );
}

export function HighlightedText({
  text,
  spans,
  claims,
  activeSpanId,
  onSelect,
}: {
  text: string;
  spans: SpanRecord[];
  claims: ClaimRecord[];
  activeSpanId: string | null;
  onSelect: (claim: ClaimRecord) => void;
}) {
  const points = new Set<number>([0, text.length]);
  for (const span of spans) {
    points.add(span.char_start);
    points.add(span.char_end);
  }
  const ordered = [...points].sort((left, right) => left - right);
  const claimsBySpan = new Map(claims.map((claim) => [claim.span_id, claim]));
  const segments = [];
  for (let index = 0; index < ordered.length - 1; index += 1) {
    const start = ordered[index];
    const end = ordered[index + 1];
    if (start === end) continue;
    const covering = spans.filter((span) => span.char_start <= start && span.char_end >= end);
    segments.push({ start, end, text: text.slice(start, end), covering });
  }
  return (
    <pre className="whitespace-pre-wrap font-mono text-sm leading-6 text-ink">
      {segments.map((segment) => {
        const evidence = segment.covering.find((span) => span.role === "evidence");
        const temporal = segment.covering.find((span) => span.role === "temporal");
        const boilerplate = segment.covering.find((span) => span.role === "boilerplate");
        const claim = evidence ? claimsBySpan.get(evidence.span_id) : undefined;
        if (evidence && claim) {
          const active = activeSpanId === evidence.span_id;
          return (
            <button
              key={`${segment.start}-${segment.end}`}
              type="button"
              onClick={() => onSelect(claim)}
              className={`rounded-sm border px-0 text-left ${
                active ? "border-accent bg-evidence" : "border-line bg-evidence"
              }`}
            >
              {segment.text}
            </button>
          );
        }
        const className = temporal
          ? "border border-line-subtle bg-temporal"
          : boilerplate
            ? "border border-line-subtle bg-boilerplate text-muted"
            : undefined;
        return (
          <span key={`${segment.start}-${segment.end}`} className={className}>
            {segment.text}
          </span>
        );
      })}
    </pre>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 7.2 5.2 10.5 12 3.5" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function CrossIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3 3.5 11 11M11 3.5 3 11" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function DashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M3 7h8" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

export function DocumentLink({ id, label }: { id: string; label: string }) {
  return (
    <Link to={`/documents/${id}`} className="text-accent underline">
      {label}
    </Link>
  );
}
