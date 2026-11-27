import { FormEvent, useState } from "react";
import { postJson } from "../api";
import { DocumentLink, Notice, Panel, Status } from "../components";
import type { AnswerPayload } from "../types";

export function InvestigateView({ questions }: { questions: string[] }) {
  const [question, setQuestion] = useState(questions[0] ?? "");
  const [answer, setAnswer] = useState<AnswerPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const payload = await postJson<AnswerPayload>("/api/investigate", { question });
      setAnswer(payload);
    } catch {
      setError("The question could not be answered.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid gap-4">
      <form onSubmit={submit} className="grid gap-3">
        <label className="text-sm" htmlFor="question">
          Question
        </label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          className="rounded-sm border border-line bg-inset px-3 py-2 text-sm text-ink"
        />
        <div className="flex flex-wrap gap-2">
          {questions.map((preset) => (
            <button
              key={preset}
              type="button"
              className="rounded-sm border border-line px-3 py-1 text-left text-xs"
              onClick={() => setQuestion(preset)}
            >
              {preset}
            </button>
          ))}
          <button type="submit" className="rounded-sm border border-line-strong bg-overlay px-3 py-1 text-sm">
            {pending ? "Asking" : "Ask"}
          </button>
        </div>
      </form>
      {error ? <Notice>{error}</Notice> : null}
      {answer ? (
        <Panel title="Finding">
          <Status state={answer.state} />
          <p className="mt-2 text-sm text-muted">{answer.state_definition}</p>
          <p className="mt-2 text-xs text-muted">{answer.audit_note}</p>
          <ul className="mt-4 grid gap-3">
            {answer.quotations.map((quotation) => (
              <li key={quotation.span_id} className="border border-line bg-inset px-3 py-2">
                <p className="font-mono text-sm">{quotation.text}</p>
                <p className="mt-2 text-xs text-muted">
                  <DocumentLink id={quotation.document_id} label={quotation.external_key} /> offsets{" "}
                  {quotation.char_start}-{quotation.char_end} · verifier {quotation.verifier_method}
                </p>
              </li>
            ))}
          </ul>
          {answer.quotations.length === 0 ? (
            <p className="mt-3 text-sm">No quotation was shipped.</p>
          ) : null}
          <p className="mt-4 text-sm">{answer.what_would_change}</p>
          <ul className="mt-3 grid gap-1 text-xs text-muted">
            {answer.system_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}
