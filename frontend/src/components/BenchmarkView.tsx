import { useQuery } from "@tanstack/react-query";
import React, { useState } from "react";
import { api, BenchmarkManifestResponse } from "../api";

export const BenchmarkView: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<string>("S1");
  const [seeds, setSeeds] = useState<number>(5);

  const benchmarkQuery = useQuery({
    queryKey: ["benchmarkResults", selectedScenario, seeds],
    queryFn: () => api.getBenchmarkResults(selectedScenario, seeds),
  });

  const manifest = benchmarkQuery.data;
  const summary = manifest?.summary;

  return (
    <section className="panel benchmark-research" aria-labelledby="benchmark-title">
      <div className="eyebrow" style={{ color: "#d9534f", fontWeight: "bold" }}>
        SYNTHETIC BENCHMARK RESEARCH
      </div>
      <h2 id="benchmark-title">Simulation & Review Prioritization Benchmark</h2>
      <p>
        Reproducible synthetic benchmark evaluation comparing Expected Review Value (ERV) against Random, Entropy, Consensus Confidence, and Worker Reliability baselines.
      </p>

      <div className="controls" style={{ display: "flex", gap: "1rem", marginBottom: "1rem" }}>
        <label>
          Controlled Scenario
          <select value={selectedScenario} onChange={(e) => setSelectedScenario(e.target.value)}>
            <optgroup label="Development Scenarios (S1–S6)">
              <option value="S1">S1 — Homogeneous Good Workers</option>
              <option value="S2">S2 — Heterogeneous Workers</option>
              <option value="S3">S3 — One/Few Weak Workers</option>
              <option value="S4">S4 — Adversarial Workers</option>
              <option value="S5">S5 — Class-Specific Confusion</option>
              <option value="S6">S6 — Class Imbalance</option>
            </optgroup>
            <optgroup label="Final Evaluation Scenarios (S7–S12)">
              <option value="S7">S7 — Sparse Overlap</option>
              <option value="S8">S8 — Ambiguous Items</option>
              <option value="S9">S9 — Correlated Workers</option>
              <option value="S10">S10 — Low Gold Coverage</option>
              <option value="S11">S11 — Mixed Difficulty</option>
              <option value="S12">S12 — Mixed Realistic World</option>
            </optgroup>
          </select>
        </label>

        <label>
          Multi-Seed Runs
          <select value={seeds} onChange={(e) => setSeeds(Number(e.target.value))}>
            <option value={5}>5 Seeds</option>
            <option value={10}>10 Seeds</option>
          </select>
        </label>
      </div>

      {benchmarkQuery.isLoading && <p role="status">Running synthetic benchmark simulation...</p>}
      {benchmarkQuery.isError && <p role="alert">Failed to load benchmark results.</p>}

      {summary && (
        <div>
          <div className="summary-cards" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
            <div style={{ background: "#f0f4f8", padding: "1rem", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.85rem", color: "#666" }}>Run ID</div>
              <strong>{manifest?.benchmark_run_id}</strong>
            </div>
            <div style={{ background: "#f0f4f8", padding: "1rem", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.85rem", color: "#666" }}>Review Unit</div>
              <strong>{summary.review_unit}</strong>
            </div>
            <div style={{ background: "#f0f4f8", padding: "1rem", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.85rem", color: "#666" }}>Seeds Evaluated</div>
              <strong>{summary.seed_count} seeds</strong>
            </div>
            <div style={{ background: "#f0f4f8", padding: "1rem", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.85rem", color: "#666" }}>ERV Config Hash</div>
              <code style={{ fontSize: "0.75rem" }}>{manifest?.erv_config_hash.slice(0, 12)}...</code>
            </div>
          </div>

          <h3>Multi-Seed Efficiency Metrics (Normalized AUREC@20%)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: "1.5rem" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
                <th>Method</th>
                <th>Mean Normalized AUREC@20%</th>
                <th>Std Dev</th>
                <th>Precision @ 10% Budget</th>
                <th>Recall @ 10% Budget</th>
              </tr>
            </thead>
            <tbody>
              {summary.methods.map((m) => (
                <tr key={m} style={{ borderBottom: "1px solid #eee", fontWeight: m === "erv" ? "bold" : "normal" }}>
                  <td><code>{m}</code> {m === "erv" && "(Target)"}</td>
                  <td>{(summary.method_aurec_means[m] || 0).toFixed(4)}</td>
                  <td>±{(summary.method_aurec_stds[m] || 0).toFixed(4)}</td>
                  <td>{((summary.method_precision_10_means[m] || 0) * 100).toFixed(1)}%</td>
                  <td>{((summary.method_recall_10_means[m] || 0) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>Paired Method Comparisons (Baseline vs ERV)</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid #ccc", textAlign: "left" }}>
                <th>Baseline Method</th>
                <th>Mean Δ AUREC (ERV - Baseline)</th>
                <th>95% Confidence Interval</th>
                <th>Win / Tie / Loss</th>
              </tr>
            </thead>
            <tbody>
              {summary.paired_comparisons.map((pc) => (
                <tr key={pc.baseline_method} style={{ borderBottom: "1px solid #eee" }}>
                  <td><code>{pc.baseline_method}</code></td>
                  <td>{pc.mean_difference >= 0 ? `+${pc.mean_difference.toFixed(4)}` : pc.mean_difference.toFixed(4)}</td>
                  <td>[{pc.ci_lower_95.toFixed(4)}, {pc.ci_upper_95.toFixed(4)}]</td>
                  <td>
                    <span style={{ color: "green", fontWeight: "bold" }}>{pc.win_count}W</span> /{" "}
                    <span style={{ color: "gray" }}>{pc.tie_count}T</span> /{" "}
                    <span style={{ color: "red", fontWeight: "bold" }}>{pc.loss_count}L</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};
