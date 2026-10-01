import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";

import { api, ConsensusRun, Dataset } from "./api";

const defaultConfig = {
  schema_version: "4.0.0", project_id: "demo_project", project_name: "DataQual demo",
  label_domain_id: "sentiment_v1", labels: ["positive", "neutral", "negative"],
  dataset_name: "Synthetic annotation fixture", dataset_version: "1.0.0",
  source_uri: "synthetic://phase2-demo", license: "CC0-1.0", redistribution_allowed: true,
  annotation_source_default: "human",
};

function ImportPanel() {
  const client = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState(JSON.stringify(defaultConfig, null, 2));
  const mutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("Choose a CSV or JSON source file.");
      return api.importFile(file, JSON.parse(config) as object);
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["datasets"] });
      client.invalidateQueries({ queryKey: ["live-datasets"] });
    },
  });
  let configSyntaxValid = true;
  try { JSON.parse(config); } catch { configSyntaxValid = false; }
  function submit(event: FormEvent) { event.preventDefault(); mutation.mutate(); }
  return <section className="panel" aria-labelledby="import-title">
    <div className="eyebrow">Evidence intake</div><h2 id="import-title">Import annotation events</h2>
    <p>CSV and JSON only. Every accepted source is checksummed and retained unchanged.</p>
    <form onSubmit={submit}>
      <label>Source file<input type="file" accept=".csv,.json" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
      <label>Import configuration<textarea rows={14} value={config} onChange={(event) => setConfig(event.target.value)} /></label>
      <div className="preflight" aria-live="polite"><strong>Preflight</strong><span>{file ? `${file.name} · ${file.size} bytes` : "Choose a CSV or JSON source."}</span><span>Configuration JSON: {configSyntaxValid ? "valid syntax" : "invalid syntax"}</span><small>Canonical schema validation runs atomically when submitted.</small></div>
      <button type="submit" disabled={mutation.isPending || !configSyntaxValid}>Import atomically</button>
    </form>
    {mutation.isPending && <p role="status">Importing… If the analysis server was idle, it can take up to a minute to start.</p>}
    {mutation.isError && <p role="alert" className="error">{mutation.error.message}</p>}
    {mutation.data && <div className={`notice ${mutation.data.status}`} role="status"><strong>{mutation.data.status === "accepted" ? "Import accepted" : "Import rejected"}</strong><span>{mutation.data.input_rows} input · {mutation.data.accepted_rows} accepted · {mutation.data.rejected_rows} rejected</span>{mutation.data.issues.map((issue) => <span key={`${issue.code}-${issue.message}`}>{issue.source_row_number ? `Row ${issue.source_row_number} · ` : ""}{issue.field ? `${issue.field} · ` : ""}{issue.code}: {issue.message}</span>)}</div>}
  </section>;
}

