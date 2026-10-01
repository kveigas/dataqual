import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, ReviewCandidate, ReviewRun } from "../api";

const methods: Record<string, string> = {
  erv: "Experimental review value",
  highest_entropy: "Vote entropy",
  lowest_consensus_confidence: "Model uncertainty",
  lowest_worker_reliability: "Worker reliability · gold evidence",
  random: "Random baseline",
};

function EvidenceDetail({ candidate }: { candidate: ReviewCandidate }) {
  const evidence = candidate.contextual_evidence ?? {};
  const votes = (evidence.vote_counts ?? {}) as Record<string, number>;
  const support = (evidence.worker_gold_support ?? {}) as Record<string, number>;
  const componentNames: Record<string, string> = { u_i: "Model uncertainty (× 0.60)", h_i: "Vote entropy (× 0.20)", e_i: "Worker error exposure (× 0.20)", raw_score: "Combined heuristic" };
  return <aside className="review-detail" aria-label="Selected candidate evidence">
    <span className="section-kicker">Why this candidate?</span>
    <h3>{candidate.item_id}</h3>
    <p>Rank {candidate.rank} · {candidate.review_unit === "annotation" ? candidate.annotator_id : "Item-level review"}</p>
    <div className="notice"><strong>{candidate.eligible_coverage ? "Evidence available" : "Incomplete model evidence"}</strong>
      <span>{candidate.eligible_coverage ? "Ranking is a triage aid, not a verdict." : "Do not interpret a fallback score as confidence. Collect evidence or inspect the model fit."}</span></div>
    <h4>Observed label distribution</h4>
    {Object.entries(votes).map(([label, count]) => <div className="evidence-bar" key={label}>
      <span>{label}</span><meter min={0} max={Math.max(1, ...Object.values(votes))} value={count} aria-label={`${label} votes`} /><strong>{count}</strong>
    </div>)}
    <h4>Score breakdown</h4>
    <dl>{Object.entries(candidate.score_components).map(([key, value]) => <div key={key}>
      <dt>{componentNames[key] ?? key.replaceAll("_", " ")}</dt><dd>{value?.toFixed(4) ?? "Unavailable"}</dd>
    </div>)}</dl>
    <p className="method-note">DS fit: {String(evidence.ds_status ?? "unavailable")}. Missing worker gold uses the documented 0.50 prior, not measured error.</p>
    <details><summary>Worker gold support</summary><dl>{Object.entries(support).map(([worker, count]) => <div key={worker}><dt>{worker}</dt><dd>{count} observations</dd></div>)}</dl></details>
    <p>Disagreement can reflect legitimate perspectives or unclear policy. Inspect the source and guidelines before changing a label.</p>
  </aside>;
}

