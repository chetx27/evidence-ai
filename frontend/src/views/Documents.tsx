import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getJson } from "../api";
import { HighlightedText, Notice, Panel } from "../components";
import type { ClaimRecord, DocumentDetail, DocumentSummary } from "../types";

export function DocumentList() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<{ documents: DocumentSummary[] }>("/api/documents")
      .then((payload) => setDocuments(payload.documents))
      .catch(() => setError("Documents could not be loaded."));
  }, []);

  if (error) return <Notice>{error}</Notice>;
  if (!documents) return <Notice>Loading documents.</Notice>;
  return (
    <div className="overflow-x-auto rounded-sm border border-line">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-line bg-raised text-muted">
          <tr>
            <th className="px-3 py-2 font-medium">Document</th>
            <th className="px-3 py-2 font-medium">Type</th>
            <th className="px-3 py-2 font-medium">Trial</th>
            <th className="px-3 py-2 font-medium">Date</th>
            <th className="px-3 py-2 font-medium">Hash</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((document) => (
            <tr key={document.document_id} className="border-b border-line-subtle">
              <td className="px-3 py-2">
                <Link className="text-accent underline" to={`/documents/${document.document_id}`}>
                  {document.external_key}
                </Link>
              </td>
              <td className="px-3 py-2">{document.doc_type}</td>
              <td className="px-3 py-2 font-mono text-xs">{document.trial_id}</td>
              <td className="px-3 py-2 font-mono text-xs">{document.document_date}</td>
              <td className="px-3 py-2 font-mono text-xs">{document.content_hash.slice(0, 12)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DocumentView() {
  const { documentId } = useParams();
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<ClaimRecord | null>(null);

  useEffect(() => {
    if (!documentId) return;
    setDocument(null);
    setSelected(null);
    getJson<DocumentDetail>(`/api/documents/${documentId}`)
      .then(setDocument)
      .catch(() => setError("This document could not be loaded."));
  }, [documentId]);

  if (error) return <Notice>{error}</Notice>;
  if (!document) return <Notice>Loading the document.</Notice>;
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <Panel title={document.external_key}>
        <p className="mb-3 text-xs text-muted">{document.page_note}</p>
        <p className="mb-3 font-mono text-xs text-muted">{document.content_hash}</p>
        {document.warnings.length > 0 ? (
          <p className="mb-3 text-sm text-uncertain">Warnings: {document.warnings.join(", ")}</p>
        ) : null}
        <HighlightedText
          text={document.text}
          spans={document.spans}
          claims={document.claims}
          activeSpanId={selected?.span_id ?? null}
          onSelect={setSelected}
        />
      </Panel>
      <Panel title="Claim">
        {selected ? (
          <dl className="grid gap-2 text-sm">
            <dt className="text-muted">Predicate</dt>
            <dd className="font-mono text-xs">{selected.predicate}</dd>
            <dt className="text-muted">Surface token</dt>
            <dd className="font-mono text-xs">{selected.raw_token}</dd>
            <dt className="text-muted">Canonical value</dt>
            <dd className="font-mono text-xs">
              {selected.canonical_value} {selected.dimension}
            </dd>
            <dt className="text-muted">Valid time</dt>
            <dd className="font-mono text-xs">
              {selected.valid_time_start ?? "unknown"} to {selected.valid_time_end ?? "unknown"} (
              {selected.valid_time_uncertainty})
            </dd>
            <dt className="text-muted">Composite confidence</dt>
            <dd>{selected.confidence.value === null ? "not yet measured" : selected.confidence.value}</dd>
            <dt className="text-muted">Calibration</dt>
            <dd>{selected.confidence.calibration}</dd>
            <dd className="text-xs text-muted">{selected.extraction_note}</dd>
          </dl>
        ) : (
          <p className="text-sm text-muted">Select a highlighted span. The highlight is the stored span, not a generated summary.</p>
        )}
      </Panel>
    </div>
  );
}
