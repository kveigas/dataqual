# Phase 0B benchmark-resolution spikes

These scripts are verification tools, not production DataQual modules. Raw datasets must be written to an external runtime directory, never this repository.

## Environment

The verified run used Python 3.12 with `crowd-kit==1.4.2`, pandas, NumPy, SciPy, scikit-learn, PyYAML, and openpyxl in an isolated virtual environment.

## Reproduce

```powershell
python spikes/phase0b/download_zenodo_candidates.py --output-dir <external-raw-dir>
python spikes/phase0b/profile_and_smoke.py --raw-dir <external-raw-dir> --output spikes/phase0b/results/candidate_profiles.json
python spikes/phase0b/assess_cifar10n.py --output-dir <external-cifar10n-dir> --result spikes/phase0b/results/cifar10n_assessment.json
python spikes/phase0b/weighted_vote_sensitivity_spike.py --replicates 10 --output spikes/phase0b/results/weighted_vote_sensitivity.json
```

The Zenodo downloader refuses records without one of the explicitly approved licenses, verifies published MD5 values, and records SHA-256. The profiler performs the registered temporary conversions, graph/disagreement summaries, and non-production Crowd-Kit MV/DS smoke tests. The CIFAR-10N script downloads only official UCSC-REAL files and records the worker-slot mapping limitation. The sensitivity spike runs the six-scenario, five-threshold design without importing future production code.

Generated aggregate JSON is evidence from an exploratory Phase 0B run. It is not a locked release benchmark report.