function ConsensusPanel({ datasetId }: { datasetId: string }) {
  const [run, setRun] = useState<ConsensusRun | null>(null);
  const mutation = useMutation({ mutationFn: () => api.createConsensus(datasetId), onSuccess: setRun });
  const detail = run?.comparison.items.find((item) => item.classification.some((value) => value.includes("disagreement"))) ?? run?.comparison.items[0];
  const diagnostic = run?.convergence[0];
  const worker = run?.workers[0];
  return <section aria-labelledby="consensus-title"><div className="section-heading"><div><span className="section-kicker">Deterministic / model-estimated · B/C</span><h3 id="consensus-title">Consensus</h3></div>{run && <span className={`evidence-level ${run.status === "success" ? "adequate" : "limited"}`}>{run.status}</span>}</div><p className="method-note">Different consensus assumptions can produce different datasets. Majority Vote is deterministic; Dawid–Skene estimates latent labels under conditional-independence assumptions.</p><button className="secondary-button" type="button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>{mutation.isPending ? "Running consensus…" : "Run Majority Vote + Dawid–Skene"}</button>{mutation.isError && <p role="alert" className="error">Consensus run failed: {mutation.error.message}</p>}{run && <div className="consensus-stack"><div className="result-grid"><article className="result"><span>Methods</span><strong>{run.methods.join(" / ")}</strong><small>Run {run.analysis_run_id}</small></article><article className="result"><span>Compared items</span><strong>{run.comparison.compared_items}</strong><small>{run.comparison.tie_or_unresolved} tie or unresolved</small></article><article className="result"><span>Method-dependent labels</span><strong>{(run.comparison.method_dependent_fraction * 100).toFixed(1)}%</strong><small>{run.comparison.mv_vs_ds_disagreement} MV / DS disagreements</small></article></div>{diagnostic && <article className={`diagnostic ${diagnostic.converged ? "" : "diagnostic-failed"}`}><div className="section-heading"><div><span className="section-kicker">Dawid–Skene diagnostics · C</span><h4>{diagnostic.converged ? "Converged" : "Not converged"}</h4></div><strong>{diagnostic.iterations} iterations</strong></div><dl><div><dt>Stopping reason</dt><dd>{diagnostic.stopping_reason}</dd></div><div><dt>Final log likelihood</dt><dd>{diagnostic.final_log_likelihood?.toFixed(3) ?? "Unavailable"}</dd></div><div><dt>Initialization</dt><dd>{diagnostic.initialization_method}</dd></div><div><dt>Component</dt><dd>{diagnostic.component_id} · {diagnostic.items} items · {diagnostic.workers} workers</dd></div></dl><p>Posterior probabilities are conditional on the model and are not calibrated error probabilities.</p></article>}{detail && <article className="diagnostic"><span className="section-kicker">Item detail · A/B/C</span><h4>{detail.item_id}</h4><div className="split"><div><h5>Raw evidence</h5><dl>{detail.raw_votes.map((vote) => <div key={vote.annotator_id}><dt>{vote.annotator_id}</dt><dd>{vote.label}</dd></div>)}</dl></div><div><h5>Method outputs</h5><dl>{Object.entries(detail.labels).map(([method, label]) => <div key={method}><dt>{method}</dt><dd>{label ?? "Unresolved"}</dd></div>)}</dl></div></div></article>}{worker && <article className="diagnostic"><span className="section-kicker">Statistically estimated · C</span><h4>Model-estimated confusion · {worker.annotator_id}</h4><p>Rows are latent classes; columns are worker-emitted classes. This is not true worker accuracy.</p><div className="table-wrap" tabIndex={0} role="region" aria-label="Model confusion matrix"><table><caption>{worker.support} observed labels · {worker.component_id}</caption><thead><tr><th scope="col">Latent ↓ / emitted →</th>{worker.labels.map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{worker.probabilities.map((row, index) => <tr key={worker.labels[index]}><th scope="row">{worker.labels[index]}</th>{row.map((value, column) => <td key={worker.labels[column]}>{value.toFixed(3)}</td>)}</tr>)}</tbody></table></div></article>}</div>}</section>;
}

import { AnnotatorIntelligenceView } from "./components/AnnotatorIntelligenceView";
import { BenchmarkView } from "./components/BenchmarkView";
import { DisagreementDiagnosticsView } from "./components/DisagreementDiagnosticsView";
import { ReviewQueueView } from "./components/ReviewQueueView";
import { LabelCollectionView } from "./components/LabelCollectionView";

const VIEWS = [
  { id: "overview", label: "Coverage & agreement", hint: "How much evidence exists and how often annotators agree." },
  { id: "collection", label: "Label collection", hint: "Which items are settled, which need more labels, and which need an expert." },
  { id: "consensus", label: "Consensus", hint: "Compare majority vote with the Dawid–Skene model and see where the choice changes the label." },
  { id: "annotators", label: "Annotators", hint: "Reliability against gold, with uncertainty, for each annotator." },
  { id: "diagnostics", label: "Disagreement diagnostics", hint: "Separate probable annotation errors from genuinely ambiguous items." },
  { id: "review_queue", label: "Review queue", hint: "A ranked list of annotations most worth a reviewer’s time." },
  { id: "benchmark", label: "Benchmarks", hint: "How ranking methods compare on synthetic worlds with known truth." },
] as const;
type ViewId = (typeof VIEWS)[number]["id"];

