import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJson } from "../api";
import { DocumentLink, Notice, Panel } from "../components";
import type { ContradictionDetail, ContradictionSummary } from "../types";

export function ContradictionList() {
  const [items, setItems] = useState<ContradictionSummary[] | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<{ contradictions: ContradictionSummary[]; note: string }>("/api/contradictions")
      .then((payload) => {
        setItems(payload.contradictions);
        setNote(payload.note);
      })
      .catch(() => setError("Contradictions could not be loaded."));
  }, []);

  if (error) return <Notice>{error}</Notice>;
  if (!items) return <Notice>Loading the triage queue.</Notice>;
  return (
    <div className="grid gap-4">
      <p className="text-sm text-muted">{note}</p>
      {items.length === 0 ? <Notice>No numeric conflicts are in the triage queue.</Notice> : null}
      <div className="overflow-x-auto rounded-sm border border-line">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line bg-raised text-muted">
            <tr>
              <th className="px-3 py-2 font-medium">Trial</th>
              <th className="px-3 py-2 font-medium">Predicate</th>
              <th className="px-3 py-2 font-medium">Tokens</th>
              <th className="px-3 py-2 font-medium">Subtype</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.assessment_id} className="border-b border-line-subtle">
                <td className="px-3 py-2 font-mono text-xs">
                  <Link className="text-accent underline" to={`/contradictions/${item.assessment_id}`}>
                    {item.trial_id}
                  </Link>
                </td>
                <td className="px-3 py-2">{item.predicate}</td>
                <td className="px-3 py-2 font-mono text-xs">
                  {item.raw_token_a} / {item.raw_token_b}
                </td>
                <td className="px-3 py-2">{item.subtype}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ContradictionDetail() {
  const { assessmentId } = useParams();
  const [detail, setDetail] = useState<ContradictionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!assessmentId) return;
    getJson<ContradictionDetail>(`/api/contradictions/${assessmentId}`)
      .then(setDetail)
      .catch(() => setError("This contradiction could not be loaded."));
  }, [assessmentId]);

  if (error) return <Notice>{error}</Notice>;
  if (!detail) return <Notice>Loading the pair.</Notice>;
  return (
    <div className="grid gap-4">
      <Panel title={`${detail.subtype} · ${detail.method}`}>
        <p className="text-sm">{detail.rationale}</p>
        <p className="mt-2 font-mono text-xs text-muted">
          difference {detail.abs_difference ?? "not computed"} · tolerance {detail.tolerance ?? "none"} · valid time{" "}
          {detail.valid_time_relation}
        </p>
        <p className="mt-3 text-sm text-muted">
          Composite confidence on both sides is{" "}
          {detail.left.confidence.value === null ? "not yet measured" : detail.left.confidence.value}. No winner is selected.
        </p>
      </Panel>
      <div className="grid gap-4 md:grid-cols-2">
        <Side title="Left span" side={detail.left} />
        <Side title="Right span" side={detail.right} />
      </div>
    </div>
  );
}

function Side({ title, side }: { title: string; side: ContradictionDetail["left"] }) {
  return (
    <Panel title={title}>
      <p className="mb-2 text-sm">
        <DocumentLink id={side.document_id} label={side.external_key} /> · {side.doc_type}
      </p>
      <p className="mb-2 font-mono text-xs text-muted">
        {side.raw_token} canonical {side.canonical_value}
      </p>
      <blockquote className="border border-line bg-evidence px-3 py-2 font-mono text-sm">{side.span_text}</blockquote>
      <p className="mt-2 font-mono text-xs text-muted">{side.content_hash}</p>
    </Panel>
  );
}
