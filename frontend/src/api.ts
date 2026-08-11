import { z } from "zod";

const Dataset = z.object({
  schema_version: z.literal("4.0.0"),
  dataset_id: z.string(),
  dataset_name: z.string(),
  dataset_version: z.string(),
  project_id: z.string(),
  import_id: z.string(),
  created_at: z.string(),
  canonical_snapshot_checksum: z.string(),
});

const Summary = z.object({
  schema_version: z.literal("4.0.0"),
  dataset_id: z.string(),
  annotation_events: z.number(),
  current_annotation_events: z.number(),
  unique_items: z.number(),
  unique_annotators: z.number(),
  label_classes: z.number(),
  annotations_by_annotator_top: z.record(z.string(), z.number()),
  annotations_by_item_top: z.record(z.string(), z.number()),
  class_counts: z.record(z.string(), z.number()),
  missing_optional_fields: z.record(z.string(), z.number()),
  gold_items: z.number(),
  gold_coverage: z.number(),
  coannotated_items: z.number(),
});

const Provenance = z.object({
  schema_version: z.literal("4.0.0"),
  dataset_id: z.string(),
  import_id: z.string(),
  project_id: z.string(),
  raw_sha256: z.string(),
  canonical_snapshot_checksum: z.string(),
  schema_version_used: z.string(),
  transformation_version: z.string(),
  input_rows: z.number(),
  accepted_rows: z.number(),
  rejected_rows: z.number(),
  import_timestamp: z.string(),
  original_filename: z.string(),
  source_format: z.string(),
  software_version: z.string(),
  git_commit: z.string().nullable(),
  git_dirty: z.boolean().nullable(),
  artifact_files: z.record(z.string(), z.string()),
  warnings: z.array(z.string()),
});

const ConfidenceInterval = z.object({
  estimate: z.number(), lower: z.number(), upper: z.number(), confidence_level: z.number(),
  replicates: z.number(), valid_replicates: z.number(), failed_replicates: z.number(),
  seed: z.number(), method: z.literal("percentile"), resampling_unit: z.literal("item"),
  population: z.string(),
});

const StatisticalResult = z.object({
  schema_version: z.literal("4.0.0"), metric_name: z.string(), value: z.unknown(),
  status: z.enum(["success", "unresolved", "insufficient_evidence", "assumption_violation", "non_converged", "unavailable", "failed"]),
  evidence_level: z.enum(["minimal", "limited", "adequate", "strong"]),
  support: z.record(z.string(), z.union([z.number(), z.string()])),
  uncertainty: ConfidenceInterval.nullable(), method_identifier: z.string(),
  method_version: z.string(), configuration: z.record(z.string(), z.unknown()),
  configuration_hash: z.string(), warnings: z.array(z.string()), failure_reason: z.string().nullable(),
  provenance: z.object({ analysis_run_id: z.string(), dataset_id: z.string(), dataset_snapshot_id: z.string(), canonical_artifact_checksum: z.string(), method_identifier: z.string(), method_version: z.string(), configuration_hash: z.string(), computed_at: z.string(), software_version: z.string(), git_commit: z.string().nullable(), git_dirty: z.boolean().nullable() }),
});

const Evidence = z.object({
  schema_version: z.literal("4.0.0"), dataset_id: z.string(), analysis_run_id: z.string(),
  annotation_event_count: z.number(), all_annotation_event_count: z.number(),
  superseded_annotation_event_count: z.number(), unique_item_count: z.number(),
  unique_annotator_count: z.number(), class_count: z.number(), gold_item_count: z.number(),
  gold_coverage_fraction: z.number(), mean_annotations_per_item: z.number(),
  median_annotations_per_item: z.number(), min_annotations_per_item: z.number(),
  max_annotations_per_item: z.number(), mean_annotations_per_annotator: z.number(),
  median_annotations_per_annotator: z.number(), coannotated_item_count: z.number(),
  coannotated_item_fraction: z.number(), items_with_1_annotation: z.number(),
  items_with_2_annotations: z.number(), items_with_3plus_annotations: z.number(),
  class_counts: z.record(z.string(), z.number()), class_proportions: z.record(z.string(), z.number()),
  labels_per_item_distribution: z.record(z.string(), z.number()),
  labels_per_annotator_distribution: z.record(z.string(), z.number()),
  evidence_level: z.enum(["minimal", "limited", "adequate", "strong"]),
  provenance: StatisticalResult.shape.provenance,
});

