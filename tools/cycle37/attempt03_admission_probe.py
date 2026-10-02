r"""Cycle #37 — Attempt #3 — replay the MF37A02-02/03 counterexamples through a source or installed consumer.

``python attempt03_admission_probe.py --mode source --import-root <worktree>/src --scratch DIR --out FILE``
``<wheel venv python> attempt03_admission_probe.py --mode installed --scratch DIR --out FILE``

Runs, in one interpreter, against whichever ``aggie_analytics`` that interpreter resolves:

* the Attempt #2 manager's scoring probe cases (``probe_admission.py``) and PIT probe cases (``probe_pit.py``),
  with the same inputs;
* a positive path with real bytes in a test-only fixture store under ``--scratch``;
* the negative classes the closure names: missing/tampered bytes, invented digest, absent or mismatched
  bindings, same teams, nonfinite probability, invalid scores/times/final provenance (scoring); unrelated,
  omitted, extra, conflicting, tampered, future/unknown publication and fabricated classification (PIT).

Every case has a declared expectation; the receipt records each observed state and whether it matched, the
exact module files and SHA-256 the calls used, and the proof that real eligibility stays zero
(``DECLARED_DURABLE_STORES`` is empty). ``--mode installed`` refuses to run if the package resolves inside a Git
checkout, and ``--mode source`` refuses unless it resolves inside ``--import-root``.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("source", "installed"), required=True)
    parser.add_argument("--import-root", type=Path)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.mode == "source":
        if not args.import_root:
            raise SystemExit("--mode source needs --import-root")
        sys.path.insert(0, str(args.import_root.resolve()))

    from aggie_analytics.cycle36 import kernel_reference as k
    from aggie_analytics.cycle36 import scoring_guards as g
    from aggie_analytics.cycle37 import receipt_authority as ra
    from aggie_analytics.cycle37.receipt_fixtures import bind_final, bind_forecast, fixture_authority, prior_receipt

    modules = {m.__name__: {"file": str(Path(m.__file__).resolve()), "sha256": sha256(Path(m.__file__))}
               for m in (g, k, ra)}
    origin = Path(g.__file__).resolve()
    in_checkout = any((parent / ".git").exists() for parent in origin.parents)
    if args.mode == "installed" and in_checkout:
        raise SystemExit(f"--mode installed resolved {origin}, which is inside a Git checkout")
    if args.mode == "source" and args.import_root.resolve() not in origin.parents:
        raise SystemExit(f"--mode source resolved {origin}, outside {args.import_root}")

    args.scratch.mkdir(parents=True, exist_ok=True)
    authority = fixture_authority(args.scratch / "fixture_store", f"a03-{args.mode}-probe")
    cases: list[dict] = []

    def case(family: str, name: str, expected, fn) -> None:
        try:
            value = fn()
            observed = value.get("state") if isinstance(value, dict) else value
            if isinstance(value, dict) and "successor_state" in value:
                observed = (value["successor_state"] if value["successor_state"] == k.PIT_PROVEN
                            else (value.get("receipt_validation") or {}).get("code") or value["successor_state"])
        except Exception as error:  # noqa: BLE001 - a raise is an outcome, and never an admission
            observed = f"RAISED:{type(error).__name__}:{error}"
        cases.append({"family": family, "case": name, "expected": expected, "observed": observed,
                      "matches": observed == expected})

    # ------------------------------------------------------------------ scoring: the manager's probe
    f = g.FrozenForecast(contest_id="MANAGER-FIXTURE-ONLY", model_identity="asserted-model",
                         input_identity="asserted-input", designated_home_team="A", designated_away_team="B",
                         home_win_probability=0.7, freeze_known_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
                         cutoff_utc=datetime(2026, 9, 2, tzinfo=timezone.utc), receipt_digest="a" * 64,
                         packet_bytes_digest="b" * 64)
    z = g.OfficialFinal(contest_id=f.contest_id, home_team="A", away_team="B", home_points=21, away_points=14,
                        lifecycle="FINAL", observed_at=None)
    manager = "manager_ADMISSION_PROBE"
    case(manager, "invented_digests_no_receipt_bytes_no_final_provenance", g.NO_AUTHORITY,
         lambda: g.admit_for_scoring(f, z))
    case(manager, "explicit_mismatched_model_positive_refusal", g.MODEL_MISMATCH,
         lambda: g.admit_for_scoring(f, z, receipt_model_identity="other"))
    case(manager, "nan_probability_positive_refusal", g.INVALID_PROBABILITY,
         lambda: g.admit_for_scoring(dataclasses.replace(f, home_win_probability=float("nan")), z))
    case(manager, "missing_timezone", g.INVALID_INSTANT,
         lambda: g.admit_for_scoring(dataclasses.replace(f, freeze_known_at=datetime(2026, 9, 1),
                                                         cutoff_utc=datetime(2026, 9, 2)), z))
    case(manager, "mixed_timezone", g.INVALID_INSTANT,
         lambda: g.admit_for_scoring(dataclasses.replace(f, freeze_known_at=datetime(2026, 9, 1)), z))
    case(manager, "same_team_both_sides", g.PARTICIPANTS_NOT_DISTINCT,
         lambda: g.admit_for_scoring(dataclasses.replace(f, designated_away_team="A"),
                                     dataclasses.replace(z, away_team="A")))
    case(manager, "invented_digests_with_an_authority", g.RECEIPT_NOT_VERIFIED,
         lambda: g.admit_for_scoring(f, z, authority=authority))

    # ------------------------------------------------------------------ scoring: positive and negatives
    cutoff = datetime(2026, 9, 2, tzinfo=timezone.utc)
    base_f = g.FrozenForecast(contest_id="A03-FIXTURE", model_identity="m", input_identity="i",
                              designated_home_team="HOME", designated_away_team="AWAY", home_win_probability=0.6,
                              freeze_known_at=cutoff - timedelta(hours=3), cutoff_utc=cutoff, receipt_digest=None,
                              packet_bytes_digest=None, neutral_site=False)
    base_z = g.OfficialFinal(contest_id="A03-FIXTURE", home_team="HOME", away_team="AWAY", home_points=28,
                             away_points=24, lifecycle="FINAL", observed_at=cutoff + timedelta(hours=4),
                             neutral_site=False)
    bf, bz = bind_forecast(authority.root, base_f), bind_final(authority.root, base_z)
    scoring = "scoring_matrix"
    case(scoring, "positive_verified_fixture", g.ADMITTED, lambda: g.admit_for_scoring(bf, bz, authority=authority))
    case(scoring, "positive_is_labelled_test_only", ra.TEST_ONLY,
         lambda: g.admit_for_scoring(bf, bz, authority=authority)["authority_class"])
    case(scoring, "positive_counts_as_real_eligible", False,
         lambda: g.admit_for_scoring(bf, bz, authority=authority)["counts_as_real_eligible_forecast"])
    # The receipt is present in the authority but the packet bytes it attests are not.
    orphan = bind_forecast(args.scratch / "other_store", dataclasses.replace(base_f, input_identity="i-orphan"))
    orphan_receipt = (args.scratch / "other_store" / "receipts" / f"{orphan.receipt_digest}.json").read_bytes()
    (authority.root / "receipts" / f"{orphan.receipt_digest}.json").write_bytes(orphan_receipt)
    case(scoring, "missing_packet_bytes", g.RECEIPT_NOT_VERIFIED,
         lambda: g.admit_for_scoring(orphan, bz, authority=authority))
    tampered = bind_forecast(authority.root, dataclasses.replace(base_f, input_identity="i-tamper"))
    (authority.root / "payloads" / f"{tampered.packet_bytes_digest}.bin").write_bytes(b"{}")
    case(scoring, "tampered_packet_bytes", g.RECEIPT_NOT_VERIFIED,
         lambda: g.admit_for_scoring(tampered, bz, authority=authority))
    for label, change, expected in (
        ("mismatched_model_binding", {"model_identity": "m2"}, g.MODEL_MISMATCH),
        ("mismatched_input_binding", {"input_identity": "i2"}, g.MODEL_MISMATCH),
        ("mismatched_cutoff_binding", {"cutoff_utc": cutoff + timedelta(minutes=5)}, g.RECEIPT_BINDING_MISMATCH),
        ("probability_not_the_frozen_bytes", {"home_win_probability": 0.61}, g.PACKET_NOT_BOUND),
        ("nonfinite_probability", {"home_win_probability": float("inf")}, g.INVALID_PROBABILITY),
        ("naive_freeze_time", {"freeze_known_at": datetime(2026, 9, 1)}, g.INVALID_INSTANT),
        ("same_teams", {"designated_away_team": "HOME"}, g.PARTICIPANTS_NOT_DISTINCT),
    ):
        case(scoring, label, expected,
             lambda c=change: g.admit_for_scoring(dataclasses.replace(bf, **c), bz, authority=authority))
    for label, change, expected in (
        ("final_without_provenance", {"source_receipt_digest": None}, g.FINAL_NO_PROVENANCE),
        ("final_score_not_its_receipt", {"home_points": 30}, g.FINAL_PROVENANCE_MISMATCH),
        ("invalid_final_score", {"home_points": -3}, g.INVALID_SCORE),
        ("naive_final_time", {"observed_at": datetime(2026, 9, 3)}, g.INVALID_INSTANT),
        ("not_final", {"lifecycle": "IN_PROGRESS"}, g.NOT_FINAL),
    ):
        case(scoring, label, expected,
             lambda c=change: g.admit_for_scoring(bf, dataclasses.replace(bz, **c), authority=authority))
    packet = {"contest_id": bf.contest_id, "model_identity": bf.model_identity, "input_identity": bf.input_identity,
              "packet_bytes_digest": bf.packet_bytes_digest, "receipt_digest": bf.receipt_digest,
              "freeze_known_at": bf.freeze_known_at.isoformat(), "cutoff_utc": cutoff.isoformat()}
    case(scoring, "packet_eligibility_verified", "ELIGIBLE_SUBJECT_TO_THE_JOIN_GUARDS",
         lambda: g.packet_eligibility(packet, authority=authority))
    case(scoring, "packet_eligibility_without_authority", "INELIGIBLE_NO_TRUSTED_RECEIPT_AUTHORITY",
         lambda: g.packet_eligibility(packet))

    # ------------------------------------------------------------------ PIT: the manager's probe
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    row = {"canonical_game_id": "MANAGER-FIXTURE-ONLY", "cutoff_utc": cutoff.isoformat(),
           "authority_class": "RETROSPECTIVE", "prior_observation_ids": ["REQUIRED-PRIOR"]}
    receipt = {"source_id": "SELF-ASSERTED", "payload_sha256": "a" * 64, "published_at_utc": "2026-09-01T00:00:00Z",
               "known_at_utc": "2026-09-01T01:00:00Z", "prior_observation_ids": ["UNRELATED-PRIOR"]}
    manager_pit = "manager_PIT_PROBE"
    for label, offered, expected in (
        ("fabricated_bytes_unrelated_prior", receipt, k.REFUSED_PRIOR_NOT_ATTESTED),
        ("missing_digest_positive_refusal", {**receipt, "payload_sha256": ""}, "REFUSED_RECEIPT_MISSING_REQUIRED_FIELDS"),
        ("late_receipt_positive_refusal", {**receipt, "known_at_utc": "2026-09-03T00:00:00Z"},
         "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF"),
    ):
        receipts = {row["canonical_game_id"]: offered}
        case(manager_pit, label, expected, lambda r=receipts: k.classify_pit(row, r, cutoff_utc=cutoff, now=now))
        case(manager_pit, label + "_standalone_gate", False,
             lambda r=receipts: k.admit_to_pit_consumer(k.classify_pit(row, r, cutoff_utc=cutoff, now=now), now=now))
        case(manager_pit, label + "_row_bound_gate", False,
             lambda r=receipts: k.admit_to_pit_consumer(k.classify_pit(row, r, cutoff_utc=cutoff, now=now), row=row,
                                                        receipts_by_game=r, cutoff_utc=cutoff, now=now))

    # ------------------------------------------------------------------ PIT: positive and negatives
    pit_row = {"canonical_game_id": "A03-TARGET", "cutoff_utc": cutoff.isoformat(),
               "authority_class": "PROVEN_PIT_TRAINING_ROW", "prior_observation_ids": ["P1", "P2"]}
    published, known = cutoff - timedelta(days=2), cutoff - timedelta(days=1)

    def prior(priors, **kw):
        digest, stored = prior_receipt(authority.root, priors=priors, published_at=kw.pop("published", published),
                                       known_at=kw.pop("known", known), **kw)
        return digest, {**stored, "receipt_digest": digest}

    good, good_claim = prior(["P1", "P2"])
    target = pit_row["canonical_game_id"]
    pit = "pit_matrix"
    case(pit, "positive_verified_consumed_set", k.PIT_PROVEN,
         lambda: k.classify_pit(pit_row, {target: good_claim}, now=now, authority=authority))
    case(pit, "positive_row_bound_gate", True, lambda: k.admit_to_pit_consumer(
        k.classify_pit(pit_row, {target: good_claim}, now=now, authority=authority), row=pit_row,
        receipts_by_game={target: good_claim}, now=now, authority=authority))
    case(pit, "positive_counts_as_real_pit_proof", False, lambda: k.classify_pit(
        pit_row, {target: good_claim}, now=now, authority=authority)["counts_as_real_pit_proof"])
    _, unrelated = prior(["UNRELATED"])
    _, omitted = prior(["P1"])
    _, extra = prior(["P1", "P2", "P3"])
    _, future = prior(["P1", "P2"], known=now + timedelta(days=9), published=now + timedelta(days=8))
    _, late = prior(["P1", "P2"], known=cutoff + timedelta(hours=1), published=cutoff)
    one, _ = prior("P1")
    two, _ = prior("P2")
    conflicting, _ = prior("P1", publication=b"a different publication of P1")
    tampered_digest, tampered_claim = prior(["P1", "P2"], extra={"note": "to be altered"})
    tampered_path = authority.root / "receipts" / f"{tampered_digest}.json"
    tampered_path.write_bytes(tampered_path.read_bytes().replace(b"to be altered", b"has been altered"))
    unknown_publication = {k2: v for k2, v in good_claim.items() if k2 != "published_at_utc"}
    for label, receipts, expected in (
        ("unrelated_prior", {target: unrelated}, k.REFUSED_PRIOR_NOT_ATTESTED),
        ("omitted_prior", {target: omitted}, k.REFUSED_PRIOR_NOT_ATTESTED),
        ("extra_prior", {target: extra}, k.REFUSED_PRIOR_NOT_CONSUMED),
        ("conflicting_receipts", {"P1": [one, conflicting], "P2": two}, k.REFUSED_CONFLICTING),
        ("tampered_receipt_bytes", {target: tampered_claim}, "REFUSED_RECEIPT_BYTES_DO_NOT_MATCH_THE_DIGEST"),
        ("future_publication", {target: future}, "REFUSED_INSTANT_IS_IN_THE_FUTURE"),
        ("unknown_publication_time", {target: unknown_publication}, "REFUSED_RECEIPT_MISSING_REQUIRED_FIELDS"),
        ("known_after_cutoff", {target: late}, "REFUSED_RECEIPT_KNOWN_AT_IS_NOT_BEFORE_THE_CUTOFF"),
        ("invented_digest_no_bytes", {target: "c" * 64}, "REFUSED_RECEIPT_BYTES_ABSENT"),
        ("self_asserted_without_digest", {target: {k2: v for k2, v in good_claim.items() if k2 != "receipt_digest"}},
         k.REFUSED_NO_BYTES_IDENTITY),
    ):
        case(pit, label, expected, lambda r=receipts: k.classify_pit(pit_row, r, now=now, authority=authority))
    fabricated = {"canonical_game_id": target, "successor_state": k.PIT_PROVEN, "admissible_to_a_pit_consumer": True,
                  "receipt": good_claim, "consumed_dependencies": ["P1", "P2"]}
    case(pit, "fabricated_classification_standalone", False,
         lambda: k.admit_to_pit_consumer(fabricated, now=now, authority=authority))
    case(pit, "fabricated_classification_against_row_without_receipts", False,
         lambda: k.admit_to_pit_consumer(fabricated, row=pit_row, receipts_by_game={}, now=now, authority=authority))
    case(pit, "no_authority", k.REFUSED_NO_AUTHORITY,
         lambda: k.classify_pit(pit_row, {target: good_claim}, now=now))
    case(pit, "durable_store_not_declared", True, lambda: ra.DECLARED_DURABLE_STORES == ())

    failed = [c for c in cases if not c["matches"]]
    result = {
        "label": "Cycle #37 — Attempt #3 — IN_PROGRESS_LOCAL_WORK_REMAINS", "cycle_number": 37, "attempt_number": 3,
        "mode": args.mode, "interpreter": sys.executable, "python_version": sys.version,
        "modules": modules, "resolved_inside_a_git_checkout": in_checkout,
        "fixture_authority": authority.describe(), "real_eligibility_possible": bool(ra.DECLARED_DURABLE_STORES),
        "cases": cases, "case_count": len(cases), "mismatches": failed, "result": "PASS" if not failed else "FAIL",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "limits": ("Fixture receipts under --scratch only; no real contest, forecast or prior is created or "
                   "admitted. A PASS shows the gate's behaviour on these inputs, not scientific eligibility."),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    for row_out in cases:
        print(("OK  " if row_out["matches"] else "BAD ") + f"{row_out['family']}/{row_out['case']}: {row_out['observed']}")
    print("result:", result["result"], "cases:", len(cases), "mismatches:", len(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
