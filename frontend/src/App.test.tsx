import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { App } from "./App";

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
}

test("explains the truthful scope and empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify([]), { status: 200 }));
  renderApp();
  expect(screen.getByRole("heading", { name: "Evidence before quality claims." })).toBeVisible();
  expect(screen.getByText(/remain conditional on evidence/i)).toBeVisible();
  await waitFor(() => expect(screen.getByText(/No canonical datasets yet/i)).toBeVisible());
});

test("shows a structured loading failure", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ error: { message: "offline" } }), { status: 503 }));
  renderApp();
  await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Datasets could not be loaded"));
});

test("submits a source and reports a successful atomic import", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => init?.method === "POST"
    ? new Response(JSON.stringify({ import_id: "imp_1", status: "accepted", dataset_id: "ds_1", input_rows: 3, accepted_rows: 3, rejected_rows: 0, duplicate_identical_occurrences: 0, issues: [] }), { status: 200 })
    : new Response(JSON.stringify([]), { status: 200 }));
  renderApp();
  fireEvent.change(screen.getByLabelText("Source file"), { target: { files: [new File(["a"], "events.csv", { type: "text/csv" })] } });
  fireEvent.click(screen.getByRole("button", { name: "Import atomically" }));
  await waitFor(() => expect(screen.getByText("Import accepted")).toBeVisible());
  expect(screen.getByText(/3 input · 3 accepted · 0 rejected/)).toBeVisible();
});

test("renders validation rejection without inventing partial success", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => init?.method === "POST"
    ? new Response(JSON.stringify({ import_id: "imp_2", status: "rejected", dataset_id: null, input_rows: 2, accepted_rows: 0, rejected_rows: 2, duplicate_identical_occurrences: 0, issues: [{ code: "duplicate_annotation_id_conflict", message: "conflicting event" }] }), { status: 200 })
    : new Response(JSON.stringify([]), { status: 200 }));
  renderApp();
  fireEvent.change(screen.getByLabelText("Source file"), { target: { files: [new File(["bad"], "bad.csv")] } });
  fireEvent.click(screen.getByRole("button", { name: "Import atomically" }));
  await waitFor(() => expect(screen.getByText("Import rejected")).toBeVisible());
  expect(screen.getByText(/duplicate_annotation_id_conflict/)).toBeVisible();
});

const provenance = { analysis_run_id: "analysis_1", dataset_id: "ds_1", dataset_snapshot_id: "ds_1", canonical_artifact_checksum: "b".repeat(64), method_identifier: "method", method_version: "1", configuration_hash: "c".repeat(64), computed_at: "2026-01-01T00:00:00Z", software_version: "0.1.0", git_commit: null, git_dirty: null };
function result(metric: string, value: number) {
  return { schema_version: "4.0.0", metric_name: metric, value, status: "success", evidence_level: "limited", support: { pairable_items: 3 }, uncertainty: null, method_identifier: metric, method_version: "1", configuration: {}, configuration_hash: "c".repeat(64), provenance, warnings: ["fewer_than_10_eligible_items"], failure_reason: null };
}

