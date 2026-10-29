# Proposed contribution: testing whether consensus survives evidence diversification

Working title: **When Cofolding Models Agree for the Wrong Reason: Evidence-Diversified Reliability of Protein–Ligand Poses**

Status: research design and implementation work, not a result, submission, final preregistration or established novelty claim. No held-out correctness outcomes have been inspected. TCBB is a target, not a promised acceptance. Existing data collection continues separately.

## The actual change

The original question was whether Protenix/Boltz agreement predicts correctness. The stronger question is:

**Does changing the information supplied to a second opinion make its agreement more informative than simply changing the model or drawing more ordinary samples?**

Two predictors can share training priors and input evidence. Therefore, calling them different models does not establish independent errors. We will deliberately vary homolog evidence while preserving the exact target protein sequence and ligand chemistry. An experimental reference remains relevant to the unchanged system. This is not a mutation assay or an assumption that a modified ligand must not bind.

The candidate contribution is a controlled decomposition of model diversity versus evidence diversity, plus a deployable reliability score for an unchanged native-top Protenix pose. **MSA subsampling, confidence calibration, consistency metrics and model ensembles are not themselves our inventions.**

## Controlled experimental arms

For every finally eligible system, first lock a native-top Protenix anchor from a separately declared 5-seed × 5-sample run. It must never change between arms or be replaced by whichever output scores best against experiment.

Construct two MSA views V0/V1 with the same query and the same number of homolog rows, drawn from nonoverlapping externally supplied sequence clusters in a common alignment pool. Keep all templates disabled in these opinion runs, and keep chemistry, chain composition, steps and recycling settings fixed within each predictor. Query-only controls and template interventions are secondary extensions, not confounded changes in the primary experiment.

| Arm | Two opinion runs | What changes |
|---|---|---|
| Same model / same evidence | Protenix V0 seed A; Protenix V0 seed B | Sampling noise only |
| Same model / different evidence | Protenix V0 seed A; Protenix V1 seed B | Evidence view |
| Different models / same evidence | Protenix V0 seed A; Boltz V0 seed B | Predictor |
| Different models / different evidence | Protenix V0 seed A; Boltz V1 seed B | Predictor and evidence view |

Only five unique opinion jobs are needed per randomized block because outputs are shared across arms. Use five prespecified blocks, five samples per job, and select each opinion's native top using only its own prediction-time ranking. That is 125 opinion samples plus 25 anchor samples per system. Blocks and seed pairs must be defined before outcomes. Reusing predictions between arms is deliberate pairing, not independent replication.

Equal sample counts are **not** equal GPU costs across predictors. Record actual hardware, peak memory, GPU seconds and failed runs; distinguish sample-matched comparisons from a later compute-matched sensitivity analysis. No runtime savings can be inferred from archive download or local analysis time.

The existing releases remain useful for curation, software checks and a retrospective ordinary-consensus baseline. The controlled experiment needs new team-run predictions. Use one verified common model/checkpoint configuration across the new main and external runs; do not silently combine released Protenix0.3.4 main outputs and Protenix1.0.0 external outputs as a pure biological shift. Candidate planning versions are Protenix1.0.0 and Boltz2.0.3; these remain blocked until runner/weight/input compatibility is verified.

## Proposed diagnostic and method

For each opinion, calculate input-mapped ligand agreement with the fixed anchor after receptor-only alignment, plus residue-contact agreement. Summarize the five blocks before training, leaving one observation per system.

The proposed diagnostic is **evidence fragility**: the change in anchor support when shared-evidence opinions are replaced with matched-depth, cluster-disjoint-evidence opinions. Preserve both absolute support and the change; a large drop is a warning feature, not proof that the anchor is wrong. Agreement that survives diversification is also not proof of correctness.

Important identifiability point: a difference between two support scores contains no new information once both component scores are given. Fragility is an interpretable parameterization, not a magically more informative metric. The substantive hypothesis concerns the value of the newly generated diversified-evidence predictions, compared with a strong baseline lacking those geometry measurements. Include a full-component-score control; do not count collinearity or regularization effects from adding an algebraic contrast as a separate methodological discovery.