function viewFromHash(): ViewId {
  const value = new URLSearchParams(window.location.hash.slice(1)).get("view");
  return VIEWS.some((view) => view.id === value) ? (value as ViewId) : "overview";
}

function DatasetView({ dataset }: { dataset: Dataset }) {
  const evidence = useQuery({ queryKey: ["evidence", dataset.dataset_id], queryFn: () => api.evidence(dataset.dataset_id) });
  const agreement = useQuery({ queryKey: ["agreement", dataset.dataset_id], queryFn: () => api.agreement(dataset.dataset_id) });
  const gold = useQuery({ queryKey: ["gold", dataset.dataset_id], queryFn: () => api.goldMetrics(dataset.dataset_id) });
  const annotators = useQuery({ queryKey: ["annotators", dataset.dataset_id], queryFn: () => api.annotators(dataset.dataset_id) });
  const provenance = useQuery({ queryKey: ["provenance", dataset.dataset_id], queryFn: () => api.provenance(dataset.dataset_id) });
  const [minimumOverlap, setMinimumOverlap] = useState(1);
  const [showAllPairs, setShowAllPairs] = useState(false);
  const [activeTab, setActiveTabState] = useState<ViewId>(viewFromHash);
  const setActiveTab = (view: ViewId) => {
    setActiveTabState(view);
    window.history.replaceState(null, "", `#view=${view}`);
  };

  if (evidence.isPending || agreement.isPending || gold.isPending || annotators.isPending || provenance.isPending) return <p role="status">Loading dataset evidence…</p>;
  if (evidence.isError || agreement.isError || gold.isError || annotators.isError || provenance.isError) return <p role="alert" className="error">Dataset evidence could not be loaded.</p>;
  const metrics = [
    ["Items", evidence.data.unique_item_count, "Canonical items in this immutable snapshot."],
    ["Current annotations", evidence.data.annotation_event_count, "Current decisions only; superseded events are excluded."],
    ["Annotators", evidence.data.unique_annotator_count, "Distinct canonical annotators."],
    ["Classes", evidence.data.class_count, "Registered labels in immutable domain order."],
    ["Gold coverage", `${(evidence.data.gold_coverage_fraction * 100).toFixed(1)}%`, "Items with resolved hard reference labels."],
    ["Co-annotation", `${(evidence.data.coannotated_item_fraction * 100).toFixed(1)}%`, "Items with at least two current events."],
  ];
  const showValue = (value: unknown) => typeof value === "number" ? value.toFixed(3) : "Unavailable";
  const interval = (result: typeof agreement.data.alpha) => result.uncertainty ? `95% CI ${result.uncertainty.lower.toFixed(3)}–${result.uncertainty.upper.toFixed(3)}` : "CI unavailable";
  const visiblePairs = agreement.data.overlap.pairwise.filter((pair) => pair.shared_item_count >= minimumOverlap);
  const displayedPairs = showAllPairs ? visiblePairs : visiblePairs.slice(0, 10);
  return <div className="dataset-detail">
    <div className="metrics" aria-label="Evidence overview">{metrics.map(([label, value, explanation]) => <div className="metric" key={label} title={String(explanation)}><strong>{value}</strong><span>{label}</span></div>)}</div>
    
    <div className="tabs" role="tablist" aria-label="Dataset views">
      {VIEWS.map((view) => (
        <button
          key={view.id} type="button" role="tab" id={`tab-${view.id}`}
          aria-selected={activeTab === view.id} aria-controls="dataset-panel"
          className={`tab-button ${activeTab === view.id ? "active" : ""}`}
          onClick={() => setActiveTab(view.id)}
        >
          {view.label}
        </button>
      ))}
    </div>
    <p className="view-hint">{VIEWS.find((view) => view.id === activeTab)?.hint}</p>

    <div role="tabpanel" id="dataset-panel" aria-labelledby={`tab-${activeTab}`}>
    {activeTab === "collection" && <LabelCollectionView datasetId={dataset.dataset_id} />}
    {activeTab === "overview" && (
      <>
        <section aria-labelledby="coverage-title"><div className="section-heading"><div><span className="section-kicker">Observed coverage · A</span><h3 id="coverage-title">Coverage and sparsity</h3></div><span className={`evidence-level ${evidence.data.evidence_level}`}>{evidence.data.evidence_level} evidence</span></div><div className="split"><dl><div><dt>Mean labels per item</dt><dd>{evidence.data.mean_annotations_per_item.toFixed(2)}</dd></div><div><dt>Median labels per item</dt><dd>{evidence.data.median_annotations_per_item.toFixed(1)}</dd></div><div><dt>One label</dt><dd>{evidence.data.items_with_1_annotation} items</dd></div><div><dt>Two labels</dt><dd>{evidence.data.items_with_2_annotations} items</dd></div><div><dt>Three or more</dt><dd>{evidence.data.items_with_3plus_annotations} items</dd></div></dl><dl>{Object.entries(evidence.data.class_counts).map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value} · {(evidence.data.class_proportions[label] * 100).toFixed(1)}%</dd></div>)}</dl></div><p className="method-note">This describes observed assignments. It does not assume labels are missing at random.</p></section>
        <section aria-labelledby="agreement-title"><div className="section-heading"><div><span className="section-kicker">Calculated / estimated · B/C</span><h3 id="agreement-title">Agreement</h3></div></div><div className="result-grid"><article className="result"><span>Raw percent agreement</span><strong>{showValue(agreement.data.dataset_agreement.value)}</strong><small>{interval(agreement.data.dataset_agreement)} · {String(agreement.data.dataset_agreement.support.pairable_items)} pairable items</small></article><article className="result"><span>Krippendorff’s Alpha · nominal</span><strong>{showValue(agreement.data.alpha.value)}</strong><small>{interval(agreement.data.alpha)} · {agreement.data.alpha.status}</small></article><article className="result"><span>Overlap graph</span><strong>{agreement.data.overlap.graph_edge_count} edges</strong><small>{agreement.data.overlap.connected_component_count} components · largest {agreement.data.overlap.largest_component_size}</small></article></div><label className="filter">Minimum shared items<input type="number" min="1" value={minimumOverlap} onChange={(event) => setMinimumOverlap(Math.max(1, Number(event.target.value) || 1))} /></label><div className="table-wrap" tabIndex={0} role="region" aria-label="Pairwise agreement table"><table><caption>Pairwise raw agreement on genuinely shared items</caption><thead><tr><th scope="col">Annotator pair</th><th scope="col">Agreement</th><th scope="col">Support</th><th scope="col">Evidence</th></tr></thead><tbody>{displayedPairs.map((pair) => <tr key={`${pair.annotator_a}-${pair.annotator_b}`} className={pair.shared_item_count < 20 ? "low-support" : ""}><th scope="row">{pair.annotator_a} / {pair.annotator_b}</th><td>{pair.raw_percent_agreement === null ? "—" : `${(pair.raw_percent_agreement * 100).toFixed(1)}%`}</td><td>N = {pair.shared_item_count}</td><td>{pair.evidence_level}</td></tr>)}</tbody></table>{visiblePairs.length > 10 && <div style={{ marginTop: "0.75rem", textAlign: "center" }}><button type="button" className="button-secondary" onClick={() => setShowAllPairs(!showAllPairs)} style={{ fontSize: "0.875rem", padding: "0.5rem 1rem", cursor: "pointer", backgroundColor: "#ffffff", color: "#111827", border: "1px solid #d1d5db", borderRadius: "0.375rem", fontWeight: 500 }}>{showAllPairs ? "Show fewer" : `View all ${visiblePairs.length} pairs`}</button></div>}</div></section>
        <section aria-labelledby="gold-title"><div className="section-heading"><div><span className="section-kicker">Hard-gold diagnostics · B/C</span><h3 id="gold-title">Gold performance</h3></div><span className={`evidence-level ${gold.data.accuracy.evidence_level}`}>{gold.data.confusion.support} evaluated events</span></div>{gold.data.confusion.support === 0 ? <p className="method-note">No resolved hard gold supports accuracy or confusion metrics.</p> : <><div className="result-grid">{[["Gold accuracy", gold.data.accuracy], ["Macro precision", gold.data.macro_precision], ["Macro recall", gold.data.macro_recall], ["Macro F1", gold.data.macro_f1]].map(([label, result]) => { const typed = result as typeof gold.data.accuracy; return <article className="result" key={String(label)}><span>{String(label)}</span><strong>{showValue(typed.value)}</strong><small>{interval(typed)}</small></article>; })}</div><div className="table-wrap" tabIndex={0} role="region" aria-label="Gold confusion matrix"><table className="confusion"><caption>Confusion matrix · rows are authoritative gold, columns are submitted annotations · raw counts</caption><thead><tr><th scope="col">Gold ↓ / submitted →</th>{gold.data.confusion.labels.map((label) => <th scope="col" key={label}>{label}</th>)}</tr></thead><tbody>{gold.data.confusion.raw_counts.map((row, index) => <tr key={gold.data.confusion.labels[index]}><th scope="row">{gold.data.confusion.labels[index]}</th>{row.map((count, column) => <td key={gold.data.confusion.labels[column]}>{count}</td>)}</tr>)}</tbody></table></div></>}</section>
      </>
    )}

    {activeTab === "consensus" && <ConsensusPanel datasetId={dataset.dataset_id} />}
    {activeTab === "annotators" && <AnnotatorIntelligenceView datasetId={dataset.dataset_id} />}
    {activeTab === "diagnostics" && <DisagreementDiagnosticsView datasetId={dataset.dataset_id} />}
    {activeTab === "review_queue" && <ReviewQueueView datasetId={dataset.dataset_id} />}
    {activeTab === "benchmark" && <BenchmarkView />}
    </div>

    <section style={{ marginTop: "1.5rem" }}><h3>Provenance</h3><dl className="provenance"><div><dt>Analysis run</dt><dd><code>{evidence.data.analysis_run_id}</code></dd></div><div><dt>Raw SHA-256</dt><dd><code>{provenance.data.raw_sha256}</code></dd></div><div><dt>Canonical SHA-256</dt><dd><code>{provenance.data.canonical_snapshot_checksum}</code></dd></div><div><dt>Transformation</dt><dd>{provenance.data.transformation_version}</dd></div></dl>{provenance.data.warnings.map((warning) => <p className="warning" key={warning}>{warning}</p>)}</section>
    <p className="scope-note">Prioritization scores and synthetic benchmark evaluations remain conditional on evidence and method assumptions.</p>
  </div>;
}