const Pair = z.object({
  annotator_a: z.string(), annotator_b: z.string(), shared_item_count: z.number(),
  agreements: z.number(), disagreements: z.number(), raw_percent_agreement: z.number().nullable(),
  status: StatisticalResult.shape.status, evidence_level: StatisticalResult.shape.evidence_level,
  uncertainty: ConfidenceInterval.nullable(), warnings: z.array(z.string()),
});

const Agreement = z.object({
  schema_version: z.literal("4.0.0"), dataset_id: z.string(), analysis_run_id: z.string(),
  dataset_agreement: StatisticalResult, alpha: StatisticalResult,
  overlap: z.object({
    worker_item_overlap_counts: z.record(z.string(), z.record(z.string(), z.number())),
    graph_node_count: z.number(), graph_edge_count: z.number(), connected_component_count: z.number(),
    largest_component_size: z.number(), isolated_workers: z.array(z.string()),
    isolated_items: z.array(z.string()), worker_degrees: z.record(z.string(), z.number()),
    worker_shared_item_totals: z.record(z.string(), z.number()), pairwise: z.array(Pair),
  }),
});

const ClassMetric = z.object({
  label: z.string(), precision: z.number().nullable(), recall: z.number().nullable(),
  f1: z.number().nullable(), gold_support: z.number(), predicted_support: z.number(),
  true_positive: z.number(), false_positive: z.number(), false_negative: z.number(),
  warnings: z.array(z.string()),
});
const Confusion = z.object({
  labels: z.array(z.string()), row_axis: z.literal("authoritative_gold"),
  column_axis: z.literal("submitted_annotation"), raw_counts: z.array(z.array(z.number())),
  row_normalized: z.array(z.array(z.number().nullable())), support: z.number(),
});
const GoldMetrics = z.object({
  schema_version: z.literal("4.0.0"), dataset_id: z.string(), analysis_run_id: z.string(),
  annotator_id: z.string().nullable(), gold_sources: z.array(z.string()),
  gold_label_record_ids: z.array(z.string()), evaluated_annotation_event_ids: z.array(z.string()),
  excluded_distributional_gold_items: z.number(), excluded_unresolved_gold_items: z.number(),
  accuracy: StatisticalResult, macro_precision: StatisticalResult, macro_recall: StatisticalResult,
  macro_f1: StatisticalResult, micro_precision: StatisticalResult, micro_recall: StatisticalResult,
  micro_f1: StatisticalResult, per_class: z.array(ClassMetric), confusion: Confusion,
});
const AnnotatorEvidence = z.object({
  annotator_id: z.string(), annotation_count: z.number(), items_covered: z.number(),
  gold_items: z.number(), classes_used: z.number(), overlapping_annotators: z.number(),
  gold_accuracy: z.number().nullable(), macro_f1: z.number().nullable(), gold_support: z.number(),
  evidence_level: StatisticalResult.shape.evidence_level,
});
const ConsensusResult = z.object({
  schema_version: z.literal("4.0.0"), result_id: z.string(), analysis_run_id: z.string(),
  dataset_id: z.string(), project_id: z.string(), item_id: z.string(),
  method: z.enum(["majority_vote", "reliability_weighted_vote", "dawid_skene"]),
  method_version: z.string(), status: z.enum(["success", "unresolved", "insufficient_evidence", "non_converged", "failed", "unavailable"]),
  label: z.string().nullable(), probabilities: z.record(z.string(), z.number()),
  vote_counts: z.record(z.string(), z.number()).nullable(), scores: z.record(z.string(), z.number()).nullable(),
  confidence: z.number().nullable(), uncertainty: z.number().nullable(), posterior_entropy: z.number().nullable(),
  support: z.number(), workers_used: z.array(z.string()), excluded_workers: z.record(z.string(), z.string()),
  configuration: z.record(z.string(), z.unknown()), configuration_hash: z.string(),
  provenance: StatisticalResult.shape.provenance, component_id: z.string().nullable(),
  warnings: z.array(z.string()), created_at: z.string(),
});
const WorkerConfusion = z.object({
  annotator_id: z.string(), analysis_run_id: z.string(), method: z.literal("dawid_skene_confusion"),
  labels: z.array(z.string()), row_axis: z.literal("latent_true_class"),
  column_axis: z.literal("worker_emitted_class"), probabilities: z.array(z.array(z.number())),
  support: z.number(), classes_observed: z.array(z.string()), component_id: z.string(), warnings: z.array(z.string()),
});
const Convergence = z.object({
  converged: z.boolean(), iterations: z.number(), stopping_reason: z.string(),
  tolerance_absolute: z.number(), tolerance_relative: z.number(), max_iterations: z.number(),
  initialization_method: z.string(), seed: z.number().nullable(), initial_class_prior: z.record(z.string(), z.number()),
  final_class_prior: z.record(z.string(), z.number()), final_log_likelihood: z.number().nullable(),
  final_delta: z.number().nullable(), log_likelihood_history: z.array(z.number()), monotonicity_tolerance: z.number(),
  component_id: z.string(), items: z.number(), workers: z.number(), annotations: z.number(), observed_classes: z.number(),
});
const ComparisonItem = z.object({
  item_id: z.string(), classification: z.array(z.string()), labels: z.record(z.string(), z.string().nullable()),
  probabilities: z.record(z.string(), z.record(z.string(), z.number())),
  raw_votes: z.array(z.object({ annotator_id: z.string(), label: z.string() })), analysis_run_id: z.string(),
});
const Comparison = z.object({
  analysis_run_id: z.string(), compared_items: z.number(), same_label_all_methods: z.number(),
  mv_vs_ds_disagreement: z.number(), weighted_vs_mv_disagreement: z.number(),
  weighted_vs_ds_disagreement: z.number(), tie_or_unresolved: z.number(), method_dependent_fraction: z.number(),
  items: z.array(ComparisonItem),
});
const ConsensusRun = z.object({
  schema_version: z.literal("4.0.0"), analysis_run_id: z.string(), dataset_id: z.string(), project_id: z.string(),
  canonical_artifact_checksum: z.string(), status: ConsensusResult.shape.status,
  methods: z.array(ConsensusResult.shape.method), configuration: z.record(z.string(), z.unknown()),
  configuration_hash: z.string(), created_at: z.string(), software_version: z.string(),
  git_commit: z.string().nullable(), git_dirty: z.boolean().nullable(), items: z.array(ConsensusResult),
  workers: z.array(WorkerConfusion), convergence: z.array(Convergence), weighted_vote_coverage: z.unknown().nullable(),
  comparison: Comparison, warnings: z.array(z.string()),
});