export function ReviewQueueView({ datasetId }: { datasetId: string }) {
  const [method, setMethod] = useState("erv");
  const [unit, setUnit] = useState<"annotation" | "item">("annotation");
  const [run, setRun] = useState<ReviewRun | null>(null);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [eligible, setEligible] = useState(false);
  const [selected, setSelected] = useState<ReviewCandidate | null>(null);
  const mutation = useMutation({
    mutationFn: () => api.createReviewRun(datasetId, method, unit),
    onSuccess: (result) => { setRun(result); setOffset(0); setSelected(null); setQuery(""); setSearch(""); },
  });
  const page = useQuery({
    queryKey: ["review-page", datasetId, run?.run_id, offset, query, eligible],
    queryFn: () => api.getReviewPage(run!.run_id, offset, query, eligible),
    enabled: run !== null,
  });
  const active = selected ?? page.data?.items[0];
  return <section className="review-queue" aria-labelledby="review-queue-title">
    <div className="section-heading"><div><span className="section-kicker">Evidence → triage → human judgment</span><h2 id="review-queue-title">Review workspace</h2></div><span className="evidence-level">Experimental ranking</span></div>
    <p>Choose what to review, then inspect the evidence behind each rank. No labels are changed automatically.</p>
    <div className="review-controls">
      <label>Prioritization method<select value={method} onChange={e => setMethod(e.target.value)}>{Object.entries(methods).map(([key, name]) => <option value={key} key={key}>{name}</option>)}</select></label>
      <label>Review unit<select value={unit} onChange={e => setUnit(e.target.value as "annotation" | "item")}><option value="annotation">Individual annotations</option><option value="item">Whole items / policy ambiguity</option></select></label>
      <button disabled={mutation.isPending} onClick={() => mutation.mutate()}>{mutation.isPending ? "Building evidence…" : "Generate Review Queue"}</button>
    </div>
    <p className="method-note">ERV = 0.60 × model uncertainty + 0.20 × vote entropy + 0.20 × worker error exposure. It is not a calibrated error probability or financial return.</p>
    {mutation.isError && <p role="alert" className="error">Queue generation failed: {mutation.error.message}. Your previous run is preserved; retry when ready.</p>}
    {!run && !mutation.isPending && <div className="review-empty"><h3>Start with a review question</h3><p>Use annotation review for individual labels, or item review to investigate ambiguity. Every generated run preserves its input checksum and ranking settings.</p></div>}
    {run && <>
      <div className="review-run"><strong>{methods[run.method]} · {run.review_unit} review</strong><span>{run.total_candidates} candidates · {run.ranking_version}</span></div>
      {(run.method !== method || run.review_unit !== unit) && <p role="status" className="warning">Settings changed. Generate a new queue to apply them; the results below still belong to the previous run.</p>}
      <form className="review-search" onSubmit={e => { e.preventDefault(); setQuery(search); setOffset(0); setSelected(null); }}>
        <label>Find item, worker, or label<input value={search} onChange={e => setSearch(e.target.value)} maxLength={200} placeholder="Search all candidates" /></label><button className="quiet-button">Search</button>
        <label className="checkbox-label"><input type="checkbox" checked={eligible} onChange={e => { setEligible(e.target.checked); setOffset(0); setSelected(null); }} /> Evidence available only</label>
      </form>
      {page.isFetching && <p role="status">Loading candidates…</p>}
      {page.isError && <div role="alert" className="error">Unable to load this page. <button onClick={() => page.refetch()}>Retry</button></div>}
      {page.data && <>
        <p className="queue-count" role="status">{page.data.total} matching · {page.data.eligible_total} with model/method evidence across this run</p>
        {!page.data.items.length ? <p>No candidates match. Clear your search or evidence filter.</p> : <div className="review-layout">
          <div className="table-wrap" tabIndex={0} aria-label="Ranked review candidates"><table><caption>Ranked candidates · select an item to inspect its evidence</caption><thead><tr><th>Rank / item</th><th>{run.review_unit === "annotation" ? "Worker / label" : "Review unit"}</th><th>Score</th></tr></thead><tbody>{page.data.items.map(c => <tr key={c.candidate_id} className={active?.candidate_id === c.candidate_id ? "selected-row" : ""}>
            <td><button className="candidate-button" aria-pressed={active?.candidate_id === c.candidate_id} onClick={() => setSelected(c)}>#{c.rank} · {c.item_id}</button>{!c.eligible_coverage && <small className="warning">Limited evidence</small>}</td>
            <td>{run.review_unit === "annotation" ? <>{c.annotator_id}<small>{c.submitted_label}</small></> : "Whole item"}</td><td>{c.score.toFixed(3)}</td>
          </tr>)}</tbody></table></div>
          {active && <EvidenceDetail candidate={active} />}
        </div>}
        <nav className="queue-pagination" aria-label="Review queue pages"><button className="quiet-button" disabled={offset === 0 || page.isFetching} onClick={() => { setOffset(Math.max(0, offset - 20)); setSelected(null); }}>Previous</button><span>{page.data.total ? `${offset + 1}–${Math.min(offset + 20, page.data.total)} of ${page.data.total}` : "0 results"}</span><button className="quiet-button" disabled={offset + 20 >= page.data.total || page.isFetching} onClick={() => { setOffset(offset + 20); setSelected(null); }}>Next</button></nav>
      </>}
      <details className="run-provenance"><summary>Run provenance</summary><p>Run: <code>{run.run_id}</code></p><p>Snapshot SHA-256: <code>{run.canonical_snapshot_checksum}</code></p><p>Created: {run.created_at}</p></details>
    </>}
  </section>;
}