function Workspace() {
  const queryClient = useQueryClient();
  const primary = useQuery({ queryKey: ["datasets"], queryFn: api.datasets });
  // The instant demo renders first; user datasets join once the live API answers.
  const live = useQuery({ queryKey: ["live-datasets"], queryFn: api.liveDatasets, retry: 4, retryDelay: 15000 });
  const datasets = {
    ...primary,
    data: primary.data && [...primary.data, ...(live.data ?? []).filter((d) => !primary.data.some((p) => p.dataset_id === d.dataset_id))],
  };
  const [selected, setSelected] = useState<string | null>(null);

  const demoMutation = useMutation({
    mutationFn: api.bootstrapDemo,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["datasets"] });
      queryClient.invalidateQueries({ queryKey: ["live-datasets"] });
      setSelected(data.dataset_id);
    },
  });

  const chosen = datasets.data?.find((dataset) => dataset.dataset_id === selected) ?? datasets.data?.[0];
  const isDemo = chosen?.dataset_name === "Synthetic Demo Dataset";

  return (
    <section className="panel workspace" aria-labelledby="workspace-title">
      <div className="eyebrow">Canonical evidence</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <h2 id="workspace-title" style={{ margin: 0 }}>Datasets</h2>
        {isDemo && (
          <span
            className="demo-badge"
            style={{
              backgroundColor: "#eff6ff",
              color: "#1e40af",
              padding: "0.25rem 0.75rem",
              borderRadius: "9999px",
              fontSize: "0.875rem",
              fontWeight: 600,
              border: "1px solid #bfdbfe",
            }}
          >
            SYNTHETIC DEMO DATA
          </span>
        )}
      </div>

      {datasets.isPending && <p role="status">Loading datasets…</p>}
      {datasets.isError && <p role="alert" className="error">Datasets could not be loaded.</p>}

      {datasets.data?.length === 0 && (
        <div style={{ padding: "1.5rem", backgroundColor: "#f9fafb", borderRadius: "0.5rem", border: "1px solid #e5e7eb", textAlign: "center", marginBottom: "1.5rem" }}>
          <h3 style={{ marginTop: 0, marginBottom: "0.5rem", color: "#111827" }}>No Canonical Datasets Yet</h3>
          <p style={{ color: "#374151", marginBottom: "1rem" }}>
            Explore DataQual's evidence engine using a deterministic synthetic dataset, or upload your own CSV/JSON annotation events.
          </p>

          {demoMutation.isPending ? (
            <p role="status" style={{ fontWeight: 600, color: "#2563eb" }}>
              Starting DataQual demo environment…
            </p>
          ) : demoMutation.isError ? (
            <div>
              <p role="alert" className="error" style={{ color: "#dc2626", marginBottom: "0.75rem" }}>
                Demo environment start failed: {demoMutation.error.message}
              </p>
              <button
                type="button"
                className="button-primary"
                onClick={() => demoMutation.mutate()}
                style={{ backgroundColor: "#2563eb", color: "#ffffff", padding: "0.5rem 1rem", borderRadius: "0.375rem", border: "none", cursor: "pointer" }}
              >
                Retry Demo Bootstrap
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="button-primary"
              onClick={() => demoMutation.mutate()}
              style={{ backgroundColor: "#2563eb", color: "#ffffff", padding: "0.625rem 1.25rem", fontWeight: 600, borderRadius: "0.375rem", border: "none", cursor: "pointer" }}
            >
              Explore Demo Dataset
            </button>
          )}
        </div>
      )}

      {(datasets.data?.length ?? 0) > 0 && (
        <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem" }}>
          <label style={{ flex: 1 }}>
            Dataset
            <select
              value={chosen?.dataset_id}
              onChange={(event) => setSelected(event.target.value)}
            >
              {datasets.data?.map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.dataset_name} · {dataset.dataset_version}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className="button-secondary"
            onClick={() => demoMutation.mutate()}
            disabled={demoMutation.isPending}
            style={{ fontSize: "0.875rem", padding: "0.375rem 0.75rem" }}
          >
            {demoMutation.isPending ? "Loading Demo…" : "Load Synthetic Demo"}
          </button>
        </div>
      )}

      {chosen && <DatasetView key={chosen.dataset_id} dataset={chosen} />}
    </section>
  );
}

export function App() {
  return <><a className="skip-link" href="#main">Skip to workspace</a><header><div><span className="mark">DQ</span><strong>DataQual v4</strong></div><span className="phase">Annotation evidence workspace</span></header><main id="main"><section className="intro"><div className="eyebrow">Research-grade annotation evidence</div><h1>Evidence before quality claims.</h1><p>DataQual traces coverage, agreement, consensus sensitivity, annotator intelligence, and review prioritization back to immutable annotation events.</p></section><div className="layout"><details className="intake-disclosure"><summary>Import your annotation data <span>CSV / JSON · checksummed evidence</span></summary><ImportPanel /></details><Workspace /></div></main><footer>DataQual v4 · Review prioritization and synthetic benchmarking remain conditional on evidence and method assumptions.</footer></>;
}
