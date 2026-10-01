import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { api, LabelCollectionPlan } from "../api";

const STATUS_TEXT: Record<LabelCollectionPlan["items"][number]["status"], string> = {
  confident: "Settled",
  collect_more: "Needs more labels",
  expert_review: "Expert review",
};

const percent = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`;

export function LabelCollectionView({ datasetId }: { datasetId: string }) {
  const [target, setTarget] = useState(0.95);
  const [maxLabels, setMaxLabels] = useState(7);
  const plan = useQuery({
    queryKey: ["label-collection", datasetId, target, maxLabels],
    queryFn: () => api.labelCollectionPlan(datasetId, target, maxLabels),
  });

  return (
    <section aria-labelledby="collection-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Model-estimated · C</span>
          <h3 id="collection-title">Label collection plan</h3>
        </div>
        {plan.data && <span className="evidence-level adequate">{plan.data.basis === "dawid_skene_worker_model" ? "Worker model fitted" : "Assumed accuracy"}</span>}
      </div>
      <p className="method-note">
        Stop paying for labels once an item is settled. Each item gets another label only while the model is below the
        target confidence; items still contested after the maximum go to an expert, because persistent disagreement is
        often genuine ambiguity rather than error. No gold labels are used to plan.
      </p>

      <div className="collection-controls">
        <label className="filter">
          Target confidence
          <select value={target} onChange={(event) => setTarget(Number(event.target.value))}>
            <option value={0.9}>90%</option>
            <option value={0.95}>95% (recommended)</option>
            <option value={0.99}>99%</option>
          </select>
        </label>
        <label className="filter">
          Maximum labels per item
          <select value={maxLabels} onChange={(event) => setMaxLabels(Number(event.target.value))}>
            {[3, 5, 7, 9].map((value) => <option key={value} value={value}>{value}</option>)}
          </select>
        </label>
      </div>

      {plan.isPending && <p role="status">Fitting the worker model…</p>}
      {plan.isError && <p role="alert" className="error">The collection plan could not be computed: {plan.error.message}</p>}
      {plan.data && (
        <>
          <div className="result-grid">
            <article className="result">
              <span>Settled — stop labelling</span>
              <strong>{plan.data.status_counts.confident}</strong>
              <small>{percent(plan.data.status_counts.confident / Math.max(1, plan.data.items_total))} of {plan.data.items_total} items reach {percent(target)} with ≥2 labels</small>
            </article>
            <article className="result">
              <span>Need more labels</span>
              <strong>{plan.data.status_counts.collect_more}</strong>
              <small>{plan.data.additional_labels_requested} labels requested next round (optimistic estimate)</small>
            </article>
            <article className="result">
              <span>Send to expert</span>
              <strong>{plan.data.status_counts.expert_review}</strong>
              <small>Still contested after {maxLabels} labels — clarify guidelines or keep a label distribution</small>
            </article>
          </div>
          <p className="method-note">
            Average annotator accuracy under the fitted model: {percent(plan.data.average_annotator_accuracy, 1)}.
            Evidence: on the twelve synthetic scenarios at a 95% target, this rule matched full-redundancy accuracy while
            saving 0–14% of labels at 3–5 labels per item, and 25–63% (within 0.8 points of accuracy) in an exploratory
            run at 7–9 labels per item.
          </p>

          <div className="table-wrap" tabIndex={0} role="region" aria-label="Items needing action">
            <table>
              <caption>
                Items that need action first ({plan.data.items_returned} of {plan.data.items_total} shown, most uncertain first)
              </caption>
              <thead>
                <tr>
                  <th scope="col">Item</th>
                  <th scope="col">Decision</th>
                  <th scope="col">Labels so far</th>
                  <th scope="col">Most likely label</th>
                  <th scope="col">Confidence</th>
                  <th scope="col">Ask for</th>
                </tr>
              </thead>
              <tbody>
                {plan.data.items.filter((row) => row.status !== "confident").slice(0, 50).map((row) => (
                  <tr key={row.item_id}>
                    <th scope="row"><code>{row.item_id}</code></th>
                    <td><span className={`decision decision-${row.status}`}>{STATUS_TEXT[row.status]}</span></td>
                    <td>{row.labels_collected}</td>
                    <td>{row.most_likely_label}</td>
                    <td>
                      <span className="confidence-bar" role="img" aria-label={`Confidence ${percent(row.confidence, 1)} against a ${percent(target)} target`}>
                        <span style={{ width: percent(row.confidence, 1) }} />
                      </span>
                      {percent(row.confidence, 1)}
                    </td>
                    <td>{row.status === "collect_more" ? `${row.additional_labels} more` : row.status === "expert_review" ? "Expert" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {plan.data.status_counts.collect_more + plan.data.status_counts.expert_review === 0 && (
              <p className="method-note">Every item is settled at this target. No further labels are needed.</p>
            )}
          </div>
          <details className="method-details">
            <summary>How the plan is calculated</summary>
            <ul>{plan.data.method.map((line) => <li key={line}>{line}</li>)}</ul>
          </details>
        </>
      )}
    </section>
  );
}
