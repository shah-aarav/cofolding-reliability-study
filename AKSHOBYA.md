# Akshobya — common runners and external-cohort execution

Your four packages are A1–A4 in WORK_SPLIT.md. Store weights, environments, MSA pools, ensemble coordinates and large intermediate tensors on compute/approved remote storage, not Aarav's30GB workspace or GitHub.

## First deliverable: verified wrapper/evidence contract

Pin actual Protenix/Boltz code commits, container/runtime versions, weight checksums, all inference settings and input identities. Candidate planning versions Protenix1.0.0/Boltz2.0.3 are NOT a working verified installation. Released main outputs use different configurations from the chosen external release; new controlled runs must use common verified configurations to avoid hiding model/configuration shift.

Extract full prediction-time confidence with input-defined chain indices and every native sample score/tie. Experimentally assigned *_rmsd or *_lddt_pli fields are NOT acceptable deployment features. Check native score direction, missing scores and failure behavior without reference labels.

Validate what each model ACTUALLY consumes after MSA cropping, deduplication, pairing, masking, automatic generation and augmentation. Hash raw/processed artifacts and extractor code. evidence_consumption.py checks only supplied normalized single-chain/unpaired records; it does not authenticate tensors or handle multichain pairing. Build/review the real adapters, including deletion/insertion features and homomer copies. Shared A3M filenames do not establish shared evidence.

## External inputs and full runs

Request the full927-ID current-run external queue from the local lead. Prior Boltz selected-seed input checks cover927targets, but Protenix external input identity and final eligibility are not established. Repeated strict identities mean927IDs are not927independent compounds; this is one target-family campaign. Do not use chemically repaired/reference-based SDFs as raw predictor chemistry.

Generate cohort-specific views with the same declared policies and validated wrappers as main. Run the full eligible external factorial only after real input/evidence proof and Aarav's frozen analysis gates. Preserve one separately native-selected Protenix anchor per system; no best-of-experiment selection. Record every failure/retry and actual costs. Small wrapper checks do not replace the full study.

## Shared QA and return

Own the common compact return schema, unit definitions, source/artifact/code identities and actual GPU cost accounting; coordinate with Sathvik so main and external feature semantics match. Export external reference-free features and independently check main feature/native-selection examples. Keep raw artifacts remotely for replay and return bounded compact batches under RETURN_CONTRACT.md. Final statistics/calibration/uncertainty/figures integration are Aarav's local track, not part of this execution repo.
