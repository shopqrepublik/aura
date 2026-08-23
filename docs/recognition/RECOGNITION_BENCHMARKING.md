# Recognition Benchmarking

Status: CURRENT practice and required standard.

## Existing tooling

`backend/scripts/latency_test.py`, catalog regression/parity checks, reference-cache tooling and many `backend/scripts/louvre_*benchmark*.py` scripts exist. Louvre scripts are research/operations tools, not a universal framework. Some call OpenAI/Wikimedia and create local outputs; some import/migrate. Read CLI/source and target DB before execution.

National Gallery controlled tooling is `backend/scripts/national_gallery_prepare_recognition_corpus.py`, `backend/scripts/national_gallery_recognition_benchmark.py`, and `backend/scripts/national_gallery_controlled_preview.py`. Corpus/benchmark output is ignored under `exports/`; only tooling, frozen metadata input and dated aggregate report belong in Git. The benchmark runner keeps the candidate snapshot separate from the test snapshot so out-of-catalog behavior is testable without contaminating the controlled 170-work universe.

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
