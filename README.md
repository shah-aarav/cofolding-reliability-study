# Cofolding reliability study

Research-in-progress code and experiment design for testing when protein–ligand prediction agreement is informative—and when models agree on the wrong pose.

The proposed contribution separates **predictor diversity** from **MSA evidence diversity** in a controlled factorial while keeping one native-top Protenix pose fixed. Compare reliability beyond native confidence, reference-free validity and ordinary same-model sampling. Ensembles, MSA perturbation, calibration and the possibility of false consensus are prior concepts, not claimed inventions.

**No new accuracy result, final protocol, established novelty or journal acceptance claim is reported.** TCBB is a potential target, not a promised outcome.

## Start here

- [Equal work split: Sathvik and Akshobya](WORK_SPLIT.md)
- [Experiment design](docs/TCBB-contribution-redesign.md)
- [Compute/input verification and return contract](docs/controlled-experiment-handoff.md)
- [Grouping feasibility and leakage constraints](docs/grouping-feasibility.md)
- [Closest-work review and incomplete access](docs/closest-work-review.md)
- [Actual AI assistance](docs/assistance-record.md)

## Public snapshot scope

This repository contains code, a portable synthetic-test subset and planning documentation. It intentionally excludes original briefs, raw prediction/reference structures, chemical/sequence inventories, private handoff archives, in-flight measurements, installed dependencies, model weights, MSA collections and credentials. Some documents describe artifacts held in the local research workspace; their presence in those documents does not mean the data are included here.

Local curation has verified871 Protenix and865 Boltz-2 native selections and616 paired input/atom mappings among877 candidates. These are provenance counts, NOT final eligibility or correct-pose counts. A refreshed877-candidate feature pass is still running at publication of this snapshot; no partial results are published here. OpenBind input auditing covers927 raw targets, with repeated chemistry and a single-family scope.

## Tests

Scientific code is under `work/study`. Use a Python3.12 environment with the recorded package versions in `requirements.lock`, then from that directory:

```text
python -m unittest discover -p "test_*.py"
```

The portable subset passed87 tests using the existing local scientific environment; the populated private workspace passed99 tests. A fresh dependency installation, Linux GPU setup and predictor CLI have NOT been tested. Tests check implementation behavior, not biological validity or performance. Acquisition scripts require separately obtained source artifacts and storage review; do not run them blindly. Some traverse a39.5GB compressed source remotely.

## Before expensive predictions or evaluation

Resolve source-backed input/reference eligibility, native missingness, actual processed-MSA equivalence, chain pairing and common runner/checkpoint provenance. Settle grouping/splits/endpoints/missingness and genuinely freeze the protocol before held-out correctness evaluation. The current scaffold+receptor graph has one component containing505/681 chemistry-resolved systems, so balanced joint-cold five-fold testing is not feasible under those draft links. Do not split or discard that component to obtain favorable results.

No model jobs, external messages or paper submissions are launched by this repository. Code/data source terms and venue assistance rules must be independently checked before reuse or submission. No blanket license grant is asserted for third-party materials. Students must independently understand and verify AI-assisted work.

## Primary data sources

- [Runs N' Poses release](https://zenodo.org/records/18366081), [author repository](https://github.com/plinder-org/runs-n-poses)
- [OpenBind selected release](https://zenodo.org/records/20798528), [benchmark repository](https://github.com/OpenBind-Consortium/EV-A71_2A_benchmark)

Obtain source data under their original terms. This public repository is not a redistribution of the source benchmark archives.
