r"""Cycle #37 - Attempt #2 - ACTUAL_STATE

Reproduce MF36-03 and MF36-04 against a chosen source tree.

The probes are the manager's own negative controls, run through the real
consumers rather than through a copy of them:

* scoring: probability 1.8, -0.5, NaN, Infinity, True; a negative score; a
  boolean score; an arbitrary string where a digest belongs;
* PIT: an unrelated truthy dictionary offered as a publication receipt, and a
  forged classification asserting its own admission.

A positive control runs beside each family, because a gate that refuses
everything is not repaired -- it is broken in the other direction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


class _bas_atomic:  # U37-11: atomic writes once this tool has imported the package itself
    @staticmethod
    def _module():
        import sys as _bas_sys

        if "aggie_analytics" not in _bas_sys.modules:
            return None  # never bind the package from another tree before the tool does
        try:
            from aggie_analytics import atomic_io
        except ImportError:
            return None
        return atomic_io

    @classmethod
    def write_text(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_text(path, *args, **kwargs) if module else path.write_text(*args, **kwargs)

    @classmethod
    def write_bytes(cls, path, *args, **kwargs):
        module = cls._module()
        return module.write_bytes(path, *args, **kwargs) if module else path.write_bytes(*args, **kwargs)

    @classmethod
    def open_write(cls, path, *args, **kwargs):
        module = cls._module()
        return module.open_write(path, *args, **kwargs) if module else path.open(*args, **kwargs)


sys.dont_write_bytecode = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()

    src = Path(args.src).resolve()
    import_root = src / "src"
    sys.path.insert(0, str(import_root))
    for name in [m for m in sys.modules if m.startswith("aggie_analytics")]:
        del sys.modules[name]

    from aggie_analytics.cycle36 import kernel_reference, scoring_guards

    for module in (kernel_reference, scoring_guards):
        origin = Path(module.__file__).resolve()
        if src not in origin.parents:
            raise SystemExit(f"import binding failed: {module.__name__} -> {origin}")

    cutoff = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    freeze = cutoff - timedelta(hours=2)
    known = cutoff - timedelta(days=1)
    digest = hashlib.sha256(b"packet").hexdigest()
    receipt_digest = hashlib.sha256(b"receipt").hexdigest()

    def forecast(**overrides: Any) -> Any:
        base = dict(
            contest_id="G1",
            model_identity="M1",
            input_identity="I1",
            designated_home_team="HOME",
            designated_away_team="AWAY",
            home_win_probability=0.6,
            freeze_known_at=freeze,
            cutoff_utc=cutoff,
            receipt_digest=receipt_digest,
            packet_bytes_digest=digest,
        )
        base.update(overrides)
        return scoring_guards.FrozenForecast(**base)

    def final(**overrides: Any) -> Any:
        base = dict(
            contest_id="G1",
            home_team="HOME",
            away_team="AWAY",
            home_points=24,
            away_points=17,
            lifecycle="FINAL",
            observed_at=cutoff + timedelta(hours=6),
        )
        base.update(overrides)
        return scoring_guards.OfficialFinal(**base)

    # Cycle #37 - Attempt #3 (MF37A02-02/03): the gates now resolve digests to bytes through a receipt
    # authority. The positive controls get real bytes in a test-only fixture store (labelled as such); the
    # bare digests of b"packet" and b"receipt" above have none and are what the negatives keep testing.
    import tempfile

    from aggie_analytics.cycle37.receipt_fixtures import bind_final, bind_forecast, fixture_authority, prior_receipt

    fixture_dir = tempfile.TemporaryDirectory()
    authority = fixture_authority(Path(fixture_dir.name) / "store", "mf36-probe-fixture")
    bound_forecast = bind_forecast(authority.root, forecast())
    bound_final = bind_final(authority.root, final())

    result: dict[str, Any] = {
        "label": args.label,
        "cycle_number": 37,
        "attempt_number": 3,
        "state": "ACTUAL_STATE",
        "fixture_authority": authority.describe(),
        "source_tree": str(src),
        "guard_version": scoring_guards.SCORING_GUARD_VERSION,
        "kernel_module": str(Path(kernel_reference.__file__).resolve()),
        "scoring_module": str(Path(scoring_guards.__file__).resolve()),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "scoring": {},
        "pit": {},
        "packet_eligibility": {},
    }

    def record(bucket: str, name: str, fn: Callable[[], Any]) -> None:
        try:
            value = fn()
        except BaseException as error:  # noqa: BLE001 - a raise is also an outcome
            result[bucket][name] = {
                "outcome": "RAISED",
                "error_type": type(error).__name__,
                "error": str(error)[:300],
            }
            return
        if isinstance(value, dict):
            admitted = bool(value.get("admitted") or value.get("eligible"))
            result[bucket][name] = {
                "outcome": "ADMITTED" if admitted else "REFUSED",
                "state": value.get("state"),
                "detail": str(value.get("detail") or "")[:240],
                "brier_component": value.get("brier_component"),
            }
        else:
            result[bucket][name] = {
                "outcome": "ADMITTED" if value else "REFUSED",
                "value": value,
            }

    # ---------------------------------------------------- scoring negatives
    record("scoring", "positive_control",
           lambda: scoring_guards.admit_for_scoring(bound_forecast, bound_final, authority=authority))
    record("scoring", "well_formed_digests_without_bytes",
           lambda: scoring_guards.admit_for_scoring(forecast(), final(), authority=authority))
    for name, probability in (
        ("probability_too_large", 1.8),
        ("probability_negative", -0.5),
        ("probability_nan", float("nan")),
        ("probability_infinite", float("inf")),
        ("probability_boolean", True),
        ("probability_string", "0.6"),
    ):
        record(
            "scoring",
            name,
            lambda p=probability: scoring_guards.admit_for_scoring(
                forecast(home_win_probability=p), final()
            ),
        )
    record(
        "scoring",
        "final_score_negative",
        lambda: scoring_guards.admit_for_scoring(forecast(), final(home_points=-7)),
    )
    record(
        "scoring",
        "final_score_boolean",
        lambda: scoring_guards.admit_for_scoring(forecast(), final(home_points=True)),
    )
    record(
        "scoring",
        "digest_is_an_arbitrary_string",
        lambda: scoring_guards.admit_for_scoring(
            forecast(receipt_digest="yes", packet_bytes_digest="yes"), final()
        ),
    )

    # ------------------------------------------------- packet eligibility
    good_packet = {
        "contest_id": "G1",
        "model_identity": "M1",
        "input_identity": "I1",
        "packet_bytes_digest": digest,
        "receipt_digest": receipt_digest,
        "freeze_known_at": freeze.isoformat(),
        "cutoff_utc": cutoff.isoformat(),
    }
    bound_packet = {**good_packet, "packet_bytes_digest": bound_forecast.packet_bytes_digest,
                    "receipt_digest": bound_forecast.receipt_digest}
    record("packet_eligibility", "positive_control",
           lambda: scoring_guards.packet_eligibility(bound_packet, authority=authority))
    record("packet_eligibility", "well_formed_digests_without_bytes",
           lambda: scoring_guards.packet_eligibility(good_packet, authority=authority))
    record(
        "packet_eligibility",
        "nonsense_nonempty_fields",
        lambda: scoring_guards.packet_eligibility(
            {**good_packet, "packet_bytes_digest": "yes", "receipt_digest": "sure"}
        ),
    )
    record(
        "packet_eligibility",
        "naive_instants",
        lambda: scoring_guards.packet_eligibility(
            {**good_packet, "freeze_known_at": "2026-09-01T10:00:00", "cutoff_utc": "2026-09-01T12:00:00"}
        ),
    )
    record(
        "packet_eligibility",
        "freeze_after_cutoff",
        lambda: scoring_guards.packet_eligibility(
            {**good_packet, "freeze_known_at": (cutoff + timedelta(hours=1)).isoformat()}
        ),
    )

    # ------------------------------------------------------- PIT negatives
    # The row declares the prior its features consumed (P1); a receipt keyed by the row's own contest id
    # names priors, never the target itself.
    row = {"canonical_game_id": "G1", "authority_class": "UNPROVEN", "cutoff_utc": cutoff.isoformat(),
           "prior_observation_ids": ["P1"]}
    verified_digest, verified_receipt = prior_receipt(authority.root, priors="P1",
                                                      published_at=known - timedelta(hours=1), known_at=known)
    valid_receipt = {**verified_receipt, "receipt_digest": verified_digest}

    def classify(receipt: Any, key: str = "G1") -> Any:
        return kernel_reference.classify_pit(row, {key: receipt}, authority=authority)

    record("pit", "positive_control",
           lambda: classify(valid_receipt, key="P1").get("admissible_to_a_pit_consumer"))
    record("pit", "self_asserted_receipt_without_bytes_identity",
           lambda: classify({k: v for k, v in valid_receipt.items() if k != "receipt_digest"}, key="P1").get(
               "admissible_to_a_pit_consumer"))
    record("pit", "truthy_unrelated_dict", lambda: classify({"unrelated": True}).get("admissible_to_a_pit_consumer"))
    record("pit", "truthy_string", lambda: classify("a receipt, honest").get("admissible_to_a_pit_consumer"))
    record("pit", "missing_fields", lambda: classify({"source_id": "SRC-001"}).get("admissible_to_a_pit_consumer"))
    record(
        "pit",
        "receipt_names_another_prior",
        lambda: classify({**valid_receipt, "prior_game_id": "G-OTHER"}).get(
            "admissible_to_a_pit_consumer"
        ),
    )
    record(
        "pit",
        "receipt_known_after_the_cutoff",
        lambda: classify(
            {**valid_receipt, "known_at_utc": (cutoff + timedelta(hours=1)).isoformat()}
        ).get("admissible_to_a_pit_consumer"),
    )
    record(
        "pit",
        "receipt_known_in_the_future",
        lambda: classify(
            {**valid_receipt, "known_at_utc": "2099-01-01T00:00:00+00:00"}
        ).get("admissible_to_a_pit_consumer"),
    )
    record(
        "pit",
        "receipt_digest_is_not_a_digest",
        lambda: classify({**valid_receipt, "payload_sha256": "trust me"}).get(
            "admissible_to_a_pit_consumer"
        ),
    )
    record(
        "pit",
        "forged_consumer_admission",
        lambda: kernel_reference.admit_to_pit_consumer(
            {
                "canonical_game_id": "G1",
                "successor_state": kernel_reference.PIT_PROVEN,
                "admissible_to_a_pit_consumer": True,
            }
        ),
    )
    record(
        "pit",
        "forged_admission_with_a_forged_receipt",
        lambda: kernel_reference.admit_to_pit_consumer(
            {
                "canonical_game_id": "G1",
                "successor_state": kernel_reference.PIT_PROVEN,
                "admissible_to_a_pit_consumer": True,
                "receipt": {"unrelated": True},
                "cutoff_utc": cutoff.isoformat(),
            }
        ),
    )
    record(
        "pit",
        "consumer_positive_control",
        lambda: kernel_reference.admit_to_pit_consumer(
            classify(valid_receipt, key="P1"), row=row, receipts_by_game={"P1": valid_receipt}, authority=authority
        ),
    )

    fixture_dir.cleanup()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _bas_atomic.write_text(out, json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    for bucket in ("scoring", "packet_eligibility", "pit"):
        print(f"--- {bucket} ---")
        for name, row_out in result[bucket].items():
            print(f"  {row_out['outcome']:<9} {name}")
    print("receipt:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
