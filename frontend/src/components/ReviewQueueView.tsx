import { useMutation, useQuery } from "@tanstack/react-query";
import React, { useState } from "react";
import { api, ReviewCandidate } from "../api";

interface ReviewQueueViewProps {
  datasetId: string;
}

export const ReviewQueueView: React.FC<ReviewQueueViewProps> = ({ datasetId }) => {
  const [selectedMethod, setSelectedMethod] = useState<string>("erv");
  const [reviewUnit, setReviewUnit] = useState<"annotation" | "item">("annotation");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  const runMutation = useMutation({
    mutationFn: async () => {
      const res = await api.createReviewRun(datasetId, selectedMethod, reviewUnit);
      setActiveRunId(res.run_id);
      return res;
    },
  });

  const candidatesQuery = useQuery({
    queryKey: ["reviewCandidates", activeRunId],
    queryFn: () => (activeRunId ? api.getReviewCandidates(activeRunId, 100, 0) : Promise.resolve([])),
    enabled: Boolean(activeRunId),
  });

  return (
    <section className="panel review-queue" aria-labelledby="review-queue-title">
      <div className="eyebrow">Operational Review Prioritization</div>
      <h2 id="review-queue-title">Review Queue</h2>
      <p>
        Prioritize annotation/item review based on evidence-backed indicators. ERV ranks candidates using frozen, decomposable score components.
      </p>

      <div className="controls" style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <label>
          Prioritization Method
          <select value={selectedMethod} onChange={(e) => setSelectedMethod(e.target.value)}>
            <option value="erv">Experimental Expected Review Value (ERV)</option>
            <option value="highest_entropy">Highest Vote Entropy</option>
            <option value="lowest_consensus_confidence">Lowest Consensus Confidence</option>
            <option value="lowest_worker_reliability">Lowest Worker Reliability (Gold Only)</option>
            <option value="random">Random Permutation</option>
          </select>
        </label>

        <label>
          Review Unit
          <select value={reviewUnit} onChange={(e) => setReviewUnit(e.target.value as "annotation" | "item")}>
            <option value="annotation">Annotation Event (annotation_error_review)</option>
            <option value="item">Item Record (ambiguity_item_routing)</option>
          </select>
        </label>

        <button
          type="button"
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          style={{ alignSelf: "flex-end" }}
        >
          {runMutation.isPending ? "Generating Queue..." : "Generate Review Queue"}
        </button>
      </div>

      <div className="erv-notice" style={{ background: "#f8f9fa", borderLeft: "4px solid #0056b3", padding: "0.75rem", marginBottom: "1rem", fontSize: "0.875rem" }}>
        <strong>Model Notice:</strong> Expected Review Value (ERV) is a decomposable heuristic score (<code>raw_i = 0.60*u_i + 0.20*h_i + 0.20*e_i</code>). It does <em>not</em> represent monetary ROI or calibrated probability of error.
      </div>

      {candidatesQuery.isLoading && <p role="status">Loading review candidates...</p>}
      {candidatesQuery.isError && <p role="alert">Failed to load review candidates.</p>}

      {candidatesQuery.data && candidatesQuery.data.length > 0 && (
        <div className="table-responsive">
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
                <th>Rank</th>
                <th>Item ID</th>
                {reviewUnit === "annotation" && <th>Annotation / Worker</th>}
                {reviewUnit === "annotation" && <th>Submitted Label</th>}
                <th>Method Score</th>
                <th>Score Components Decomposition</th>
                <th>Eligible</th>
              </tr>
            </thead>
            <tbody>
              {candidatesQuery.data.map((c: ReviewCandidate) => {
                const comp = c.score_components || {};
                return (
                  <tr key={c.candidate_id} style={{ borderBottom: "1px solid #eee" }}>
                    <td><strong>#{c.rank}</strong></td>
                    <td><code>{c.item_id}</code></td>
                    {reviewUnit === "annotation" && (
                      <td>
                        <small>{c.annotation_id} ({c.annotator_id})</small>
                      </td>
                    )}
                    {reviewUnit === "annotation" && <td><code>{c.submitted_label || "—"}</code></td>}
                    <td><strong>{c.score.toFixed(4)}</strong></td>
                    <td>
                      {c.prioritization_method === "erv" ? (
                        <span style={{ fontSize: "0.8rem", fontFamily: "monospace" }}>
                          u_i={comp.u_i?.toFixed(3)} | h_i={comp.h_i?.toFixed(3)} | e_i={comp.e_i?.toFixed(3)}
                        </span>
                      ) : (
                        <span style={{ fontSize: "0.8rem" }}>{JSON.stringify(comp)}</span>
                      )}
                    </td>
                    <td>{c.eligible_coverage ? "Yes" : "No"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
