import { useEffect, useState } from "react";
import { getJson } from "../api";
import { Notice, Panel } from "../components";
import type { EvaluationPayload, Rate } from "../types";

function formatRate(rate: Rate): string {
  if (!rate) return "undefined";
  return `${rate.numerator}/${rate.denominator} (${rate.value})`;
}

export function EvaluationView() {
  const [payload, setPayload] = useState<EvaluationPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getJson<EvaluationPayload>("/api/evaluation")
      .then(setPayload)
      .catch(() => setError("The fixture diagnostic could not be loaded."));
  }, []);

  if (error) return <Notice>{error}</Notice>;
  if (!payload) return <Notice>Loading the fixture diagnostic.</Notice>;
  return (
    <div className="grid gap-4">
      <Panel title={payload.fixture}>
        <p className="text-sm text-muted">{payload.fixture_role}</p>
        <p className="mt-2 text-sm">Corpus label: {payload.corpus_label}</p>
        <p className="mt-2 text-sm">
          Directional expectation met: {payload.directional_expectation_met ? "yes" : "no"}. This is a census of the fixed fixture.
        </p>
      </Panel>
      {Object.entries(payload.methods).map(([name, block]) => (
        <Panel key={name} title={name}>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted">False-conflict rate</dt>
            <dd className="font-mono text-xs">{formatRate(block.false_conflict_rate)}</dd>
            <dt className="text-muted">Recall</dt>
            <dd className="font-mono text-xs">{formatRate(block.recall)}</dd>
            <dt className="text-muted">Precision</dt>
            <dd className="font-mono text-xs">{formatRate(block.precision)}</dd>
            <dt className="text-muted">Counts</dt>
            <dd className="font-mono text-xs">
              tp {block.tp} fp {block.fp} tn {block.tn} fn {block.fn}
            </dd>
          </dl>
        </Panel>
      ))}
      <Panel title="Quotation check">
        <p className="text-sm">{payload.quotation_check.note}</p>
        <p className="mt-2 font-mono text-xs">{formatRate(payload.quotation_check.pass_rate)}</p>
      </Panel>
      <Panel title="Not measured">
        <ul className="grid gap-2 text-sm">
          {payload.not_measured.map((item) => (
            <li key={item.metric}>
              <span className="font-mono text-xs">{item.metric}</span>
              <span className="text-muted"> — {item.reason}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
