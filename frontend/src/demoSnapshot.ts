// Instant demo: answers the public demo's API requests from static JSON built at deploy time
// (scripts/build_demo_snapshot.py) by the same code that serves the live API. The hosted API
// sleeps when idle; with a snapshot the demo renders immediately and the live API is only
// needed for imports and user datasets.

interface Manifest {
  snapshot_version: string;
  generated_at: string;
  demo_dataset: { dataset_id: string; dataset_name: string; dataset_version: string } & Record<string, unknown>;
  entries: Record<string, string>;
  review_runs: Record<string, string>;
}

interface ReviewCandidateLike {
  eligible_coverage?: boolean;
  [key: string]: unknown;
}

let enabled = import.meta.env.MODE !== "test";
let baseUrl = `${import.meta.env.BASE_URL}demo-snapshot/`;
let manifestPromise: Promise<Manifest | null> | null = null;
const fileCache = new Map<string, Promise<unknown>>();

/** Test hook: turn the snapshot on or off and point it at another location. */
export function configureSnapshot(options: { enabled: boolean; baseUrl?: string }): void {
  enabled = options.enabled;
  if (options.baseUrl) baseUrl = options.baseUrl;
  manifestPromise = null;
  fileCache.clear();
}

/** Canonical request key, identical to request_key() in the build script. */
export function requestKey(method: string, path: string): string {
  const url = new URL(path, "http://snapshot.local");
  const params = [...url.searchParams.entries()].sort(([ak, av], [bk, bv]) =>
    ak < bk ? -1 : ak > bk ? 1 : av < bv ? -1 : av > bv ? 1 : 0,
  );
  const query = new URLSearchParams(params).toString();
  return `${method.toUpperCase()} ${url.pathname}${query ? `?${query}` : ""}`;
}

function loadManifest(): Promise<Manifest | null> {
  if (!enabled) return Promise.resolve(null);
  manifestPromise ??= fetch(`${baseUrl}manifest.json`)
    .then(async (response) => {
      if (!response.ok) return null;
      const body = (await response.json()) as Partial<Manifest>;
      return body && body.entries && body.demo_dataset ? (body as Manifest) : null;
    })
    .catch(() => null);
  return manifestPromise;
}

function loadFile(name: string): Promise<unknown> {
  let cached = fileCache.get(name);
  if (!cached) {
    cached = fetch(`${baseUrl}${name}`).then((response) => {
      if (!response.ok) throw new Error(`Snapshot file missing: ${name}`);
      return response.json() as Promise<unknown>;
    });
    cached.catch(() => fileCache.delete(name));
    fileCache.set(name, cached);
  }
  return cached;
}

/** The demo dataset record, or null when no snapshot is deployed. */
export async function snapshotDemoDataset(): Promise<Manifest["demo_dataset"] | null> {
  return (await loadManifest())?.demo_dataset ?? null;
}

/** A snapshot response for this request, or undefined to use the live API. */
export async function snapshotFor(method: string, path: string): Promise<unknown | undefined> {
  const manifest = await loadManifest();
  if (!manifest) return undefined;
  const url = new URL(path, "http://snapshot.local");

  // Review queues: the build stores each run's full ranking; paging and search are done here
  // exactly as the API does them (see review_page in dataqual/api/app.py).
  const run = /^\/api\/v1\/review-runs\/([^/]+)\/(page|candidates)$/.exec(url.pathname);
  if (run && method.toUpperCase() === "GET" && manifest.review_runs[run[1]]) {
    const candidates = (await loadFile(manifest.review_runs[run[1]])) as ReviewCandidateLike[];
    const number = (key: string, fallback: number) => {
      const value = Number(url.searchParams.get(key));
      return Number.isFinite(value) && url.searchParams.has(key) ? value : fallback;
    };
    if (run[2] === "candidates") {
      const offset = number("offset", 0);
      return candidates.slice(offset, offset + number("limit", 50));
    }
    const limit = number("limit", 20);
    const offset = number("offset", 0);
    const needle = (url.searchParams.get("q") ?? "").trim().toLowerCase();
    const eligibleOnly = url.searchParams.get("eligible_only") === "true";
    const rows = candidates.filter(
      (c) =>
        (!eligibleOnly || c.eligible_coverage) &&
        (!needle ||
          ["item_id", "annotator_id", "annotation_id", "submitted_label"].some((key) =>
            String(c[key] ?? "").toLowerCase().includes(needle),
          )),
    );
    return {
      items: rows.slice(offset, offset + limit),
      total: rows.length,
      offset,
      limit,
      eligible_total: candidates.filter((c) => c.eligible_coverage).length,
    };
  }

  const file = manifest.entries[requestKey(method, `${url.pathname}${url.search}`)];
  return file ? loadFile(file) : undefined;
}

/** Wake the hosted API in the background so imports respond quickly later. */
export function warmUpLiveApi(apiBaseUrl: string): void {
  if (!enabled || !apiBaseUrl) return;
  fetch(`${apiBaseUrl.replace(/\/+$/, "")}/api/v1/health`, { cache: "no-store" }).catch(() => undefined);
}
