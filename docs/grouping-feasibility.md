# Outcome-free joint grouping feasibility

October28,2026. Draft input-only audit, not a frozen cohort, partition or scientific accuracy result. All877 main candidates are represented using existing draft sequence-relatedness groups and matched proper-input chemical identities. No prediction correctness or experimental reference geometry was examined. Short receptor-chain handling and full chemical/reference eligibility remain unresolved.

build_joint_group_plans.py constructs connected components using receptor-group links PLUS either exact chemical identity or nonempty Murcko scaffold links. Connections are transitive: sharing a receptor with one system and a ligand with another can connect all three. Grouping by a tuple of receptor and chemical IDs would NOT prevent leakage across either axis. Empty scaffolds fall back to exact identity; unrelated acyclic ligands are not joined simply because both scaffolds are empty. Missing chemistry stays explicitly unresolved, not an assertion of chemical separation.

| Draft grouping rule | All877 candidates: groups / largest | Chemistry-resolved681 only: groups / largest |
|---|---:|---:|
| Existing receptor relatedness |230 /255|168 /251|
| Receptor OR exact input identity |188 /255|126 /251|
| Receptor OR nonempty scaffold |152 /569|90 /505|

The196 chemistry-unresolved systems remain in the full manifest. Known-chemistry counts restrict reported component sizes to resolved members while retaining draft receptor connections; they do not establish final eligibility. Exact identity is canonical isomeric input graph identity without salt, charge or tautomer normalization. Nonchiral Murcko scaffold is a specific sensitivity rule, not a universal definition of unseen chemistry. Components are not proven independent evolutionary families.

## Implication before protocol freeze

Joint exact-identity grouping is stricter than receptor-only grouping but already has a component with251/681 resolved systems. Scaffold sensitivity links505/681 systems (about74.2%) into one component. A balanced five-fold partition cannot keep that component intact in a20%-sized test fold. GroupKFold may still execute with very uneven folds; software success does not establish a balanced independent test. Final eligibility may change these sizes: regenerate before freezing.

Do not split the giant component across train/test to make partitions look balanced. Do not remove it, loosen criteria or choose a successful partition after inspecting accuracy. A held-out set excluding this component excludes most currently resolved systems from its test population; state that scope. If it is held out, training can be small; disclose that limitation.

Candidate outcome-independent decision: retain receptor-cold evaluation with explicit chemical-overlap reporting as one estimand; add receptor+exact-identity-cold evaluation where feasible; keep receptor+scaffold-cold evaluation a separate, potentially unbalanced sensitivity analysis. Alternatively choose a genuinely joint-cold primary estimand with full imbalance declared. Neither choice is finalized here. State test population, minimum training/test group requirements and the policy for failed feasibility before labels.

Compute uncertainty by the declared grouping unit, not seeds or raw system count. Do not call126 or90 components effective independent sample sizes without justification; size imbalance and biological dependence matter. OpenBind's single-family repeated-compound campaign cannot repair missing main-study family diversity.

## Artifacts and next steps

manifests/joint_group_plans_draft.jsonl and manifests/joint_group_summary_draft.json preserve all candidates, missing chemistry and hashes. Source receptor-groups SHA2562623891f4d7ad1b5bb899c82de1977d815d3a9d6f31943985b0ff8d26bcda2ca; chemical-inventory SHA256980ff982edcbd966db69a8e6f40ea7ea84497aca02e2eee13d5737e6017ad6ff. Joint manifest SHA25692a46b00071025e3d32fd937df61ac4b8144e3717990fcb6a5959fa2fceec710. Three synthetic tests cover transitivity/order invariance, empty scaffolds, missing chemistry and conflicting metadata.

After final eligibility and short-chain policy are justified, regenerate, choose grouping/estimand, create deterministic outcome-free splits and audit no prohibited edge crosses partitions. Then freeze the protocol before held-out correctness evaluation. No final split or frozen_protocol.json was created here.
