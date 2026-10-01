import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import { api, LabelCollectionPlan } from "../api";
import { LabelCollectionView } from "./LabelCollectionView";

const plan: LabelCollectionPlan = {
  plan_version: "adaptive-collection-1.0.0",
  basis: "dawid_skene_worker_model",
  target_confidence: 0.95,
  max_labels: 7,
  average_annotator_accuracy: 0.82,
  items_total: 3,
  items_returned: 3,
  status_counts: { confident: 1, collect_more: 1, expert_review: 1 },
  labels_collected: 12,
  additional_labels_requested: 2,
  items: [
    { item_id: "item-7", labels_collected: 7, posterior: { a: 0.5, b: 0.5 }, most_likely_label: "a", confidence: 0.5, status: "expert_review", additional_labels: 0 },
    { item_id: "item-2", labels_collected: 3, posterior: { a: 0.8, b: 0.2 }, most_likely_label: "a", confidence: 0.8, status: "collect_more", additional_labels: 2 },
    { item_id: "item-1", labels_collected: 2, posterior: { a: 0.99, b: 0.01 }, most_likely_label: "a", confidence: 0.99, status: "confident", additional_labels: 0 },
  ],
  method: ["Smoothed Dawid-Skene worker confusion matrices; no gold used."],
};

function view() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><LabelCollectionView datasetId="ds_test" /></QueryClientProvider>);
}

test("summarises settled, needs-more and expert items and lists only items needing action", async () => {
  vi.spyOn(api, "labelCollectionPlan").mockResolvedValue(plan);
  view();
  expect(await screen.findByText("Settled — stop labelling")).toBeVisible();
  expect(screen.getByText("2 more")).toBeVisible();
  expect(screen.getByText("Expert")).toBeVisible();
  expect(screen.queryByText("item-1")).toBeNull();
  expect(screen.getByRole("img", { name: /Confidence 80.0% against a 95% target/ })).toBeInTheDocument();
});

test("recomputes the plan when the target confidence changes", async () => {
  const spy = vi.spyOn(api, "labelCollectionPlan").mockResolvedValue(plan);
  view();
  await screen.findByText("Settled — stop labelling");
  fireEvent.change(screen.getByLabelText("Target confidence"), { target: { value: "0.99" } });
  await waitFor(() => expect(spy).toHaveBeenLastCalledWith("ds_test", 0.99, 7));
});
