# Recognition Benchmarking

Status: CURRENT practice and required standard.

## Existing tooling

`backend/scripts/latency_test.py`, catalog regression/parity checks, reference-cache tooling and many `backend/scripts/louvre_*benchmark*.py` scripts exist. Louvre scripts are research/operations tools, not a universal framework. Some call OpenAI/Wikimedia and create local outputs; some import/migrate. Read CLI/source and target DB before execution.

National Gallery controlled tooling is `backend/scripts/national_gallery_select_controlled_catalog.py`, `backend/scripts/national_gallery_prepare_recognition_corpus.py`, `backend/scripts/national_gallery_finalize_recognition_readiness.py`, `backend/scripts/national_gallery_recognition_benchmark.py`, `backend/scripts/national_gallery_hard_negative_benchmark.py`, and `backend/scripts/national_gallery_controlled_preview.py`. Corpus/benchmark output is ignored under `exports/`; only tooling, frozen metadata/selection input and dated aggregate reports belong in Git. The benchmark runner keeps the candidate snapshot/selection separate from test manifests so out-of-catalog behavior is testable without contaminating the controlled universe. The current controlled version is `ng-controlled-1000-v1-retrieval`; see [the dated report](NATIONAL_GALLERY_CONTROLLED_1000_BENCHMARK_2026-08-24.md).

Quality-recovery diagnostics add `national_gallery_reference_asset_audit.py`, `national_gallery_population_quality_audit.py`, and `national_gallery_visual_retrieval_probe.py`. The production benchmark runner can record stage timings and candidate ranks with `--profile-stages --diagnose-retrieval`. Retrieval recall@1/3/5/10/20 must be reported separately from final verified recognition: a descriptor hit is never a successful recognition. Current runtime version `ng-controlled-1000-v1-retrieval` preserves the prior 500 works and unchanged thresholds while bounding expensive verification to one call with at most three references.

## Benchmark dimensions

For every activated museum, maintain separately:

- exact reference/self images;
- real gallery captures with crop/glare/angle;
- same-artist/similar-title decoys;
- other-museum works;
- labels, rooms, blank walls and non-art objects;
- uncataloged but identifiable works;
- low-quality/network/error cases.

Report match, needs-confirmation, no-match, confident-wrong, wrong-museum leakage, p50/p95 latency and AI calls/cost per attempt. Never collapse needs-confirmation into success without showing the policy.

## Safety gates

Confident-wrong and cross-museum leakage are release blockers. Recall targets must be museum/asset-class specific and backed by a frozen manifest. Benchmarks must record code SHA, catalog version, model, thresholds, asset manifest hash, date and network/cache state.

## Production analytics limitations

First-party events began 2026-08-20. Current recognition attempts carry anonymous, session, optional server-derived user, institution, artwork, terminal outcome, visitor resolution, latency and trusted `internal_test` classification. Controlled preview requests use the server-trusted QA token and are excluded from founder KPIs. Historical pre-contract rows remain legacy and cannot be reconstructed; admin results supplement, not replace, frozen controlled benchmarks.
