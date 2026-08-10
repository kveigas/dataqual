# DataQual v4 Canonical Data Model

Status: implementation contract  
Schema family: `dataqual.v4.core`  
Initial schema version: `4.0.0`

## 1. Conventions

- IDs are UTF-8 strings, 1–128 characters, unique within the stated scope, and must not contain control characters.
- System-generated IDs use UUIDv7 when available; imported stable IDs may be retained after validation.
- Timestamps are RFC 3339 UTC strings ending in `Z`. Inputs with explicit offsets are converted to UTC while the raw value remains in the immutable import.
- NaN, positive infinity, and negative infinity are invalid serialized values.
- Optional means the field may be absent. `null` is accepted only where this document explicitly permits it.
- Empty strings are never treated as missing. They are invalid unless a field explicitly allows them.
- Arbitrary metadata must be a JSON object with string keys and a serialized size of at most 64 KiB per row.
- All canonical records include `schema_version` and provenance identifiers.
- Labels are case-sensitive opaque strings after Unicode NFC normalization. Display aliases do not change canonical labels.

## 2. Project

| Field | Type | Req. | Constraints and semantics | Provenance / missing behavior |
|---|---|---:|---|---|
| `schema_version` | string | yes | Must be supported semver, initially `4.0.0`. | System assigned; never inferred from row shape. |
| `project_id` | string | yes | Globally unique in one installation. | Imported or system generated. |
| `name` | string | yes | 1–200 visible characters. | User supplied. |
| `description` | string | no | Maximum 4,000 characters. | Missing means no description. |
| `annotation_type` | enum | yes | Core value must be `categorical_single_label`. | User supplied and validated. |
| `label_domain_id` | string | yes | Must reference a registered label domain. | Cannot be missing after project creation. |
| `default_timezone` | string | no | Valid IANA timezone; display/import assistance only. | Missing defaults to UTC; canonical timestamps remain UTC. |
| `created_at` | timestamp | yes | UTC. | System generated. |
| `metadata_json` | object | no | No secrets or raw item payloads. | Missing becomes `{}`. |

## 3. Label-domain registry

A label domain is immutable after annotations reference it.

| Field | Type | Req. | Constraints and semantics |
|---|---|---:|---|
| `label_domain_id` | string | yes | Unique ID. |
| `project_id` | string | yes | Owning project. |
| `version` | integer | yes | Starts at 1 and increases for a changed taxonomy. |
| `labels` | ordered array[string] | yes | 2–100 unique canonical labels. Order is authoritative for matrices and probabilities. |
| `display_names` | object | no | Canonical label to display string. |
| `created_at` | timestamp | yes | UTC. |
| `supersedes_label_domain_id` | string | no | References prior domain when taxonomy changes. |

Adding, removing, merging, or renaming a canonical label creates a new domain and a new analytical dataset snapshot. Existing events are never silently relabeled.

## 4. Item

| Field | Type | Req. | Constraints and semantics | Provenance / missing behavior |
|---|---|---:|---|---|
| `schema_version` | string | yes | Supported schema version. | System/import. |
| `project_id` | string | yes | Must reference Project. | Import relation. |
| `item_id` | string | yes | Unique within project. | Source ID is preferred. |
| `label_domain_id` | string | yes | Domain applicable when item was annotated. | Must match accepted annotation events. |
| `content_ref` | string | no | URI/path/opaque external reference; DataQual need not store content. | Missing means content is unavailable in UI. |
| `task_family` | string | no | Maximum 128 characters. | Missing is an explicit unknown group. |
| `severity_weight` | number | no | Finite, `0 < value <= 100`; default `1.0`. | User/source supplied; never inferred from class. |
| `expected_review_cost` | number | no | Finite positive relative cost; default `1.0`. | Missing uses documented default and emits provenance. |
| `metadata_json` | object | no | Non-sensitive item metadata. | Missing becomes `{}`. |
| `source_import_id` | string | yes | Import that introduced the item. | System assigned. |

Items do not contain a mutable `gold_label` field. Gold labels are versioned records.

## 5. AnnotationEvent

The annotation event is the primary analytical fact.

