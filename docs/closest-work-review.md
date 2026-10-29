# Closest work and the remaining research question

Prepared from accessible primary technical documentation and author code on October 26, 2026. This is a source audit, not a claim that the proposed study is novel or that published findings have been reproduced.

## PLI-Parallax

The deposited technical README and validation notebook implement contact agreement, isotonic reliability calibration, protein-grouped validation, filtering curves, and calibration transfer across model training-cutoff eras. These are already occupied contributions. Its validation target averages contact-set accuracy across teacher models; the teacher panel includes Chai-1, Boltz-2 and smina.

Our defensible candidate distinction is the incremental value of agreement for a fixed anchor pose's binary geometric correctness, over both native confidence and reference-free validity, with a second-model-confidence control and separate experimental-campaign validation. The inspected notebook does not show that exact comparison. The full preprint is still inaccessible through the attempted endpoint, so absence from the notebook does not prove absence from the paper or literature.

Sources: [technical README](https://huggingface.co/datasets/ThorKl/PLI-parallax/blob/main/deposit/README.md), especially schema and sections 9–12; [validation notebook](https://huggingface.co/datasets/ThorKl/PLI-parallax/blob/main/notebooks/pli_parallax_validation_notebook.ipynb), source cells 2, 4, 6 and 8. Notebook source was read; downloaded code was not executed. Its published output numbers are not our research results.

## Runs N' Poses

The author preprint already studies generalization, confidence scoring and structural plausibility. The associated extraction notebook confirms that the native ranking score comes from prediction outputs, whereas ligand-specific chain-pair confidence fields use experimentally assigned ligand chains. Those suffixed fields cannot simply become deployable predictors.

The preprint's methods report Protenix 0.3.4 and Boltz-2 2.0.3, with matched MSA inputs, five seeds and five samples per seed. This is source-reported provenance; the exact correspondence to every file in Zenodo v6 still requires verification. The Boltz-2 subset follows a later training cutoff than the original four-model benchmark.

The native top pose must be rechecked against raw ranking/confidence files. The released scoring CSV contains entries conditional on successful experimental scoring and ligand assignment. Taking the highest available score from that table could miss an unscored native-top prediction. Our current top selections are therefore provisional. This is a sample-selection issue, not an observed performance result.

Sources: [author preprint](https://www.researchsquare.com/article/rs-7311192/v1), PDF pages 18–19; [score extraction source](https://github.com/plinder-org/runs-n-poses/blob/197fafc60a5cef3a9e7f8a4b0dac7c965eed3839/extract_scores.ipynb), functions process_boltz_file and process_protenix_file; [data release](https://zenodo.org/records/18366081).

## OpenBind

The chosen external resource is a separate protease campaign. Its inference repository and released archive provide the path to raw predictions; matching exact checkpoints and input modes to Runs N' Poses is unresolved. A later OpenBind model-release blog uses Protenix-v1-20250630, but that alone does not identify the Protenix checkpoint in the selected earlier archive. Do not silently attach the later release's version label to the earlier files.

Direct inspection of `run_protenix_monomer_no-pair/submit_protenix.sh` inside the selected release now establishes an explicit launch argument: `-n protenix_base_default_v1.0.0`, with the same five listed seeds. This is stronger than inferring a checkpoint from a later blog, but it is a model-name argument, not a verified weight digest or complete environment. The corresponding Boltz launch script requests five diffusion samples; its saved prediction hparams report three recycling steps and 200 sampling steps. These are not the main preprint's matched ten-recycle settings. Main-versus-external comparisons therefore require a configuration-shift caveat even before exact software/checkpoint reconciliation is complete.

The archived processing script also invokes a ligand-conversion utility whose source can repair bond orders from Fragalysis chemical templates. Consequently, reformatted ligand SDFs cannot automatically be treated as untouched predictor chemistry/validity outputs. Raw model CIFs and input-derived chemical provenance are preferred; use of chemical metadata must be distinguished from use of experimental geometry or correctness.

If compatibility fails, external results can describe transport across both dataset and prediction-configuration changes; they cannot isolate biological distribution shift. The study can still ask a practical reliability question, with narrower attribution.

Sources: [benchmark repository](https://github.com/OpenBind-Consortium/EV-A71_2A_benchmark), [inference/evaluation repository](https://github.com/OmeirK/cofolding_evaluation), [selected archive](https://zenodo.org/records/20798528), [later model-release blog](https://openbind.uk/news/blog-openbind-0-advancing-open-molecular-structure-prediction/).

## Consequence for the study

Additional primary literature located during the overnight audit reinforces that consensus itself is not new. MULTICOM_ligand uses structural-consensus pose ranking together with chemical/structural filters and later confidence assessment. Its task is selecting ensemble poses, rather than testing incremental reliability for one predictor's unchanged native-top pose. That distinction is a proposed study framing, not proof of novelty. [Primary article](https://pmc.ncbi.nlm.nih.gov/articles/PMC12353915/), [author repository](https://github.com/BioinfoMachineLearning/MULTICOM_ligand).

COPAL reports multi-model rank aggregation for LuxR ligand preference and an association between inter-model agreement and ranking accuracy. Its abstract concerns receptor–ligand specificity ranking, not the proposed fixed-pose geometric-success comparison. Full-method review is still needed; the abstract alone cannot rule out overlap. [Author preprint record and abstract](https://pubmed.ncbi.nlm.nih.gov/42818562/), DOI 10.64898/2026.09.04.749498. Secondary indexing gave inconsistent dates; the primary record identifies the September 2026 preprint, so do not label it a new October discovery.

A separate reliability-aware multi-engine fusion preprint concerns binding affinity and uncertainty-based filtering, not structural pose correctness. It is relevant background, not a directly interchangeable endpoint. [Author preprint](https://arxiv.org/abs/2607.17601). This study must consistently distinguish pose reliability, affinity prediction and ligand-preference ranking.

Keep the fixed-pose comparison and strong baseline. Do not claim to invent agreement calibration, filtering curves, grouped validation, or temporal transfer. Complete raw-ranking provenance and exact release-version reconciliation before freezing the statistical test. The literature audit has identified a plausible narrower question, not established publication-level novelty.

## October28 redesign audit: ACER code access

The official [ACER repository](https://github.com/molML/acer) describes pocket exploration and pose ranking; its README currently states that code will be available soon. A bounded official API tree inspection pinned commitfe68c40d32304c6b187f5885b0927d72e97b90e1: a30-byte README and a `boltz` gitlink, not an inspectable implementation tree. The gitlink browser route returned404. This is an access/provenance finding, NOT evidence that ACER lacks evidence diversification or our proposed contrast. Full-method overlap remains unresolved. Do not market MSA diversity, ensemble agreement or confidence-weighted ranking as new based on this access limitation. Source tree/hash is recorded in sources/acer_repository_tree_20261028.json and the download ledger.

## October28,09:25UTC access and overlap clarification

Re-read cached PLI-Parallax README lines29–45 and technical schema's system_reliability section: its panel explicitly contains Boltz-2 single-sequence AND Boltz-2 with a ColabFold MSA, not only different predictor architectures. Its schema explicitly warns of jointly wrong agreement under shared architecture/training data. Thus neither mixing evidence modes nor warning about false consensus is a new contribution here. The proposed narrower experiment is the repeated, depth-matched cluster-disjoint evidence/model factorial for one unchanged anchor, evaluated beyond a full-confidence/component control. Whether that exact design is absent from all prior methods remains unproven. [Author README](https://huggingface.co/datasets/ThorKl/PLI-parallax/blob/main/README.md), [deposited technical schema](https://huggingface.co/datasets/ThorKl/PLI-parallax/blob/main/deposit/README.md).

The search-indexed primary ACER v2 page exposes methods3.2: pocket-local ensemble ranking combines native confidence with Gaussian/Lorentzian weights based on standardized ensemble scores; its introduction describes decoy conditioning and repulsive steering. This is closer overlap than a generic ensemble citation. Direct full-page access still returned403, so this is PARTIAL indexed-method evidence, not a completed full-paper/code review. Do not claim confidence-weighted consistency or stable-pocket ranking as new. [Primary ACER v2 methods](https://www.biorxiv.org/content/10.64898/2026.06.02.728568v2.full).

Official COPAL PMC page is abstract-only and explicitly directs full text to the preprint server; having a PMCID does not mean its full methods were inspected. PLI-Parallax full-preprint endpoint remained inaccessible. Both full-method reviews remain open; access failures do not establish novelty. [COPAL PMC availability statement](https://pmc.ncbi.nlm.nih.gov/articles/PMC13622532/).