const ImportRecord = z.object({
  import_id: z.string(),
  status: z.enum(["accepted", "rejected"]),
  dataset_id: z.string().nullable(),
  input_rows: z.number(),
  accepted_rows: z.number(),
  rejected_rows: z.number(),
  duplicate_identical_occurrences: z.number(),
  issues: z.array(z.object({
    source_row_number: z.number().nullable().optional(),
    code: z.string(),
    field: z.string().nullable().optional(),
    message: z.string(),
    fatal: z.boolean().optional(),
  })),
});

export type Dataset = z.infer<typeof Dataset>;
export type Summary = z.infer<typeof Summary>;
export type Provenance = z.infer<typeof Provenance>;
export type ImportRecord = z.infer<typeof ImportRecord>;
export type Evidence = z.infer<typeof Evidence>;
export type Agreement = z.infer<typeof Agreement>;
export type GoldMetrics = z.infer<typeof GoldMetrics>;
export type AnnotatorEvidence = z.infer<typeof AnnotatorEvidence>;
export type ConsensusRun = z.infer<typeof ConsensusRun>;

export interface BetaBinomialEstimate {
  annotator_id: string;
  successes: number;
  failures: number;
  evaluated_gold_items: number;
  posterior_mean: number;
  posterior_median: number;
  lower_bound: number;
  upper_bound: number;
  confidence_level: number;
  prior_alpha: number;
  prior_beta: number;
  prior_source: "leave_one_out_project" | "fallback_symmetric";
  prior_population_n: number;
  prior_mean: number;
  prior_strength: number;
  evidence_status: "strong" | "adequate" | "limited" | "minimal" | "no_gold";
}

export interface DirichletCellInterval {
  true_class: string;
  emitted_label: string;
  raw_count: number;
  smoothed_probability: number;
  marginal_lower_bound: number;
  marginal_upper_bound: number;
  interval_type: "marginal_beta_credible_interval";
}

