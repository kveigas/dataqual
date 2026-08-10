"""Verify callable agreement-statistic reference dependencies."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
from pathlib import Path

import krippendorff
import numpy as np
from nltk.metrics.agreement import AnnotationTask
from statsmodels.stats.inter_rater import fleiss_kappa


def distribution_license(package: str) -> dict[str, object]:
    dist = metadata.distribution(package)
    license_files = [str(path) for path in (dist.files or []) if "license" in str(path).lower()]
    return {
        "version": dist.version,
        "metadata_license": dist.metadata.get("License"),
        "classifiers": [value for value in dist.metadata.get_all("Classifier", []) if value.startswith("License ::")],
        "license_files": license_files,
        "home_page": dist.metadata.get("Home-page") or dist.metadata.get("Project-URL"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Rows are raters, columns are items. NaN is an absent rating.
    reliability_data = np.array(
        [
            [0, 0, 1, 1, 0],
            [0, 1, 1, 1, np.nan],
            [0, 0, 1, 0, 1],
        ],
        dtype=float,
    )
    alpha = krippendorff.alpha(reliability_data=reliability_data, level_of_measurement="nominal")
    nltk_rows = [
        (f"rater-{rater}", f"item-{item}", int(value))
        for rater, row in enumerate(reliability_data)
        for item, value in enumerate(row)
        if not np.isnan(value)
    ]
    nltk_alpha = AnnotationTask(data=nltk_rows).alpha()

    # Fleiss expects item-by-category counts and, in its classical form, a
    # constant number of ratings per item. Use only the four complete items.
    complete = reliability_data[:, :4].T.astype(int)
    counts = np.stack([(complete == 0).sum(axis=1), (complete == 1).sum(axis=1)], axis=1)
    kappa = fleiss_kappa(counts, method="fleiss")

    result = {
        "status": "pass",
        "packages": {
            "krippendorff": distribution_license("krippendorff"),
            "nltk": distribution_license("nltk"),
            "statsmodels": distribution_license("statsmodels"),
        },
        "fixture": {
            "rater_by_item": [[None if np.isnan(value) else int(value) for value in row] for row in reliability_data],
            "fleiss_item_by_category_counts_complete_items_only": counts.tolist(),
        },
        "nominal_krippendorff_alpha": float(alpha),
        "nltk_nominal_krippendorff_alpha": float(nltk_alpha),
        "alpha_absolute_difference": abs(float(alpha) - float(nltk_alpha)),
        "fleiss_kappa": float(kappa),
        "convention_notes": [
            "Krippendorff alpha accepts missing ratings and variable ratings per item.",
            "statsmodels Fleiss kappa consumes item-by-category counts and its documented classical form assumes a constant number of ratings per item.",
            "The two values are not interchangeable and are not expected to match on the same observations.",
            "The standalone krippendorff package is GPL-3.0; keep it out of runtime dependencies.",
            "NLTK is Apache-2.0, matches this fixture exactly, and is the selected independent parity reference.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
