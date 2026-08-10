import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, AnnotatorProfile } from "../api";

export function AnnotatorIntelligenceView({ datasetId }: { datasetId: string }) {
  const { data: profiles, isPending, isError } = useQuery({
    queryKey: ["annotator-intelligence", datasetId],
    queryFn: () => api.annotatorIntelligence(datasetId),
  });

  const [sortKey, setSortKey] = useState<"total_annotations" | "evaluated_gold_items" | "posterior_mean" | "lower_bound">("total_annotations");
  const [selectedWorker, setSelectedWorker] = useState<string | null>(null);

  if (isPending) return <p role="status">Loading annotator intelligence…</p>;
  if (isError || !profiles) return <p role="alert" className="error">Could not load annotator intelligence.</p>;

  // Sort profiles according to selected key (Default: total_annotations - Amendment 6)
  const sorted = [...profiles].sort((a, b) => {
    if (sortKey === "total_annotations") return b.total_annotations - a.total_annotations;
    if (sortKey === "evaluated_gold_items") return b.evaluated_gold_items - a.evaluated_gold_items;
    const aMean = a.beta_binomial?.posterior_mean ?? 0;
    const bMean = b.beta_binomial?.posterior_mean ?? 0;
    if (sortKey === "posterior_mean") return bMean - aMean;
    const aBound = a.beta_binomial?.lower_bound ?? 0;
    const bBound = b.beta_binomial?.lower_bound ?? 0;
    return bBound - aBound;
  });

  const activeProfile = sorted.find((p) => p.annotator_id === selectedWorker) ?? sorted[0];

  return (
    <section aria-labelledby="annotator-intel-title" className="panel">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Statistically estimated · B/C</span>
          <h3 id="annotator-intel-title">Annotator Intelligence &amp; Bayesian Reliability</h3>
        </div>
        <span className="evidence-level adequate">Beta-Binomial Shrinkage</span>
      </div>

      <p className="method-note">
        Gold-Observed Reliability and Bayesian Reliability derive strictly from evaluated hard gold.
        Default ordering is evidence-oriented (annotation count / gold N) to avoid single-number ranking bias on low-support workers.
      </p>

      <div className="controls">
        <label>
          Sort annotators by:
          <select value={sortKey} onChange={(e) => setSortKey(e.target.value as typeof sortKey)}>
            <option value="total_annotations">Total Annotations N (Default Evidence Support)</option>
            <option value="evaluated_gold_items">Evaluated Gold N</option>
            <option value="posterior_mean">Posterior Reliability Mean</option>
            <option value="lower_bound">95% Credible Lower Bound</option>
          </select>
        </label>
      </div>

      <div className="table-wrap">
        <table>
          <caption>Annotator Reliability Profiles (Leave-One-Worker-Out Project Prior)</caption>
          <thead>
            <tr>
              <th scope="col">Annotator</th>
              <th scope="col">Total N</th>
              <th scope="col">Gold N</th>
              <th scope="col">Gold Correctness</th>
              <th scope="col">Posterior Reliability Mean</th>
              <th scope="col">95% Credible Interval</th>
              <th scope="col">Evidence Level</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((p) => {
              const bb = p.beta_binomial;
              const isSelected = p.annotator_id === activeProfile?.annotator_id;
              return (
                <tr
                  key={p.annotator_id}
                  className={isSelected ? "selected-row" : ""}
                  onClick={() => setSelectedWorker(p.annotator_id)}
                  style={{ cursor: "pointer" }}
                >
                  <th scope="row">
                    <strong>{p.annotator_id}</strong>
                  </th>
                  <td>{p.total_annotations}</td>
                  <td>{p.evaluated_gold_items}</td>
                  <td>
                    {bb && bb.evaluated_gold_items > 0
                      ? `${bb.successes} / ${bb.evaluated_gold_items}`
                      : "No Gold"}
                  </td>
                  <td>
                    {bb && bb.evaluated_gold_items > 0
                      ? bb.posterior_mean.toFixed(3)
                      : "—"}
                  </td>
                  <td>
                    {bb && bb.evaluated_gold_items > 0
                      ? `[${bb.lower_bound.toFixed(3)}, ${bb.upper_bound.toFixed(3)}]`
                      : "—"}
                  </td>
                  <td>
                    <span className={`evidence-level ${p.evidence_level}`}>{p.evidence_level}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {activeProfile && (
        <article className="diagnostic" style={{ marginTop: "1.5rem" }}>
          <h4>Annotator Detail: {activeProfile.annotator_id}</h4>

          {activeProfile.beta_binomial && (
            <div className="provenance-box" style={{ marginBottom: "1rem" }}>
              <h5>Bayesian Gold Reliability Provenance</h5>
              <dl>
                <div>
                  <dt>Prior Source</dt>
                  <dd><code>{activeProfile.beta_binomial.prior_source}</code></dd>
                </div>
                <div>
                  <dt>Prior Mean (m_-w)</dt>
                  <dd>{activeProfile.beta_binomial.prior_mean.toFixed(3)}</dd>
                </div>
                <div>
                  <dt>Prior Strength (kappa_0)</dt>
                  <dd>{activeProfile.beta_binomial.prior_strength}</dd>
                </div>
                <div>
                  <dt>Population N (excluding worker)</dt>
                  <dd>{activeProfile.beta_binomial.prior_population_n}</dd>
                </div>
              </dl>
            </div>
          )}

          {activeProfile.dirichlet_confusion && (
            <div>
              <h5>Dirichlet-Smoothed Class Confusion (Jeffreys Prior &alpha; = 0.5)</h5>
              <p className="method-note">
                Cell bounds are <em>marginal Beta credible intervals</em> derived from the Dirichlet posterior. Raw counts remain separate from smoothed probabilities.
              </p>
              <div className="table-wrap">
                <table className="confusion">
                  <thead>
                    <tr>
                      <th scope="col">Gold ↓ / Emitted →</th>
                      {activeProfile.dirichlet_confusion.labels.map((l) => (
                        <th scope="col" key={l}>{l}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {activeProfile.dirichlet_confusion.labels.map((cLabel, cIdx) => (
                      <tr key={cLabel}>
                        <th scope="row">{cLabel} (N={activeProfile.dirichlet_confusion?.row_support[cLabel] ?? 0})</th>
                        {activeProfile.dirichlet_confusion?.labels.map((kLabel, kIdx) => {
                          const raw = activeProfile.dirichlet_confusion?.raw_counts[cIdx][kIdx] ?? 0;
                          const prob = activeProfile.dirichlet_confusion?.smoothed_probabilities[cIdx][kIdx] ?? 0;
                          return (
                            <td key={kLabel}>
                              <strong>{prob.toFixed(3)}</strong>
                              <small style={{ display: "block", color: "var(--color-muted, #666)" }}>
                                Raw: {raw}
                              </small>
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeProfile.calibration && (
            <div style={{ marginTop: "1rem" }}>
              <h5>Calibration Metrics</h5>
              {activeProfile.calibration.status === "available" ? (
                <dl>
                  <div>
                    <dt>Brier Score</dt>
                    <dd>{activeProfile.calibration.brier_score?.toFixed(4)}</dd>
                  </div>
                  <div>
                    <dt>Expected Calibration Error (ECE)</dt>
                    <dd>{activeProfile.calibration.ece?.toFixed(4)}</dd>
                  </div>
                </dl>
              ) : (
                <p className="method-note">{activeProfile.calibration.reason ?? "Calibration unavailable."}</p>
              )}
            </div>
          )}
        </article>
      )}
    </section>
  );
}
