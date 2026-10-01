import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { api } from "../api";
import { ReviewQueueView } from "./ReviewQueueView";

function view() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><ReviewQueueView datasetId="ds_test" /></QueryClientProvider>);
}

test("keeps run identity when draft settings change and supports paging all candidates", async () => {
  vi.spyOn(api, "createReviewRun").mockResolvedValue({ run_id: "run-1", dataset_id: "ds_test", method: "erv", review_unit: "annotation", total_candidates: 25, created_at: "2026-09-29", ranking_version: "2", canonical_snapshot_checksum: "a".repeat(64) });
  const page = vi.spyOn(api, "getReviewPage").mockResolvedValue({ total: 25, eligible_total: 25, items: [{ candidate_id: "c1", item_id: "item-1", review_unit: "annotation", annotator_id: "worker-1", prioritization_method: "erv", score: 0.3, rank: 1, eligible_coverage: true, score_components: { u_i: 0.2 }, contextual_evidence: { vote_counts: { yes: 2, no: 1 }, ds_status: "success" } }] });
  view();
  fireEvent.click(screen.getByRole("button", { name: "Generate Review Queue" }));
  expect(await screen.findByText("Why this candidate?")).toBeVisible();
  fireEvent.change(screen.getByLabelText("Review unit"), { target: { value: "item" } });
  expect(screen.getByText(/Settings changed/)).toBeVisible();
  expect(screen.getByText("Worker / label")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Next" }));
  await waitFor(() => expect(page).toHaveBeenLastCalledWith("run-1", 20, "", false));
});

test("reports generation failures instead of silently showing an empty queue", async () => {
  vi.spyOn(api, "createReviewRun").mockRejectedValue(new Error("backend unavailable"));
  view();
  fireEvent.click(screen.getByRole("button", { name: "Generate Review Queue" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("backend unavailable");
});