| Field | Type | Req. | Constraints and semantics | Provenance / missing behavior |
|---|---|---:|---|---|
| `schema_version` | string | yes | Supported version. | System/import. |
| `annotation_id` | string | yes | Globally unique and immutable. | Source ID or system UUID. |
| `project_id` | string | yes | Must reference Project. | Required relation. |
| `item_id` | string | yes | Must reference Item in project. | Required relation. |
| `annotator_id` | string | yes | Must reference Annotator in project. | Required relation. |
| `label_domain_id` | string | yes | Must match Item/domain version. | Required relation. |
| `label` | string | yes | Must exactly match a canonical label. | Missing/null/empty is invalid, not abstention. |
| `event_version` | integer | yes | Positive; normally 1. | Increases only through explicit reannotation. |
| `supersedes_annotation_id` | string | no | Prior event for the same item/annotator. | Required when `event_version > 1`. |
| `is_current` | boolean | yes | Exactly one current event per item/annotator/domain. | Derived during snapshot creation, not trusted from input. |
| `timestamp` | timestamp | no | UTC when known. | Missing is allowed but excludes event from future temporal analyses. |
| `confidence` | number | no | Finite in `[0,1]`; semantic is confidence in submitted label. | Missing means unobserved, never `0`. |
| `duration_ms` | integer | no | `0 <= value <= 86,400,000`. | Missing means unobserved. Zero is retained. |
| `annotation_source` | enum | yes | `human`, `ai_assisted`, `model`, or `gold_import`; core human analysis normally uses first two. | Defaults to `human` only when importer configuration explicitly declares that default. |
| `ai_suggestion` | string | no | Registered label. Allowed only for `ai_assisted`. | Missing means no recorded suggestion. |
| `ai_confidence` | number | no | Finite in `[0,1]`; allowed only with `ai_suggestion`. | Missing means unavailable. |
| `metadata_json` | object | no | Event metadata. | Missing becomes `{}`. |
| `source_import_id` | string | yes | Raw import provenance. | System assigned. |
| `source_row_number` | integer | yes | One-based row/object index. | System assigned. |

An abstention is not represented by a null label. If a project needs abstention as an analyzed category, `ABSTAIN` must be registered as a canonical label and its semantics documented.

## 6. Annotator

| Field | Type | Req. | Constraints and semantics | Provenance / missing behavior |
|---|---|---:|---|---|
| `schema_version` | string | yes | Supported version. | System/import. |
| `project_id` | string | yes | Project membership. | Required relation. |
| `annotator_id` | string | yes | Unique within project. | Source ID preferred. |
| `role` | string | no | Operational role; not used as a reliability prior in core. | Missing means unknown. |
| `team` | string | no | Operational group. | Missing means unknown. |
| `tenure_start` | date | no | ISO date. | Missing means unknown. |
| `language` | string | no | Optional operational metadata. | Missing means unknown. |
| `specialty` | string | no | Optional operational metadata. | Missing means unknown. |
| `active` | boolean | no | Operational state; default true at import. | Does not remove historical events. |
| `metadata_json` | object | no | Sensitive metadata prohibited in core demo. | Missing becomes `{}`. |
| `source_import_id` | string | yes | Record provenance. | System assigned. |

Email, pay rate, legal name, and demographic attributes are not canonical analytical fields. They may be stored only in a separately governed application profile store and must not enter benchmark artifacts.

## 7. GoldLabel

| Field | Type | Req. | Constraints and semantics | Provenance / missing behavior |
|---|---|---:|---|---|
| `schema_version` | string | yes | Supported version. | System/import. |
| `gold_label_id` | string | yes | Globally unique. | Source/system. |
| `project_id` | string | yes | Project relation. | Required. |
| `item_id` | string | yes | Item relation. | Required. |
| `label_domain_id` | string | yes | Domain relation. | Required. |
| `label` | string | no | Canonical hard label. Mutually exclusive with `distribution`. | Null allowed only when distributional or unresolved. |
| `distribution` | object[string, number] | no | Complete registered domain; finite nonnegative probabilities summing to 1 within `1e-9`. | Mutually exclusive with hard label unless hard label equals documented mode. |
| `resolution_status` | enum | yes | `resolved_hard`, `resolved_distributional`, `unresolved`. | Explicit; never inferred from null alone. |
| `gold_source` | enum | yes | `expert_adjudication`, `trusted_reference`, `benchmark_truth`, `simulation_truth`. | Required provenance semantics. |
| `version` | integer | yes | Positive and monotonic per item. | Required. |
| `supersedes_gold_label_id` | string | no | Previous gold version. | Required when version > 1. |
| `created_at` | timestamp | yes | UTC. | System/source. |
| `source_import_id` | string | no | Required for imported gold. | System assigned. |
| `metadata_json` | object | no | Rationale/reference metadata. | Missing becomes `{}`. |