test("shows evidence, support, agreement, gold diagnostics, and provenance", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path.endsWith("/evidence")) return new Response(JSON.stringify({ schema_version: "4.0.0", dataset_id: "ds_1", analysis_run_id: "analysis_1", annotation_event_count: 8, all_annotation_event_count: 9, superseded_annotation_event_count: 1, unique_item_count: 4, unique_annotator_count: 3, class_count: 3, gold_item_count: 2, gold_coverage_fraction: .5, mean_annotations_per_item: 2, median_annotations_per_item: 2, min_annotations_per_item: 1, max_annotations_per_item: 3, mean_annotations_per_annotator: 2.67, median_annotations_per_annotator: 3, coannotated_item_count: 3, coannotated_item_fraction: .75, items_with_1_annotation: 1, items_with_2_annotations: 2, items_with_3plus_annotations: 1, class_counts: { positive: 1, neutral: 4, negative: 3 }, class_proportions: { positive: .125, neutral: .5, negative: .375 }, labels_per_item_distribution: { "1": 1, "2": 2, "3": 1 }, labels_per_annotator_distribution: { "2": 1, "3": 2 }, evidence_level: "limited", provenance }), { status: 200 });
    if (path.endsWith("/agreement")) return new Response(JSON.stringify({ schema_version: "4.0.0", dataset_id: "ds_1", analysis_run_id: "analysis_1", dataset_agreement: result("raw", .4), alpha: result("alpha", .2), overlap: { worker_item_overlap_counts: {}, graph_node_count: 3, graph_edge_count: 2, connected_component_count: 1, largest_component_size: 3, isolated_workers: [], isolated_items: ["i4"], worker_degrees: { w1: 2 }, worker_shared_item_totals: { w1: 3 }, pairwise: [{ annotator_a: "w1", annotator_b: "w2", shared_item_count: 2, agreements: 1, disagreements: 1, raw_percent_agreement: .5, status: "success", evidence_level: "limited", uncertainty: null, warnings: ["small"] }] } }), { status: 200 });
    if (path.endsWith("/gold-metrics")) { const metric = result("gold", .75); return new Response(JSON.stringify({ schema_version: "4.0.0", dataset_id: "ds_1", analysis_run_id: "analysis_1", annotator_id: null, gold_sources: ["trusted_reference"], gold_label_record_ids: ["g1"], evaluated_annotation_event_ids: ["a1", "a2"], excluded_distributional_gold_items: 0, excluded_unresolved_gold_items: 0, accuracy: metric, macro_precision: metric, macro_recall: metric, macro_f1: metric, micro_precision: metric, micro_recall: metric, micro_f1: metric, per_class: [], confusion: { labels: ["positive", "neutral", "negative"], row_axis: "authoritative_gold", column_axis: "submitted_annotation", raw_counts: [[1,0,0],[0,1,0],[0,0,0]], row_normalized: [[1,0,0],[0,1,0],[null,null,null]], support: 2 } }), { status: 200 }); }
    if (path.endsWith("/annotators")) return new Response(JSON.stringify([{ annotator_id: "w1", annotation_count: 3, items_covered: 3, gold_items: 2, classes_used: 2, overlapping_annotators: 2, gold_accuracy: .5, macro_f1: .4, gold_support: 2, evidence_level: "limited" }]), { status: 200 });
    if (path.endsWith("/provenance")) return new Response(JSON.stringify({ schema_version: "4.0.0", dataset_id: "ds_1", import_id: "imp_1", project_id: "p", raw_sha256: "a".repeat(64), canonical_snapshot_checksum: "b".repeat(64), schema_version_used: "4.0.0", transformation_version: "phase1-canonical-1.0.0", input_rows: 9, accepted_rows: 9, rejected_rows: 0, import_timestamp: "2026-01-01T00:00:00Z", original_filename: "events.csv", source_format: "csv", software_version: "0.1.0", git_commit: null, git_dirty: null, artifact_files: {}, warnings: [] }), { status: 200 });
    return new Response(JSON.stringify([{ schema_version: "4.0.0", dataset_id: "ds_1", dataset_name: "Demo", dataset_version: "1", project_id: "p", import_id: "imp_1", created_at: "2026-01-01T00:00:00Z", canonical_snapshot_checksum: "b".repeat(64) }]), { status: 200 });
  });
  renderApp();
  await waitFor(() => expect(screen.getByRole("heading", { name: "Agreement" })).toBeVisible());
  expect(screen.getByText("N = 2")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Gold performance" })).toBeVisible();
  expect(screen.getByText(/rows are authoritative gold/i)).toBeVisible();
  expect(screen.getByText("analysis_1")).toBeVisible();
});
