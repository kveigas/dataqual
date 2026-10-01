import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "./api";
import { configureSnapshot, requestKey, snapshotFor } from "./demoSnapshot";

const demo = {
  schema_version: "4.0.0", dataset_id: "ds_demo", dataset_name: "Synthetic Demo Dataset", dataset_version: "2.0.0",
  project_id: "demo_project", import_id: "imp_1", created_at: "2026-10-01T00:00:00Z", canonical_snapshot_checksum: "abc",
};
const candidates = [
  { candidate_id: "c1", item_id: "item_0001", annotator_id: "w01", eligible_coverage: true, rank: 1 },
  { candidate_id: "c2", item_id: "item_0002", annotator_id: "w02", eligible_coverage: false, rank: 2 },
  { candidate_id: "c3", item_id: "item_0003", annotator_id: "w01", eligible_coverage: true, rank: 3 },
];
const files: Record<string, unknown> = {
  "/snap/manifest.json": {
    snapshot_version: "demo-snapshot-1", generated_at: "2026-10-01T00:00:00Z", demo_dataset: demo,
    entries: { "GET /api/v1/datasets/ds_demo/label-collection-plan?limit=200&max_labels=7&target_confidence=0.95": "plan.json" },
    review_runs: { run_1: "run.json" },
  },
  "/snap/plan.json": { plan_version: "x" },
  "/snap/run.json": candidates,
};

function mockFetch(served: Record<string, unknown>) {
  const fetchMock = vi.fn(async (url: string) => {
    const body = served[url];
    return { ok: body !== undefined, status: body === undefined ? 404 : 200, json: async () => body ?? {} } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  configureSnapshot({ enabled: false });
});

describe("demo snapshot", () => {
  it("builds the same canonical key as the build script", () => {
    expect(requestKey("get", "/api/x?seeds=5&scenario_id=S1")).toBe("GET /api/x?scenario_id=S1&seeds=5");
    expect(requestKey("POST", "/api/x")).toBe("POST /api/x");
  });

  it("answers matching requests from the snapshot whatever the parameter order", async () => {
    mockFetch(files);
    configureSnapshot({ enabled: true, baseUrl: "/snap/" });
    const body = await snapshotFor("GET", "/api/v1/datasets/ds_demo/label-collection-plan?target_confidence=0.95&max_labels=7&limit=200");
    expect(body).toEqual({ plan_version: "x" });
    expect(await snapshotFor("GET", "/api/v1/datasets/other/summary")).toBeUndefined();
  });

  it("pages and searches review runs exactly like the API", async () => {
    mockFetch(files);
    configureSnapshot({ enabled: true, baseUrl: "/snap/" });
    const page = (await snapshotFor("GET", "/api/v1/review-runs/run_1/page?limit=1&offset=1&q=W01&eligible_only=true")) as {
      items: { candidate_id: string }[]; total: number; eligible_total: number;
    };
    expect(page.total).toBe(2);
    expect(page.items.map((c) => c.candidate_id)).toEqual(["c3"]);
    expect(page.eligible_total).toBe(2);
    const slice = await snapshotFor("GET", "/api/v1/review-runs/run_1/candidates?limit=2&offset=1");
    expect((slice as { candidate_id: string }[]).map((c) => c.candidate_id)).toEqual(["c2", "c3"]);
  });

  it("serves the demo dataset instantly without calling the live API", async () => {
    const fetchMock = mockFetch(files);
    configureSnapshot({ enabled: true, baseUrl: "/snap/" });
    const datasets = await api.datasets();
    expect(datasets.map((d) => d.dataset_id)).toEqual(["ds_demo"]);
    expect((await api.bootstrapDemo()).dataset_id).toBe("ds_demo");
    const liveCalls = fetchMock.mock.calls.filter(([url]) => String(url).includes("/api/v1/datasets"));
    expect(liveCalls).toHaveLength(0);
  });

  it("falls back to the live API when no snapshot is deployed", async () => {
    const fetchMock = mockFetch({ "/api/v1/datasets": [demo] });
    configureSnapshot({ enabled: true, baseUrl: "/missing/" });
    expect(await snapshotFor("GET", "/api/v1/datasets/ds_demo/summary")).toBeUndefined();
    const datasets = await api.datasets();
    expect(datasets).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/datasets", undefined);
    expect(await api.liveDatasets()).toEqual([]);
  });
});