Only `resolved_hard` gold contributes to hard accuracy, precision, recall, and confusion matrices. Distributional gold contributes only to compatible probabilistic/distributional metrics. Unresolved gold is excluded and counted.

## 8. ReviewEvent

| Field | Type | Req. | Constraints and semantics | Provenance / missing behavior |
|---|---|---:|---|---|
| `schema_version` | string | yes | Supported version. | System. |
| `review_event_id` | string | yes | Globally unique. | System/source. |
| `project_id` | string | yes | Project relation. | Required. |
| `item_id` | string | yes | Item relation. | Required. |
| `reviewer_id` | string | yes | Reviewer identifier. | Required. |
| `strategy_id` | string | yes | Exact queue strategy/config version that selected the item. | Required for evaluation. |
| `queue_rank` | integer | yes | Positive rank at selection time. | Required. |
| `review_budget_fraction` | number | no | Finite in `(0,1]`. | Missing if not part of a budgeted experiment. |
| `pre_review_label` | string | no | Hard label before review. | Null allowed when unresolved. |
| `post_review_label` | string | no | Hard label after review. | Null allowed only for unresolved/distributional resolution. |
| `post_review_distribution` | object | no | Valid label distribution. | Optional alternative to hard result. |
| `outcome` | enum | yes | `confirmed`, `corrected`, `unresolved`, `policy_issue`. | Required. |
| `reason_code` | string | yes | Registered review reason. | Required. |
| `decision_timestamp` | timestamp | yes | UTC. | Required. |
| `review_duration_ms` | integer | no | Nonnegative. | Missing means unobserved. |
| `source_snapshot_id` | string | yes | Snapshot used to rank item. | Required. |
| `metadata_json` | object | no | Additional review evidence. | Missing becomes `{}`. |

Review outcomes are append-only. Corrections generate new GoldLabel or AnnotationEvent records through an explicit workflow; ReviewEvent itself does not overwrite them.

## 9. ConsensusResult

| Field | Type | Req. | Constraints and semantics |
|---|---|---:|---|
| `schema_version` | string | yes | Supported version. |
| `consensus_result_id` | string | yes | Globally unique. |
| `dataset_snapshot_id` | string | yes | Immutable input snapshot. |
| `project_id` | string | yes | Project. |
| `item_id` | string | yes | Item. |
| `method` | enum | yes | `majority_vote`, `reliability_weighted_vote`, `dawid_skene`. |
| `method_version` | string | yes | Semantic implementation version. |
| `config_hash` | string | yes | SHA-256 of canonical method configuration. |
| `hard_label` | string | no | Null when tied/unresolved/unavailable. |
| `probabilities` | object[string, number] | yes | Complete label domain, normalized within `1e-9`. |
| `confidence` | number | no | Maximum probability only when probabilities have the stated interpretation. |
| `uncertainty` | number | no | `1 - max(probabilities)` for probabilistic consensus. |
| `status` | enum | yes | `success`, `unresolved`, `insufficient_evidence`, `non_converged`, `failed`. |
| `support_n` | integer | yes | Current annotations used for item. |
| `convergence` | object | no | Required for Dawid-Skene; iterations, criterion, likelihood history reference. |
| `warnings` | array[string] | yes | Empty array when none. |
| `created_at` | timestamp | yes | UTC. |

## 10. AnnotatorEstimate

| Field | Type | Req. | Constraints and semantics |
|---|---|---:|---|
| `schema_version` | string | yes | Supported version. |
| `annotator_estimate_id` | string | yes | Unique. |
| `dataset_snapshot_id` | string | yes | Immutable input. |
| `project_id` | string | yes | Project. |
| `annotator_id` | string | yes | Annotator. |
| `method` | enum | yes | `gold_empirical`, `beta_binomial`, `dirichlet_confusion`, `dawid_skene_confusion`. |
| `method_version` | string | yes | Version. |
| `config_hash` | string | yes | Configuration checksum. |
| `estimate` | object | yes | Method-specific values. |
| `intervals` | object | no | Credible/confidence intervals with level and method. |
| `support` | object | yes | Labels, gold labels, classes, co-annotations. |
| `status` | enum | yes | `success`, `insufficient_evidence`, `unavailable`, `failed`. |
| `warnings` | array[string] | yes | Explicit caveats. |
| `created_at` | timestamp | yes | UTC. |