Initial implementation now exists in `evidence_factorial_features.py`. For a two-opinion arm, contact support is the minimum of the two opinion-to-anchor Jaccards; distance burden is the maximum of the two receptor-aligned opinion-to-anchor ligand RMSDs. Contact fragility is shared-view support minus diversified-view support; distance fragility uses the opposite distance subtraction so positive values mean a loss of support. The contrast of the two model-specific fragilities is an input feature, not an estimated causal effect on correctness. The code requires all five prespecified blocks and leaves a feature missing if a required contact measurement is missing; it does not silently average only favorable/available blocks. Three synthetic tests verify the arithmetic, fixed-anchor/view/seed constraints and outcome exclusion.

These are **anchor-support** measures, not direct opinion-to-opinion distances. The latter require independent pairwise measurement; two distances to an anchor cannot reconstruct mutual RMSD. Include all five opinion confidence signals in the strongest common-feature control when isolating the added value of geometry. That control needs the full opinion panel too; it is not a cheap two-call deployment or evidence of cost savings.

Fit an interpretable reliability model using these features, with a prespecified nonlinear sensitivity model. The strongest baseline already includes anchor native confidence, reference-free validity, within-anchor ordinary-sample dispersion, and all available opinion confidence fields. This prevents an apparent benefit arising merely from obtaining more confidence scores or more samples. Compare confidence-only opinions, ordinary consistency, and evidence-diversified consistency on identical systems.

A secondary extension is an acquisition gate that requests extra opinions only when expected decision value is high. Generic cascades are not novel; add this extension only if the core diagnostic succeeds and an independently validated cost tradeoff is demonstrated. Do not make two weak contributions substitute for one convincing result.

## What would make the study stand out

1. Show whether model diversity and evidence diversity contribute separately to detecting an anchor's errors, rather than merely to producing a best-of-many pose.
2. Directly quantify **false consensus**: strong prediction-to-prediction agreement accompanying experimentally incorrect anchor placement. Compare it across the four arms without conditioning the entire study on only easy or agreeing cases.
3. Demonstrate incremental reliability beyond confidence, physical checks and ordinary same-model diversity, with an openly reproducible mapping/native-selection pipeline.
4. Freeze a grouped main test and transfer the unchanged rule to the independently curated external campaign. Report compound-cluster uncertainty and the single-family limitation; do not turn927 raw identifiers into927 independent compounds.

These are hypotheses and required demonstrations. The data might show that evidence diversification makes agreement less useful, or that ordinary sampling is sufficient. Those outcomes must be reported, not repaired by selecting a new intervention on the test set.

## Validation and go/no-go criteria

Use full eligible cohorts, not a favorable handpicked demonstration. Resolve receptor groups, repeated chemicals, shallow MSAs, short peptide partners, covalency and alternate reference poses using outcome-independent rules. A provisional depth of128 nonquery cluster representatives per view requires at least256 eligible clusters; shallow alignments get an explicit separate stratum or preregistered lower-depth design, never outcome-guided exemptions. The number of eligible independent groups may constrain the achievable certainty.

The primary analysis is paired incremental error–coverage performance for the fixed anchor, with family/group-held-out validation. Name one operating point and a smallest practically relevant improvement before labels; a provisional10% accepted-error target is not a guaranteed error bound or an already frozen threshold. Also report complete curves, calibration and costs. Bootstrap independent receptor groups, not samples or seed replicates. Keep external repeated chemical identities together and include scaffold sensitivity analyses.

Do not label any risk control distribution-free under arbitrary dataset/model shift. Do not claim cluster-disjoint MSAs are statistically independent or that an intervention proves memorization caused an error. Randomization identifies the effect of the specified evidence-selection procedure, not a unique biological explanation.

For a strong journal submission, require a stable held-out advantage over the strongest baseline, meaningful uncertainty, a useful failure-mode analysis and honest transfer results. If benefit disappears with confidence/within-model controls, the proposed method contribution fails its principal test. A negative finding may still be useful but does not earn a high-confidence TCBB acceptance claim.

## Prior-work boundary and unresolved novelty audit

Input-only grouping feasibility now exposes a major constraint: joint receptor+scaffold components connect505/681 chemistry-resolved candidates into one component; receptor+exact identity grouping yields126 components, largest251. Thus a balanced five-fold, jointly scaffold-cold test is not available under these draft links. See grouping-feasibility.md before choosing the final estimand and splits. Do not split/drop the giant component or tune grouping after outcomes. These are draft input-group counts, not accuracy results, final eligibility or proven independent families.

