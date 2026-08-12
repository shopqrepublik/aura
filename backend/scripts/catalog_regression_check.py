"""
Local, no-network regression checks for the DB-backed catalog transition.

This uses DEMO_ARTWORKS as the known-good fixture source but exercises the
new function signatures: candidates are supplied by the caller, as the DB
repository does at runtime.
"""
import os
import sys

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

import app.main as backend  # noqa: E402


def _candidates(museum_id: str) -> list[dict]:
    return [row for row in backend.DEMO_ARTWORKS if row["museum_id"] == museum_id]


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_recognition_case(candidate: dict, museum_id: str, candidates: list[dict], expected_id: str | None) -> None:
    original_open = backend.recognize_open
    original_verify = backend.visual_verify_single_candidate
    original_topn = backend.verify_top_candidates_with_openai
    try:
        backend.recognize_open = lambda image_base64, scoped_museum_id: {
            "artist": candidate.get("artist"),
            "title": candidate.get("title"),
            "confidence": 0.96,
        }
        backend.visual_verify_single_candidate = lambda image_base64, visual_candidate: {
            "is_match": visual_candidate["id"] == expected_id,
            "confidence": 0.95,
        }
        backend.verify_top_candidates_with_openai = lambda image_base64, vision, ranked: {
            "decision": "MATCH" if expected_id else "NO_MATCH",
            "chosen_id": expected_id,
            "confidence": 0.95 if expected_id else 0.0,
            "runner_up": None,
            "reason": "mocked regression verifier",
            "observable_evidence": [],
        }
        result = backend.recognize_with_vision("dummy-image", museum_id, None, candidates)
    finally:
        backend.recognize_open = original_open
        backend.visual_verify_single_candidate = original_verify
        backend.verify_top_candidates_with_openai = original_topn

    if expected_id is None:
        _assert(result.get("artwork_id") is None, f"expected no match for {museum_id}, got {result}")
    else:
        _assert(result.get("artwork_id") == expected_id, f"expected {expected_id}, got {result}")


def main() -> None:
    orsay = _candidates("orsay")
    orangerie = _candidates("orangerie")
    louvre: list[dict] = []

    _assert(len(orsay) == 101, f"expected 101 Orsay DEMO records, found {len(orsay)}")
    _assert(len(orangerie) == 15, f"expected 15 Orangerie DEMO records, found {len(orangerie)}")

    for row in backend.DEMO_ARTWORKS:
        scoped = _candidates(row["museum_id"])
        match, score, _runner = backend.fuzzy_match_catalog(row["artist"], row["title"], scoped)
        _assert(match is not None, f"no fuzzy match for {row['id']}")
        _assert(match["id"] == row["id"], f"fuzzy parity failed for {row['id']}: got {match['id']} score={score}")

    orsay_fixture = next(row for row in orsay if row["id"] == "orsay_rf_644")
    orangerie_fixture = next(row for row in orangerie if row["id"] == "orangerie_rf_1960_44")

    _run_recognition_case(orsay_fixture, "orsay", orsay, "orsay_rf_644")
    _run_recognition_case(orsay_fixture, "orangerie", orangerie, None)
    _run_recognition_case(orangerie_fixture, "orangerie", orangerie, "orangerie_rf_1960_44")
    _run_recognition_case(orangerie_fixture, "orsay", orsay, None)
    _run_recognition_case(orsay_fixture, "louvre", louvre, None)

    null_artist_candidate = {
        "id": "louvre_null_artist_fixture",
        "museum_id": "louvre",
        "artist": None,
        "title": "Fragment of a Sarcophagus",
        "year": None,
        "image_url": "http://example.invalid/reference.jpg",
    }
    _run_recognition_case(null_artist_candidate, "louvre", [null_artist_candidate], "louvre_null_artist_fixture")

    print("catalog_regression_check=ok")
    print("demo_parity=116/116")
    print("orsay_wrong_museum=no_match")
    print("orangerie_wrong_museum=no_match")
    print("louvre_before_import=no_candidates")
    print("null_artist=title_match_ok")


if __name__ == "__main__":
    main()