No field may be named `accuracy` unless it was calculated against resolved hard gold.

## 11. QualityFlag

| Field | Type | Req. | Constraints and semantics |
|---|---|---:|---|
| `schema_version` | string | yes | Supported version. |
| `quality_flag_id` | string | yes | Unique. |
| `dataset_snapshot_id` | string | yes | Input snapshot. |
| `project_id` | string | yes | Project. |
| `entity_type` | enum | yes | Core: `item` or `dataset`. |
| `entity_id` | string | yes | Flagged item/project. |
| `flag_type` | enum | yes | `probable_quality_defect`, `probable_ambiguity_policy_issue`, `insufficient_evidence`, `overlap_connectivity`. |
| `severity` | enum | yes | `info`, `low`, `medium`, `high`; rule-defined, not color-defined. |
| `evidence` | object | yes | Named values and references used by rule. |
| `support_n` | integer | yes | Relevant observations. |
| `method` | string | yes | Rule/method name and version. |
| `threshold_config_hash` | string | yes | Frozen thresholds. |
| `uncertainty` | object | no | Relevant interval/posterior data. |
| `recommended_action` | enum | yes | `review_label`, `clarify_policy`, `collect_more_labels`, `inspect_overlap`, `no_action`. |
| `status` | enum | yes | `active`, `resolved`, `superseded`. |
| `created_at` | timestamp | yes | UTC. |

Every flag must be reconstructable from its snapshot and configuration.

## 12. BenchmarkRun

| Field | Type | Req. | Constraints and semantics |
|---|---|---:|---|
| `schema_version` | string | yes | Supported version. |
| `benchmark_run_id` | string | yes | Unique and immutable. |
| `protocol_version` | string | yes | Approved benchmark protocol. |
| `config_checksum` | string | yes | SHA-256. |
| `dataset_manifest_ids` | array[string] | yes | At least one. |
| `git_commit` | string | yes | Full commit hash. |
| `dirty_tree` | boolean | yes | Must be false for release evidence. |
| `dependency_lock_checksum` | string | yes | SHA-256. |
| `seeds` | ordered array[integer] | yes | Exact predefined order. |
| `methods` | array[object] | yes | Names, versions, config hashes. |
| `started_at` | timestamp | yes | UTC. |
| `completed_at` | timestamp | no | Required for completed run. |
| `status` | enum | yes | `running`, `completed`, `partial`, `failed`. |
| `runtime_metadata` | object | yes | Python, OS, architecture, CPU. |
| `artifact_root` | string | yes | Immutable run artifact path. |
| `failure_summary` | object | no | Required for partial/failed. |

## 13. DatasetManifest

| Field | Type | Req. | Constraints and semantics |
|---|---|---:|---|
| `schema_version` | string | yes | Supported version. |
| `dataset_manifest_id` | string | yes | Unique. |
| `dataset_name` | string | yes | Stable canonical name. |
| `dataset_version` | string | yes | Source release or simulator config version. |
| `source_uri` | string | yes | Authoritative source. |
| `license` | string | yes | SPDX identifier or exact documented terms. `unknown` fails release use. |
| `redistribution_allowed` | boolean | yes | Based on documented audit. |
| `raw_checksums` | object[path, sha256] | yes | Every required source file. |
| `canonical_snapshot_checksum` | string | yes | Derived canonical dataset. |
| `schema_version_used` | string | yes | Canonical schema. |
| `adapter_version` | string | yes | Dataset adapter implementation. |
| `split_definition` | object | yes | Deterministic evaluation/development separation. |
| `known_limitations` | array[string] | yes | May be empty only with explicit audit. |
| `created_at` | timestamp | yes | UTC. |

## 14. Duplicate annotation policy

Duplicate identity key:

```text
(project_id, item_id, annotator_id, label_domain_id, event_version)
```

Rules:

1. Same identity key and byte-equivalent canonical content: retain one analytical row, record every source occurrence in the import report, status `duplicate_identical`.
2. Same identity key with conflicting content: reject the entire import by default, status `duplicate_conflict`.
3. Same `annotation_id` with any differing canonical content: reject.
4. Multiple labels for the same worker/item without explicit versions: reject; never select “last row wins.”
5. A user may resolve conflicts only through a corrected import or the explicit reannotation policy.