export interface DirichletConfusionEstimate {
  annotator_id: string;
  labels: string[];
  raw_counts: number[][];
  smoothed_probabilities: number[][];
  cell_intervals: DirichletCellInterval[];
  row_support: Record<string, number>;
  dominant_targets: Record<string, string | null>;
  status: "success" | "limited" | "no_gold";
}

export interface CellDifference {
  true_class: string;
  emitted_label: string;
  gold_observed_probability: number | null;
  ds_estimated_probability: number;
  absolute_difference: number;
}

export interface GoldVsDSComparison {
  annotator_id: string;
  matched_cells: CellDifference[];
  mae: number | null;
  gold_support: number;
  ds_support: number;
  warning: string;
}

export interface AnnotatorCalibration {
  annotator_id: string;
  status: "available" | "not_available";
  observations: number;
  brier_score: number | null;
  ece: number | null;
  bins: Array<{
    bin_index: number;
    lower_bound: number;
    upper_bound: number;
    count: number;
    mean_confidence: number | null;
    accuracy: number | null;
  }>;
  reason?: string | null;
}

export interface AnnotatorProfile {
  annotator_id: string;
  total_annotations: number;
  evaluated_gold_items: number;
  evidence_level: "strong" | "adequate" | "limited" | "minimal";
  beta_binomial?: BetaBinomialEstimate | null;
  dirichlet_confusion?: DirichletConfusionEstimate | null;
  gold_vs_ds?: GoldVsDSComparison | null;
  calibration?: AnnotatorCalibration | null;
}

export interface ItemDisagreementFeatures {
  item_id: string;
  annotation_count: number;
  vote_counts: Record<string, number>;
  vote_proportions: Record<string, number>;
  vote_entropy: number;
  normalized_entropy: number | null;
  vote_margin: number;
  mv_status: string;
  mv_label: string | null;
  ds_status: string;
  ds_probabilities: Record<string, number> | null;
  ds_max_posterior: number | null;
  ds_entropy: number | null;
  method_disagreement: boolean;
  distinct_labels_count: number;
  gold_status: string | null;
  dissenting_worker_ids: string[];
  dissenting_worker_gold_reliabilities: Record<string, number | null>;
}

