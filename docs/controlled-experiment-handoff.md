# Controlled cofolding experiment: verification and return contract

Internal AI-assisted planning document, October28,2026. Not a launch authorization, executable runner, final protocol or student-authored submission. No controlled GPU predictions have been generated here. Read with TCBB-contribution-redesign.md and the blocked job manifest in work/study/manifests/evidence_experiment/.

## Scientific object that must stay fixed

Each system has one input-defined protein/ligand assembly and one separately generated native-top Protenix anchor. All four opinion arms assess that SAME anchor. An opinion may disagree with it, but must not replace it, move it to another pocket or select a better experimental match. Preserve native ranking for all25 anchor samples and all5 samples in each opinion job, including unsuccessful runs. Experimental geometry cannot determine ligand mapping, native selection, input treatment, rerun eligibility or feature extraction.

Full-cohort planning currently contains877 candidate statuses, not877 eligible systems. The677 input-planned systems have30 blocked job specifications each:5 anchor jobs and25 opinion jobs, yielding150 planned samples/system. Actual MSA availability, input chemistry and common runner compatibility remain unverified; there is no final launch list or valid GPU-hour estimate. Do not silently turn these specifications into runnable predictor commands.

## Gate1: input and runner identity

Return the system-input SHA256, exact protein sequences and copy/chain roles, proper ligand identity and atom mapping, cofactors/ions and declared covalency. No experimental-chain assignment in predictor confidence. Resolve unsupported peptides, hydrogen/isotope cases, covalent assemblies and alternate chemical states by outcome-independent policy before inclusion.

For each predictor, record exact code commit, container/environment digest, model/checkpoint identifier and weight checksum, runtime dependency versions, invocation/configuration, diffusion seeds, sample IDs, recycles, sampling steps, template settings, MSA server/cache settings and any automatic fallback. Candidate versions in the planner are not verified runner compatibility. Use the same verified configuration for new main and external predictions; released main/external runs are not a matched intervention.

## Gate2: prove the evidence intervention reached the model

Saving two A3M files is insufficient. A wrapper may recrop, reorder, subsample, deduplicate, pair, augment or replace their rows. Prediction-time data transformations must be inspected and a compact processed-input audit returned before claiming shared or diversified evidence.

For every protein entity/copy and block, retain these hashes and audit facts:

- Original alignment pool, exact query, clustering job/configuration and complete sequence-to-cluster assignments. The alignment-source hash alone does not establish clustering provenance.
- Requested view manifest: seed, ordered source-row IDs, provided cluster IDs, original insertion-bearing rows, aligned residues and row depth. Both views include the exact query and exclude its entire provided cluster from the homolog pool.
- Actually consumed rows after all runner preprocessing: row identities/order, effective depth, aligned residues, insertion/deletion features and chain boundaries. Record the extraction location and code hash; a flag saying verified is not evidence.
- Pairing semantics for multichain systems: paired versus unpaired rows, partner row correspondence, homomer copy handling and any padding/masks. Build chain-aware views; do not independently shuffle rows that represent a paired homolog complex. If equivalence cannot be verified, leave the system unresolved for the primary controlled contrast.
- Whether templates, database lookup, automatic MSA generation, row augmentation or fallback changed effective inputs. Fail the intended treatment gate when undeclared evidence enters; retain the failure record.

Use normalized, input-defined semantic evidence identities across predictor formats, not equality of unrelated tensor-file bytes. Preserve separate byte hashes too. V0 consumed in P0a/P0b/B0b should represent the declared shared evidence; V1 in P1b/B1b should represent its declared alternative. If a model-specific transformation prevents equivalence, report it and do not describe that contrast as a clean model-only intervention. Different architectures still interpret identical evidence differently; this gate does not establish statistical independence.

The existing evidence_views.py implements selection from PROVIDED clusters only. It does not cluster, verify similarity thresholds, preserve arbitrary paired-MSA semantics automatically, audit predictor tensors or prove model independence. No chain-specific MSA collection should be sent to this local workspace.