## 15. Reannotation and version policy

- A changed judgment creates a new AnnotationEvent.
- `event_version` must be prior version + 1.
- `supersedes_annotation_id` must point to the current prior event.
- The old event remains immutable and becomes `is_current = false` in the new snapshot.
- Analyses use current events unless a historical analysis explicitly selects an earlier snapshot.
- Original and reannotation timestamps are retained.
- Concurrent branches for the same prior event are a conflict and block snapshot creation.

## 16. Unresolved and distributional labels

- A tied Majority Vote returns `hard_label = null`, `status = unresolved`, and complete vote fractions.
- A low-confidence Dawid-Skene result may still return an argmax label, but project policy can mark it unresolved; the probability vector remains authoritative.
- Distributional gold is stored as a complete probability vector, not synthetic repeated rows.
- Unresolved gold cannot be used for hard-label performance metrics.
- No method may convert unresolved to a hard label without recording the method and threshold.

## 17. Timestamp rules

- Canonical storage is UTC.
- Naive timestamps are rejected unless the import configuration explicitly supplies an IANA timezone.
- DST-ambiguous local timestamps are rejected unless an offset/fold resolution is supplied.
- Event ordering uses `(timestamp, annotation_id)` when timestamps exist.
- Missing timestamps are allowed for core non-temporal analysis and counted in data quality diagnostics.
- Import time is never substituted for annotation time.

## 18. Raw-data preservation

For every import:

- preserve source bytes before parsing;
- calculate SHA-256;
- record original filename, MIME detection, size, and ingestion UTC time;
- store importer configuration and column mapping;
- write validation issues with source row numbers;
- never overwrite the raw source;
- create a new import ID for every retry;
- prevent raw personal metadata from entering public benchmark artifacts.

## 19. Schema versioning

- Patch: validation clarification or backward-compatible optional field.
- Minor: backward-compatible new entity/field/enum value.
- Major: changed semantics, identity, or required fields.
- Every migration is one-way, explicit, tested, and produces a new snapshot.
- Readers reject unsupported future major versions.
- No migration edits the raw import.

## 20. Valid examples

### Valid annotation row

```json
{
  "schema_version": "4.0.0",
  "annotation_id": "ann_01JABC",
  "project_id": "sentiment_demo",
  "item_id": "item_1042",
  "annotator_id": "worker_17",
  "label_domain_id": "sentiment_v1",
  "label": "neutral",
  "event_version": 1,
  "is_current": true,
  "timestamp": "2026-08-09T06:30:00Z",
  "confidence": 0.72,
  "duration_ms": 18400,
  "annotation_source": "human",
  "metadata_json": {},
  "source_import_id": "imp_01JXYZ",
  "source_row_number": 42
}
```

### Valid distributional gold

```json
{
  "schema_version": "4.0.0",
  "gold_label_id": "gold_77_v1",
  "project_id": "sentiment_demo",
  "item_id": "item_77",
  "label_domain_id": "sentiment_v1",
  "distribution": {"negative": 0.10, "neutral": 0.55, "positive": 0.35},
  "resolution_status": "resolved_distributional",
  "gold_source": "expert_adjudication",
  "version": 1,
  "created_at": "2026-08-09T07:00:00Z",
  "metadata_json": {"panel_size": 5}
}
```

## 21. Invalid examples

| Invalid row | Reason |
|---|---|
| Annotation with `label: null` | Missing is not abstention. |
| Annotation label `Positive` when domain contains `positive` | Labels are canonical and case-sensitive. |
| `confidence: 72` | Confidence must be in `[0,1]`. |
| Naive timestamp `2026-08-09 12:00` without import timezone | Temporal meaning is ambiguous. |
| Two different labels at event version 1 for same worker/item | Conflicting duplicate; no last-row-wins policy. |
| Gold row with hard label and a contradictory distribution | Gold representation is ambiguous. |
| Distribution summing to `0.98` | Must normalize within `1e-9`; importer must not silently repair. |
| Annotation referencing an unknown worker or item | Referential-integrity failure. |
| `severity_weight: -2` | Severity must be positive. |
| Reannotation version 3 with no superseded annotation | Broken history. |
| Project with one registered class | Core categorical agreement/consensus is undefined. |
| Benchmark manifest with `license: unknown` | Cannot pass benchmark release gate. |