export interface QualityFlag {
  schema_version: string;
  quality_flag_id: string;
  dataset_snapshot_id: string;
  project_id: string;
  entity_type: "item" | "annotation" | "dataset";
  entity_id: string;
  flag_type: "probable_quality_defect" | "probable_ambiguity_policy_issue" | "mixed_evidence" | "insufficient_evidence" | "no_flag";
  severity: "info" | "low" | "medium" | "high";
  evidence: Record<string, unknown>;
  support_n: number;
  method: string;
  threshold_config_version: string;
  threshold_config_hash: string;
  thresholds_used: Record<string, unknown>;
  uncertainty?: Record<string, unknown> | null;
  recommended_action: "review_annotation" | "review_label" | "clarify_policy" | "collect_more_labels" | "inspect_overlap" | "no_action";
  status: "active" | "resolved" | "superseded";
  created_at: string;
  explanation: string;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";

function getUrl(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  const cleanBase = API_BASE_URL.replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${cleanBase}${cleanPath}`;
}

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const response = await fetch(getUrl(path), init);
  const body: unknown = await response.json();
  if (!response.ok) {
    const message = z.object({ error: z.object({ message: z.string() }) }).safeParse(body);
    throw new Error(message.success ? message.data.error.message : `Request failed (${response.status})`);
  }
  return schema.parse(body);
}

async function rawRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(getUrl(path), init);
  const body: unknown = await response.json();
  if (!response.ok) {
    const message = z.object({ error: z.object({ message: z.string() }) }).safeParse(body);
    throw new Error(message.success ? message.data.error.message : `Request failed (${response.status})`);
  }
  return body as T;
}

export interface ReviewCandidate {
  candidate_id: string;
  review_unit: "annotation" | "item";
  item_id: string;
  annotation_id?: string | null;
  annotator_id?: string | null;
  submitted_label?: string | null;
  prioritization_method: string;
  score: number;
  score_components: {
    u_i?: number;
    h_i?: number;
    e_i?: number;
    raw_score?: number;
    [key: string]: number | undefined;
  };
  rank: number;
  eligible_coverage?: boolean;
  contextual_evidence?: Record<string, unknown>;
  provenance_reference?: string;
}

export interface BenchmarkManifestResponse {
  benchmark_run_id: string;
  generated_at: string;
  scenario_id: string;
  seed_count: number;
  world_seeds: number[];
  random_ranking_seeds: number[];
  erv_config_hash: string;
  methods: string[];
  summary: {
    scenario_id: string;
    review_unit: string;
    seed_count: number;
    methods: string[];
    method_aurec_means: Record<string, number>;
    method_aurec_stds: Record<string, number>;
    method_precision_10_means: Record<string, number>;
    method_recall_10_means: Record<string, number>;
    paired_comparisons: Array<{
      baseline_method: string;
      target_method: string;
      metric_name: string;
      mean_difference: number;
      std_difference: number;
      ci_lower_95: number;
      ci_upper_95: number;
      win_count: number;
      tie_count: number;
      loss_count: number;
    }>;
  };
}

const DemoBootstrapResponse = z.object({
  status: z.string(),
  dataset_id: z.string(),
  dataset_name: z.string(),
  dataset_version: z.string(),
  is_existing: z.boolean().optional(),
  imported_events: z.number().optional(),
  imported_golds: z.number().optional(),
});
export type DemoBootstrapResponse = z.infer<typeof DemoBootstrapResponse>;

export const api = {
  bootstrapDemo: () => request("/api/v1/demo/bootstrap", DemoBootstrapResponse, { method: "POST" }),
  datasets: () => request("/api/v1/datasets", z.array(Dataset)),
  summary: (id: string) => request(`/api/v1/datasets/${encodeURIComponent(id)}/summary`, Summary),
  provenance: (id: string) =>
    request(`/api/v1/datasets/${encodeURIComponent(id)}/provenance`, Provenance),
  evidence: (id: string) => request(`/api/v1/datasets/${encodeURIComponent(id)}/evidence`, Evidence),
  agreement: (id: string) => request(`/api/v1/datasets/${encodeURIComponent(id)}/agreement`, Agreement),
  goldMetrics: (id: string) => request(`/api/v1/datasets/${encodeURIComponent(id)}/gold-metrics`, GoldMetrics),
  annotators: (id: string) => request(`/api/v1/datasets/${encodeURIComponent(id)}/annotators`, z.array(AnnotatorEvidence)),
  annotatorIntelligence: (id: string) =>
    rawRequest<AnnotatorProfile[]>(`/api/v1/datasets/${encodeURIComponent(id)}/annotator-intelligence`),
  qualityFlags: (id: string, flagType?: string, severity?: string, entityType?: string) => {
    const params = new URLSearchParams();
    if (flagType) params.append("flag_type", flagType);
    if (severity) params.append("severity", severity);
    if (entityType) params.append("entity_type", entityType);
    const q = params.toString();
    return rawRequest<QualityFlag[]>(`/api/v1/datasets/${encodeURIComponent(id)}/quality-flags${q ? "?" + q : ""}`);
  },
  itemDiagnostics: (id: string) =>
    rawRequest<ItemDisagreementFeatures[]>(`/api/v1/datasets/${encodeURIComponent(id)}/diagnostics/items`),
  createConsensus: (id: string) => request(
    `/api/v1/datasets/${encodeURIComponent(id)}/consensus/runs`, ConsensusRun,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ methods: ["majority_vote", "dawid_skene"] }) },
  ),
  createReviewRun: (id: string, method = "erv", reviewUnit = "annotation") =>
    rawRequest<{ run_id: string; total_candidates: number }>(
      `/api/v1/datasets/${encodeURIComponent(id)}/review-runs?method=${method}&review_unit=${reviewUnit}`,
      { method: "POST" }
    ),
  getReviewCandidates: (runId: string, limit = 50, offset = 0) =>
    rawRequest<ReviewCandidate[]>(`/api/v1/review-runs/${encodeURIComponent(runId)}/candidates?limit=${limit}&offset=${offset}`),
  getBenchmarkResults: (scenarioId = "S1", seeds = 5) =>
    rawRequest<BenchmarkManifestResponse>(`/api/v1/benchmark/results?scenario_id=${scenarioId}&seeds=${seeds}`),
  importFile: (file: File, config: object) => {
    const form = new FormData();
    form.append("file", file);
    form.append("config_json", JSON.stringify(config));
    return request("/api/v1/imports", ImportRecord, { method: "POST", body: form });
  },
};
