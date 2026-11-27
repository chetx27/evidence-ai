import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { getJson } from "./api";
import { Notice, Shell } from "./components";
import type { CasePayload } from "./types";
import { CaseHome } from "./views/CaseHome";
import { ContradictionDetail, ContradictionList } from "./views/Contradictions";
import { DocumentList, DocumentView } from "./views/Documents";
import { EvaluationView } from "./views/Evaluation";
import { InvestigateView } from "./views/Investigate";

const FALLBACK_DISCLAIMER =
  "EvidenceAI outputs are investigative aids, not adjudications. Gate 1 does not select a winning source. Calibrated probabilities are not yet measured.";

export function App() {
  const [casePayload, setCasePayload] = useState<CasePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<CasePayload>("/api/case")
      .then((payload) => {
        setCasePayload(payload);
        setError(null);
      })
      .catch(() => {
        setError("The API did not respond. Start the Gate 1 server on 127.0.0.1:8000 and reload.");
      });
  }, []);

  return (
    <Shell
      disclaimer={casePayload?.standing_disclaimer ?? FALLBACK_DISCLAIMER}
      banner={casePayload?.disclaimer ?? null}
    >
      {error ? <Notice>{error}</Notice> : null}
      <Routes>
        <Route path="/" element={<CaseHome initial={casePayload} />} />
        <Route path="/documents" element={<DocumentList />} />
        <Route path="/documents/:documentId" element={<DocumentView />} />
        <Route path="/contradictions" element={<ContradictionList />} />
        <Route path="/contradictions/:assessmentId" element={<ContradictionDetail />} />
        <Route path="/investigate" element={<InvestigateView questions={casePayload?.registered_questions ?? []} />} />
        <Route path="/evaluation" element={<EvaluationView />} />
      </Routes>
    </Shell>
  );
}
