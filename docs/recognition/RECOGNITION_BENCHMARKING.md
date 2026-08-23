# Recognition Benchmarking

Status: CURRENT practice and required standard.

## Existing tooling

`backend/scripts/latency_test.py`, catalog regression/parity checks, reference-cache tooling and many `backend/scripts/louvre_*benchmark*.py` scripts exist. Louvre scripts are research/operations tools, not a universal framework. Some call OpenAI/Wikimedia and create local outputs; some import/migrate. Read CLI/source and target DB before execution.

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

First-party events began 2026-08-20. Browser attempts are identifiable but currently lack measured latency. Server operations have backend outcomes but no browser identity/correlation ID. Historical stdout cannot reconstruct precise attempts. Admin results therefore supplement, not replace, controlled benchmarking.
