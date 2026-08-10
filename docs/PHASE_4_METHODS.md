# Phase 4 Methods Specification — Annotator Intelligence & Disagreement Diagnostics

## 1. Overview & Conceptual Architecture

Phase 4 introduces an uncertainty-aware **Annotator Intelligence Engine** and an evidence-backed **Item Disagreement Diagnostic System** for DataQual v4.

The system addresses two fundamental questions without making ungrounded claims of causal truth:
1. **Worker Intelligence**: How much trusted gold evidence supports an annotator's reliability, how uncertain is that estimate, and what class-specific confusions does the worker exhibit?
2. **Item Diagnostics**: Which item-level disagreements stem from low-quality worker errors versus genuine data ambiguity or labeling policy gaps?

---

## 2. Annotator Intelligence Engine

### 2.1 Beta-Binomial Reliability Shrinkage & Prior Provenance

For target worker $w$ evaluated on $n_w$ resolved hard gold items, let $s_w$ be the number of correct annotations and $f_w = n_w - s_w$ be failures.

#### Leave-One-Worker-Out Project Prior
To avoid circular self-reinforcement, the project prior excludes target worker $w$:
$$S_{-w} = \sum_{v \ne w} s_v, \quad N_{-w} = \sum_{v \ne w} (s_v + f_v)$$

- If $N_{-w} \ge 20$:
  $$m_{-w} = \frac{S_{-w} + 0.5}{N_{-w} + 1.0}, \quad \text{prior\_source} = \text{"leave\_one\_out\_project"}$$
- If $N_{-w} < 20$:
  $$m_{-w} = 0.5, \quad \text{prior\_source} = \text{"fallback\_symmetric"}$$

#### Posterior Distribution
With prior weight $\kappa_0 = 2.0$, prior parameters are $\alpha_0 = 2 m_{-w}$ and $\beta_0 = 2(1 - m_{-w})$. The posterior distribution is:
$$\text{Beta}(\alpha_0 + s_w, \, \beta_0 + f_w)$$

- **Posterior Mean**: $\mathbb{E}[\theta_w] = \frac{\alpha_0 + s_w}{\alpha_0 + \beta_0 + n_w}$
- **95% Credible Interval**: $[L_{0.025}, U_{0.975}]$ computed via `scipy.stats.beta.ppf([0.025, 0.975], \alpha_{\text{post}}, \beta_{\text{post}})`.

#### Provenance Fields
`BetaBinomialEstimate` explicitly exposes:
- `prior_source`: `"leave_one_out_project"` or `"fallback_symmetric"`
- `prior_population_n`: $N_{-w}$
- `prior_mean`: $m_{-w}$
- `prior_strength`: $\kappa_0 = 2.0$

---

### 2.2 Dirichlet-Smoothed Class Confusion & Marginal Beta Credible Intervals

For worker $w$ evaluated on hard gold, let $x_{c,k}$ be the count of times gold class $c$ was annotated as class $k$, across registered domain classes $K$.

#### Dirichlet Smoothing
Using Jeffreys prior $\alpha = 0.5$, smoothed probabilities are:
$$\hat{\pi}_{c,k} = \frac{x_{c,k} + 0.5}{n_c + 0.5 K}, \quad \text{where } n_c = \sum_{k=1}^{K} x_{c,k}$$

#### Marginal Beta Credible Intervals
Per Amendment 5, per-cell credible intervals are derived from the marginal Beta posterior of the Dirichlet distribution:
$$\text{Beta}\left(x_{c,k} + 0.5, \, (n_c - x_{c,k}) + 0.5(K - 1)\right)$$

Raw counts $x_{c,k}$ remain strictly separated from smoothed probabilities $\hat{\pi}_{c,k}$.

---

### 2.3 Gold-Observed vs Dawid-Skene Latent Confusion Comparison

For workers with gold coverage ($n_c > 0$), cell-by-cell absolute differences compare gold-observed confusion $\hat{\pi}_{c,k}^{\text{gold}}$ to Dawid-Skene estimated latent transition probabilities $\hat{\pi}_{c,k}^{\text{DS}}$:
$$\Delta_{c,k} = \left| \hat{\pi}_{c,k}^{\text{gold}} - \hat{\pi}_{c,k}^{\text{DS}} \right|$$
Mean Absolute Error (MAE) is reported across all evaluated cells.

---

### 2.4 Calibration Metrics (Brier Score & ECE)

When annotator confidence scores $p_i \in [0, 1]$ are recorded:
- **Brier Score**: $\text{BS} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$ where $y_i \in \{0, 1\}$.
- **Expected Calibration Error (ECE)**: 10 equal-width bins $[0, 0.1), \dots, [0.9, 1.0]$.
  $$\text{ECE} = \sum_{b=1}^{10} \frac{|B_b|}{N} \left| \text{acc}(B_b) - \text{conf}(B_b) \right|$$

If confidence is unobserved, `status = "not_available"` is set.

---

## 3. Disagreement Diagnostics & Quality Flags

### 3.1 Normalized Categorical Entropy
Per Amendment 4, categorical vote entropy $H = -\sum_{c=1}^K p_c \ln p_c$ is normalized using registered domain size $K$:
$$H_{\text{norm}} = \frac{H}{\ln K}$$
Zero-probability classes contribute $0$. If $K \le 1$, $H_{\text{norm}}$ returns undefined (`None`).

### 3.2 Vote Margin
$$m = p_{(1)} - p_{(2)}$$
where $p_{(1)}$ and $p_{(2)}$ are the top two vote proportions.

---

### 3.3 Quality Flag Entity Semantics & Diagnostic Rules (Amendment 1 & 2)

Diagnostic rules generate versioned, hashed `QualityFlag` objects with strict entity semantics:

#### 1. Dissenting Annotation Quality Defect (`entity_type = "annotation"`)
- **Condition**: Consensus lead exists (margin $\ge 0.20$ or top prop $\ge 0.60$), and worker $w$ dissents with gold reliability lower bound $L_{0.025} < 0.50$.
- **Semantics**: Flag targets the specific dissenting annotation (`entity_id = "annotation_id"`), NOT the item.
- **Recommended Action**: `"review_annotation"`

#### 2. Probable Ambiguity / Policy Issue (`entity_type = "item"`)
- **Condition**: High vote entropy ($H_{\text{norm}} \ge 0.60$) or small vote margin ($m \le 0.20$) or split strong workers ($L_{0.025} \ge 0.70$), without evidence of weak worker error.
- **Recommended Action**: `"clarify_policy"`

#### 3. Mixed Evidence (`entity_type = "item"`)
- **Condition**: High entropy combines both weak worker dissent and unexplained disagreement.
- **Recommended Action**: `"inspect_overlap"`

#### 4. Insufficient Evidence (`entity_type = "item"`)
- **Condition**: $m_i < 2$ annotations.
- **Recommended Action**: `"collect_more_labels"`

---

### 3.4 Diagnostic Threshold Configuration Provenance (Amendment 2)

All generated `QualityFlag` objects record immutable provenance:
- `threshold_config_version`: `"1.0.0"`
- `threshold_config_hash`: SHA-256 digest of serialized thresholds
- `thresholds_used`: dictionary of exact parameters evaluated
