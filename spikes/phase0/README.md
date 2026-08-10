# DataQual v4 Phase 0 Spikes

These scripts verify assumptions only. They are not production storage, API, UI, or statistical-engine modules.

## Safety and repository policy

- Never commit `raw/`, `outputs/`, `.venv/`, or the downloaded `relevance-2` files.
- The dataset license is not stated. The downloader records hashes but does not grant redistribution rights.
- All synthetic output directories may be deleted and regenerated.
- `crowdkit_ds_small.json` contains generated fixture inputs and observed outputs only; it contains no copied Crowd-Kit implementation.

## Tested Windows environment setup

From the repository root in PowerShell, with Python 3.12 and uv available:

```powershell
uv venv spikes/phase0/.venv --python 3.12 --seed
$phase0Python = Resolve-Path 'spikes/phase0/.venv/Scripts/python.exe'
& $phase0Python -m pip install --requirement spikes/phase0/python312_freeze.txt
& $phase0Python -m pip check
```

`python312_freeze.txt` captures the complete tested spike environment. It intentionally includes research-only and spike-only packages and must not become the production backend dependency file.

Run the import and minimal-operation probe:

```powershell
& $phase0Python spikes/phase0/environment_probe.py `
  --output spikes/phase0/results/environment_probe.json
```

## Acquire `relevance-2` outside the repository

```powershell
$phase0Python = Resolve-Path 'spikes/phase0/.venv/Scripts/python.exe'
& $phase0Python spikes/phase0/download_relevance_2.py `
  --output-dir 'C:/temporary-data/dataqual-relevance-2'
```

The script refuses to overwrite an existing archive unless `--force` is provided. Expected archive hashes:

- MD5: `a39c3c30d9e946eeb80ca39954c96e95`
- SHA-256: `0d8b5c4ffdb042cc1435ac20933bcf3218310e0bcc6dd27baef5bcfe64973bef`

## Crowd-Kit and frozen Dawid–Skene fixture

After downloading through Crowd-Kit's loader or extracting the verified archive to an external cache:

```powershell
$phase0Python = Resolve-Path 'spikes/phase0/.venv/Scripts/python.exe'
& $phase0Python spikes/phase0/verify_crowdkit.py `
  --output tests/reference_fixtures/crowdkit_ds_small.json `
  --dataset-cache 'C:/temporary-data/crowdkit-cache'
```

The `--dataset-cache` argument is optional. Omitting it runs only the generated method-callability and DS fixture checks.

## Agreement references

```powershell
$phase0Python = Resolve-Path 'spikes/phase0/.venv/Scripts/python.exe'
& $phase0Python spikes/phase0/agreement_reference_spike.py `
  --output spikes/phase0/results/agreement_reference.json
```

The script verifies NLTK nominal alpha, the standalone GPL implementation for audit comparison, and statsmodels Fleiss kappa. The GPL package is rejected from normal runtime/test dependencies; NLTK is the selected parity reference.

## Small storage path

```powershell
$phase0Python = Resolve-Path 'spikes/phase0/.venv/Scripts/python.exe'
& $phase0Python spikes/phase0/duckdb_arrow_spike.py `
  --output-dir spikes/phase0/outputs/duckdb-arrow `
  --rows 10000
```

## Registered one-million-row feasibility run

```powershell
$phase0Python = Resolve-Path 'spikes/phase0/.venv/Scripts/python.exe'
& $phase0Python spikes/phase0/million_row_feasibility.py `
  --output-dir spikes/phase0/outputs/million-row `
  --rows 1000000 `
  --seed 20260809
```

The script intentionally rejects row counts other than one million for the registered Phase 0 result. Output data are synthetic and ignored; the small result JSON is retained under `spikes/phase0/results/`.

## Frontend compatibility probe

```powershell
Push-Location spikes/phase0/frontend_probe
pnpm install --frozen-lockfile
node probe.mjs
pnpm exec vite --version
pnpm exec tsc --version
pnpm exec vitest --version
pnpm exec playwright --version
pnpm exec pyright --version
Pop-Location
```

A fresh networked install and module probe passed. Playwright browser binaries are not part of Phase 0 and were not downloaded. A fully offline install into a newly empty pnpm store was not verified because that store lacked optional cross-platform and npm-attestation artifacts.

## Result interpretation

The JSON timings are single-machine feasibility observations. Do not present them as throughput guarantees or benchmark rankings. Refer to `docs/REFERENCE_ENVIRONMENT.md` for the exact machine and limitations.