- PLI-Parallax already supplies calibrated agreement, grouped validation and transfer analyses. Its cached author technical methods were reviewed; full-preprint review remains incomplete. Our proposed distinction is the controlled evidence/model factorial and fixed-anchor diagnostic, not consensus calibration. [Author resource](https://huggingface.co/datasets/ThorKl/PLI-parallax).
- Boltz-Perturb perturbs conditioning to improve sampling and compares MSA-based baselines. Its author repository was reviewed; blocked paper endpoints mean the complete methods overlap still needs resolution. We cannot claim that MSA perturbation is new or absent from that work. [Author repository](https://github.com/MSDLLCpapers/boltz-perturb).
- Published cofolding robustness work tests binding-site/ligand perturbations and recommends repeated/input-perturbed checks. Our unchanged chemistry/sequence and calibrated anchor-reliability objective are a proposed distinction, not a finding that all robustness testing is new. [Primary article, methods](https://www.nature.com/articles/s41467-025-63947-5).
- COFOLDER already exposes reference-free repeat-consistency/robustness diagnostics with explicit evidence regimes. Those implementation patterns are not novelty claims for us. [Author documentation](https://cddleiden.github.io/COFOLDER/user-guide/validate/), [metric contract](https://cddleiden.github.io/COFOLDER/user-guide/metric-reference/).
- MCTH already uses multi-expert uncertainty/agreement in finite-budget sequence–structure co-design. Its methods describe changing design sequences and allocating folding calls. That is different from certifying a fixed input/anchor pose, but rules out claiming adaptive multi-model allocation in general. [Full methods and appendices](https://arxiv.org/html/2608.17381v1).

Full papers/code for ACER, PLI-Parallax, Boltz-Perturb and COPAL still require a precise comparison before any “first” claim. Search failure or an inaccessible paper is not evidence of absence.

Further boundary check: PLI-Parallax already includes BOTH Boltz-2 single-sequence and MSA modes and explicitly warns that shared training/architectures can agree while wrong. Evidence-mode diversity and the false-consensus concern are therefore also occupied concepts. Partial indexed ACER methods describe local-ensemble consistency combined with absolute native confidence; direct full-paper access remains blocked. The candidate distinction is the controlled matched-depth factorial and its incremental fixed-anchor test, not those broad ideas. See closest-work-review.md for exact access scope and sources.

## Work started and teammate package

`work/study/evidence_views.py` implements deterministic cluster-disjoint view construction, alignment/query checks, deduplication, insertion preservation and content hashes, with synthetic tests. It does not fabricate cluster labels or download MSAs. Supplied cluster assignments must be validated by the team's recorded clustering job.

Clustering metadata must include the exact query and its cluster membership. The entire query-containing cluster is excluded from the homolog sampling pool, not merely the exact query row; the unchanged query is then inserted into both views as the common target. Missing/inconsistent query membership is rejected. This deliberately removes a potential near-query duplication asymmetry but may reduce eligibility at the proposed depth. It still does not establish statistical independence between the evidence views or their training priors.

`work/study/build_evidence_experiment_plan.py` emits blocked job specifications and counts from all877 candidate input plans. These are NOT working predictor CLI commands, GPU-hour estimates, submissions or completed runs. Model wrappers, real MSA pool/cluster hashes, exact chemical/chain inputs, container/weights, native outputs and reference eligibility must be verified before launch. Teammates can generate predictions remotely and return compact confidence/measurement/provenance artifacts. No external messages or GPU jobs have been sent by this chat.

Local storage remains below15GB: no model weights or MSA collections here; new all-sample measurements should be streamed to compact records rather than retaining every coordinate. This plan changes the required experiments, not the outcome-protection rules or independent-student-work disclosure.

Detailed local handoff is now in controlled-experiment-handoff.md. A crucial launch gate is evidence equivalence AFTER runner preprocessing: provided A3M files alone cannot prove that the models consumed the declared shared/diversified rows. Require chain-aware pairing/copy semantics, effective row/deletion-feature audits and clustering provenance, or keep the intended causal contrast unresolved. This is a design requirement, not an implemented predictor wrapper or permission to launch jobs.
