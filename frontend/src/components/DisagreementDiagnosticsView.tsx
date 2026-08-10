import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, ItemDisagreementFeatures, QualityFlag } from "../api";

export function DisagreementDiagnosticsView({ datasetId }: { datasetId: string }) {
  const { data: flags, isPending: flagsPending } = useQuery({
    queryKey: ["quality-flags", datasetId],
    queryFn: () => api.qualityFlags(datasetId),
  });

  const { data: itemDiagnostics, isPending: diagPending } = useQuery({
    queryKey: ["item-diagnostics", datasetId],
    queryFn: () => api.itemDiagnostics(datasetId),
  });

  const [filterType, setFilterType] = useState<string>("all");
  const [filterEntityType, setFilterEntityType] = useState<string>("all");
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  if (flagsPending || diagPending) return <p role="status">Loading disagreement diagnostics…</p>;
  if (!flags || !itemDiagnostics) return <p role="alert" className="error">Could not load diagnostics.</p>;

  // Filter quality flags
  const filteredFlags = flags.filter((f) => {
    if (filterType !== "all" && f.flag_type !== filterType) return false;
    if (filterEntityType !== "all" && f.entity_type !== filterEntityType) return false;
    return true;
  });

  // Calculate summary counts
  const flagCounts = {
    probable_quality_defect: flags.filter((f) => f.flag_type === "probable_quality_defect").length,
    probable_ambiguity_policy_issue: flags.filter((f) => f.flag_type === "probable_ambiguity_policy_issue").length,
    mixed_evidence: flags.filter((f) => f.flag_type === "mixed_evidence").length,
    insufficient_evidence: flags.filter((f) => f.flag_type === "insufficient_evidence").length,
    no_flag: flags.filter((f) => f.flag_type === "no_flag").length,
  };

  const activeFlag = filteredFlags.find((f) => f.entity_id === selectedEntityId) ?? filteredFlags[0];
  const activeItemDiag = activeFlag
    ? itemDiagnostics.find((d) => d.item_id === (activeFlag.entity_type === "annotation" ? (activeFlag.evidence.item_id as string) : activeFlag.entity_id))
    : itemDiagnostics[0];

  return (
    <section aria-labelledby="diagnostics-title" className="panel">
      <div className="section-heading">
        <div>
          <span className="section-kicker">Heuristic Diagnostic · D</span>
          <h3 id="diagnostics-title">Item Disagreement &amp; Quality Flags</h3>
        </div>
        <span className="evidence-level adequate">Explainable QualityFlags</span>
      </div>

      <p className="method-note">
        Diagnostic rules evaluate vote entropy, margin, consensus disagreement, and dissenting worker gold reliability.
        Per Amendment 1, lone dissenting annotations are flagged as <code>entity_type = annotation</code>, reserving item-level defect flags for data corruption.
      </p>

      {/* Summary Cards */}
      <div className="result-grid" style={{ marginBottom: "1rem" }}>
        <article className="result" style={{ borderLeft: "4px solid #ef4444" }}>
          <span>Probable Quality Defect</span>
          <strong>{flagCounts.probable_quality_defect}</strong>
          <small>Dissenting annotation / data defect</small>
        </article>
        <article className="result" style={{ borderLeft: "4px solid #f59e0b" }}>
          <span>Probable Ambiguity / Policy</span>
          <strong>{flagCounts.probable_ambiguity_policy_issue}</strong>
          <small>High entropy / policy gap</small>
        </article>
        <article className="result" style={{ borderLeft: "4px solid #3b82f6" }}>
          <span>Mixed Evidence</span>
          <strong>{flagCounts.mixed_evidence}</strong>
          <small>Contradictory signals</small>
        </article>
        <article className="result" style={{ borderLeft: "4px solid #6b7280" }}>
          <span>Insufficient Evidence</span>
          <strong>{flagCounts.insufficient_evidence}</strong>
          <small>Low annotation count (&lt; 2)</small>
        </article>
      </div>

      {/* Filter controls */}
      <div className="controls" style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <label>
          Filter by Flag Type:
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)}>
            <option value="all">All Flags ({flags.length})</option>
            <option value="probable_quality_defect">Probable Quality Defect ({flagCounts.probable_quality_defect})</option>
            <option value="probable_ambiguity_policy_issue">Probable Ambiguity / Policy ({flagCounts.probable_ambiguity_policy_issue})</option>
            <option value="mixed_evidence">Mixed Evidence ({flagCounts.mixed_evidence})</option>
            <option value="insufficient_evidence">Insufficient Evidence ({flagCounts.insufficient_evidence})</option>
            <option value="no_flag">No Flag ({flagCounts.no_flag})</option>
          </select>
        </label>
        <label>
          Filter by Entity Type:
          <select value={filterEntityType} onChange={(e) => setFilterEntityType(e.target.value)}>
            <option value="all">All Entities</option>
            <option value="annotation">Annotation (Dissenting worker)</option>
            <option value="item">Item (Data record)</option>
          </select>
        </label>
      </div>

      {/* Quality Flags Table */}
      <div className="table-wrap">
        <table>
          <caption>Generated Quality Flags</caption>
          <thead>
            <tr>
              <th scope="col">Entity ID</th>
              <th scope="col">Entity Type</th>
              <th scope="col">Flag Type</th>
              <th scope="col">Severity</th>
              <th scope="col">Recommended Action</th>
              <th scope="col">Support N</th>
              <th scope="col">Explanation</th>
            </tr>
          </thead>
          <tbody>
            {filteredFlags.map((f) => {
              const isSelected = f.entity_id === activeFlag?.entity_id;
              return (
                <tr
                  key={f.quality_flag_id}
                  className={isSelected ? "selected-row" : ""}
                  onClick={() => setSelectedEntityId(f.entity_id)}
                  style={{ cursor: "pointer" }}
                >
                  <th scope="row">
                    <code>{f.entity_id}</code>
                  </th>
                  <td>
                    <span className="badge">{f.entity_type}</span>
                  </td>
                  <td>
                    <strong className={`flag-badge ${f.flag_type}`}>{f.flag_type}</strong>
                  </td>
                  <td>
                    <span className={`severity ${f.severity}`}>{f.severity}</span>
                  </td>
                  <td>
                    <code>{f.recommended_action}</code>
                  </td>
                  <td>{f.support_n}</td>
                  <td style={{ maxWidth: "300px", whiteSpace: "normal" }}>{f.explanation}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Active Flag & Item Detail UX */}
      {activeFlag && (
        <article className="diagnostic" style={{ marginTop: "1.5rem" }}>
          <div className="section-heading">
            <div>
              <span className="section-kicker">Structured QualityFlag Detail · {activeFlag.entity_type}</span>
              <h4>{activeFlag.quality_flag_id} (Entity: {activeFlag.entity_id})</h4>
            </div>
            <span className={`severity ${activeFlag.severity}`}>{activeFlag.severity} severity</span>
          </div>

          <p><strong>Explanation:</strong> {activeFlag.explanation}</p>
          <p><strong>Recommended Action:</strong> <code>{activeFlag.recommended_action}</code></p>

          {/* Frozen Threshold Provenance */}
          <div className="provenance-box" style={{ marginTop: "1rem", marginBottom: "1rem" }}>
            <h5>Diagnostic Rule Provenance</h5>
            <dl>
              <div>
                <dt>Rule Method</dt>
                <dd><code>{activeFlag.method}</code></dd>
              </div>
              <div>
                <dt>Config Version</dt>
                <dd><code>{activeFlag.threshold_config_version}</code></dd>
              </div>
              <div>
                <dt>Config Hash</dt>
                <dd><code>{activeFlag.threshold_config_hash.substring(0, 16)}...</code></dd>
              </div>
            </dl>
          </div>

          {/* Item Features Breakdown */}
          {activeItemDiag && (
            <div className="split" style={{ marginTop: "1rem" }}>
              <div>
                <h5>Item Disagreement Features</h5>
                <dl>
                  <div>
                    <dt>Vote Count (N)</dt>
                    <dd>{activeItemDiag.annotation_count}</dd>
                  </div>
                  <div>
                    <dt>Normalized Vote Entropy (H/ln K)</dt>
                    <dd>{activeItemDiag.normalized_entropy !== null ? activeItemDiag.normalized_entropy.toFixed(3) : "Undefined (K<=1)"}</dd>
                  </div>
                  <div>
                    <dt>Vote Margin</dt>
                    <dd>{activeItemDiag.vote_margin.toFixed(3)}</dd>
                  </div>
                  <div>
                    <dt>Distinct Labels Emitted</dt>
                    <dd>{activeItemDiag.distinct_labels_count}</dd>
                  </div>
                  <div>
                    <dt>Method Disagreement (MV vs DS)</dt>
                    <dd>{activeItemDiag.method_disagreement ? "Yes" : "No"}</dd>
                  </div>
                </dl>
              </div>

              <div>
                <h5>Consensus &amp; Worker Evidence</h5>
                <dl>
                  <div>
                    <dt>Majority Vote Label</dt>
                    <dd>{activeItemDiag.mv_label ?? "Unresolved"}</dd>
                  </div>
                  <div>
                    <dt>Dawid-Skene Status</dt>
                    <dd>{activeItemDiag.ds_status}</dd>
                  </div>
                  <div>
                    <dt>Dissenting Workers</dt>
                    <dd>{activeItemDiag.dissenting_worker_ids.length > 0 ? activeItemDiag.dissenting_worker_ids.join(", ") : "None"}</dd>
                  </div>
                </dl>
              </div>
            </div>
          )}
        </article>
      )}
    </section>
  );
}