A preliminary pure-data return checker now exists in evidence_consumption.py. In its deliberately restricted single-protein-chain/unpaired scope, it checks a supplied normalized processed-row record against the hash-bound requested view: exact query/row order/depth, aligned residues, insertion counts and active columns; rejects templates/automatic extra evidence, masks/crops and multichain/paired inputs. A canonical audit convention counts insertions before each aligned column plus a terminal count; this is NOT a model tensor layout. Three synthetic tests exercise altered depth/order/insertion features/masks, evidence flags, provenance identities and unsupported pairing. No real predictor adapter or tensor extraction is implemented. Passing the checker proves only consistency of supplied records, not that a runner actually consumed them; returned flags explicitly keep actual_tensor_extraction_verified=false. Independently verify extractor code and hash-bound raw tensors before accepting that scientific gate. Model-specific unobservable/transformed terminal insertions must not be fabricated to satisfy the contract; unresolved normalization requires a documented policy before any controlled run.

## Gate3: compact prediction and measurement return

Return outcome-free JSON/JSONL records with explicit schema/version and job ID, input/view/runner hashes, actual settings and seeds, all sample native confidence fields with exact field meanings, native ranking direction/tie policy, selected sample ID, and hashes of raw confidence/coordinate artifacts. Preserve score ties and missing scores. Any failed sample/job has a reason and retry lineage; never return only successes or best experimental fits.

Keep an immutable raw-artifact index at the remote execution site. For selected coordinates return their input-only chain/atom correspondence proof, proper ligand graph/atom-order identity and receptor-alignment specification. Compact geometry returns must identify code version, coordinate hashes, atom correspondence and each missing check. Independent remeasurement must remain possible from retained remote raw artifacts; compact self-reported scores alone are not reproducible evidence. Local all-sample coordinates, model weights and MSA databases are not requested.

For every job log hardware, device count, wall time, aggregate allocated GPU-device seconds, measured peak memory, run status and retry costs, with units and measurement method. Do not confuse summed device time with wall time, exclude failures from cost, or infer equal compute from equal samples. Shared predictions contribute once to cost although reused between arms.

Return no experimental correctness labels in the prediction/feature package. Reference-dependent evaluation is a separate gated step after input eligibility, group assignments, splits, endpoints, missingness rules and analysis are genuinely frozen. A source hash or completed engineering archive is not that freeze.

## Gate4: unbiased cohort and evaluation handoff

Reconcile ALL877 main candidate IDs, including no-run, shallow-MSA, mapping failure and acquisition failure. Distinguish structural invalidity from missing acquisition, timeout and unavailable confidence. Prespecify complete-panel primary analyses and broader missingness/deployment analyses; do not assign wrong-pose labels to processing failures or compare methods on different successful subsets.

Summarize five blocks to one system observation. Reused cells and seeds are paired measurements, not independent experimental units. Freeze receptor groups and ligand/scaffold sensitivity rules, then lock grouped splits without outcomes. External927 raw targets are a single-family campaign with repeated chemical identities, not927 independent tests of broad biological generalization. Exact reference eligibility and Protenix external input identity are still unresolved.

The strongest common control must receive all native confidence fields available from the same opinion panel, anchor validity and ordinary within-anchor dispersion. Compare it to ordinary/shared-evidence geometry, diversified-evidence geometry and the complete component-score model on the same cohort/folds. Fragility contrasts are deterministic differences, not extra information after their components. Predeclare calibration, decision operating point and smallest practical improvement. Report full error-coverage curves and group uncertainty without outcome-guided changes.

## Current outstanding responsibilities

New outcome-free joint grouping audit: see grouping-feasibility.md. One receptor+scaffold component contains505/681 chemistry-resolved candidates, so declaring balanced joint-cold folds would be misleading. Resolve the grouping/estimand and imbalance policy before launch/evaluation; do not infer chemically cold validation from receptor groups alone. Draft group manifests are not final split assignments.

Local pipeline: finish released-data provenance/missingness reconciliation and input/feature software checks; freeze only after justified eligibility and split rules exist. Future compute team: validate real alignment/cluster inputs, predictor wrappers and processed evidence equivalence; generate new predictions only with explicit authorization outside this chat; retain immutable raw artifacts and costs. Students: independently understand, verify and own their scientific decisions and writing; disclose actual AI assistance under the chosen venue's rules. No teammate has been contacted and no submission has been made.
