# Cofolding reliability — Sathvik and Akshobya execution repo

This public repository now contains **only the teammates' acquisition, predictor/MSA preparation, measurement and return-contract materials**, plus necessary shared safeguards and portable tests. Aarav's statistical analysis/grouping modules, analysis tests and venue notes have been removed from the current tree and remain in his local project. Earlier commits remain recoverable; this is not a history purge.

## Ownership

- **Aarav: local analysis/integration track,30GB planned working budget.** Receives compact curated inputs/features; owns final eligibility/protocol/splits, statistics, calibration, uncertainty, transfer evaluation, figures and manuscript integration. No full model/MSA/ensemble storage locally. His detailed local runbook is deliberately not in this repo.
- **[Sathvik](SATHVIK.md): main-cohort input recovery, MSA preparation, full controlled predictions and compact feature export.**
- **[Akshobya](AKSHOBYA.md): common verified runners, external-cohort inputs/MSAs/predictions and shared artifact/cost QA.**

See [the full split](WORK_SPLIT.md) and [the compact return contract](RETURN_CONTRACT.md). Sathvik and Akshobya each have four3-point work packages (12 planning points each). This balances estimated human responsibility, not proven GPU hours, disk usage or author order.

## Storage boundary

**The30GB is Aarav's allocation, not data stored in GitHub and not a requirement to download30GB.** Model checkpoints, MSA pools, generated raw ensembles, GPU environments and large temporary artifacts stay with the compute team or approved remote storage. Their actual sizes depend on validated runners and cohort eligibility; no fixed total or exact fifty-fifty byte split is established. They must measure storage and preserve replayable remote raw artifacts, then deliver bounded compact batches.

GitHub contains no real prediction/reference structures, chemical/sequence inventories, private handoff ZIPs, original briefs, installed environments, model weights, MSA collections or credentials. Obtain source data directly from the official releases under their original terms. Do not push bulk data here, including through Git LFS.

## Project and nonclaims

Test whether changing MSA evidence makes agreement more useful for reliability of an unchanged native-top Protenix pose than simply switching models or drawing more ordinary samples. The proposed factorial crosses predictor diversity and matched-depth, cluster-disjoint evidence views. Calibration, ensembles, MSA perturbation and false-consensus concerns already exist in prior work.

**This is unfinished research. No new accuracy result, proven novelty, final protocol or TCBB acceptance claim is reported.** Native/mapping counts are acquisition/input provenance, not final sample sizes. Initial curation found616 paired input mappings among877 candidates; six Boltz true-top coordinates and twelve raw-ranking pairs still need resolution. A later local refresh ended at its runtime limit with only141/877statuses, and its finalizer timed out; do not treat it as a completed measurement pass or promise automatic completion. Historical completed snapshots are held locally, not published here.

## Start here

1. Read your owner file and WORK_SPLIT.md.
2. Read [design](docs/TCBB-contribution-redesign.md), [input/evidence contract](docs/controlled-experiment-handoff.md), [grouping constraint](docs/grouping-feasibility.md), [prior-work boundary](docs/closest-work-review.md), and [assistance disclosure](docs/assistance-record.md).
3. Validate wrappers/input evidence and supply outcome-free curation records. Full runs require Aarav's genuinely frozen eligibility/protocol and cross-review; no ceremonial freeze or best-reference selection.
4. Return compact artifacts using RETURN_CONTRACT.md. Statistical evaluation code is intentionally maintained outside this repo.

## Tests and code

Code is in `work/study`. The recorded Python3.12 package versions are in requirements.lock. With those dependencies available, from that directory run:

```text
python -m unittest discover -p "test_*.py"
```

The trimmed teammate subset is tested locally using the existing scientific environment. A fresh dependency install, Linux GPU environment, actual model wrappers and predictor CLI are not verified. No weights or MSA setup commands are asserted. Some acquisition scripts traverse a39.5GB remote archive and require source inputs absent here; do not run every script blindly. The measurement runner has a finite runtime, explicit missingness and bounded writes; a timeout is not completion. Tests certify software behavior only, not scientific results.

Primary sources: [Runs N' Poses](https://zenodo.org/records/18366081), [author code](https://github.com/plinder-org/runs-n-poses), [OpenBind release](https://zenodo.org/records/20798528), [benchmark](https://github.com/OpenBind-Consortium/EV-A71_2A_benchmark). Review applicable original terms; no blanket third-party license grant is made. No invitations, external GPU jobs or paper submissions are created by this repo.
