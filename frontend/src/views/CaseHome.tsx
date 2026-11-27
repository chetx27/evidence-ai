import { Link } from "react-router-dom";
import { Notice, Panel } from "../components";
import type { CasePayload } from "../types";

export function CaseHome({ initial }: { initial: CasePayload | null }) {
  if (!initial) {
    return <Notice>Loading the case record.</Notice>;
  }
  const counts = initial.counts;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Panel title="Corpus">
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <dt className="text-muted">Case</dt>
          <dd className="font-mono text-xs">{initial.case_id}</dd>
          <dt className="text-muted">Label</dt>
          <dd>{initial.corpus_label}</dd>
          <dt className="text-muted">Documents</dt>
          <dd>{counts ? counts.documents : "not yet measured"}</dd>
          <dt className="text-muted">Claims</dt>
          <dd>{counts ? counts.claims : "not yet measured"}</dd>
          <dt className="text-muted">Triage conflicts</dt>
          <dd>{initial.triage_conflicts}</dd>
          <dt className="text-muted">Run</dt>
          <dd>{initial.run_status}</dd>
          <dt className="text-muted">Duration seconds</dt>
          <dd className="font-mono text-xs">{initial.duration_seconds ?? "not yet measured"}</dd>
        </dl>
      </Panel>
      <Panel title="Pack">
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <dt className="text-muted">Pack</dt>
          <dd>
            {initial.pack_id} {initial.pack_version}
          </dd>
          <dt className="text-muted">Extractor</dt>
          <dd className="font-mono text-xs">{initial.extractor_id}</dd>
          <dt className="text-muted">Schema</dt>
          <dd className="font-mono text-xs">{initial.schema_version}</dd>
          <dt className="text-muted">Pre-registration</dt>
          <dd className="font-mono text-xs">{initial.preregistration_id}</dd>
          <dt className="text-muted">Seed</dt>
          <dd>{initial.seed ?? "not recorded"}</dd>
        </dl>
        <p className="mt-4 text-sm">
          <Link className="text-accent underline" to="/contradictions">
            Open the numeric triage queue
          </Link>
        </p>
      </Panel>
    </div>
  );
}
