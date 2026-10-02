r"""Cycle #37 — Attempt #3 — build test-only receipt fixtures for the scoring and PIT gates.

These helpers exist so the admitted path can be exercised -- in unit tests, in the attempt's source and
installed-consumer probes, and by an independent reviewer replaying them -- with *real bytes* behind every
digest, instead of the digest-shaped strings that MF37A02-02/03 showed were being admitted. Everything they
write goes into a store marked ``TEST_ONLY_FIXTURE_AUTHORITY``; an authority opened over it labels every
admission it supports as a fixture, and none counts as a real eligible forecast or real PIT proof.

They never write inside the canonical data root (the authority refuses to open such a store) and never
create a receipt for a real contest.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from aggie_analytics.cycle37.receipt_authority import (
    FINAL_RECEIPT,
    FORECAST_RECEIPT,
    PRIOR_RECEIPT,
    TEST_ONLY,
    ReceiptAuthority,
    create_test_only_store,
    write_fixture_receipt,
)

FIXTURE_SOURCE = "BAS-TEST-ONLY-FIXTURE-SOURCE"


def _iso(value: Any) -> Any:
    return value.isoformat() if isinstance(value, datetime) else value


def fixture_authority(root: Path | str, authority_id: str = "a03-fixture") -> ReceiptAuthority:
    """Create (if needed) and open a marked test-only store trusting only the fixture source."""

    create_test_only_store(root, authority_id)
    return ReceiptAuthority(root, authority_class=TEST_ONLY, authority_id=authority_id,
                            trusted_source_ids={FIXTURE_SOURCE}, acknowledge_test_only=True)


def bind_forecast(root: Path | str, forecast: Any, *, source_id: str = FIXTURE_SOURCE,
                  packet_overrides: Mapping[str, Any] | None = None,
                  receipt_overrides: Mapping[str, Any] | None = None) -> Any:
    """Write a frozen packet and its freeze receipt for ``forecast``; return it with both digests set.

    ``packet_overrides``/``receipt_overrides`` let a negative test make the stored bytes disagree with the
    forecast on purpose; the returned forecast still carries the digests of what was actually written.
    """

    packet = {"contest_id": forecast.contest_id, "model_identity": forecast.model_identity,
              "input_identity": forecast.input_identity, "designated_home_team": forecast.designated_home_team,
              "designated_away_team": forecast.designated_away_team,
              "home_win_probability": forecast.home_win_probability}
    packet.update(packet_overrides or {})
    payload = json.dumps(packet, sort_keys=True).encode("utf-8")
    receipt = {"receipt_kind": FORECAST_RECEIPT, "source_id": source_id, "contest_id": forecast.contest_id,
               "model_identity": forecast.model_identity, "input_identity": forecast.input_identity,
               "designated_home_team": forecast.designated_home_team,
               "designated_away_team": forecast.designated_away_team, "neutral_site": forecast.neutral_site,
               "cutoff_utc": _iso(forecast.cutoff_utc), "freeze_known_at": _iso(forecast.freeze_known_at)}
    receipt.update(receipt_overrides or {})
    receipt_digest, packet_digest = write_fixture_receipt(root, receipt, payload)
    return dataclasses.replace(forecast, receipt_digest=receipt_digest, packet_bytes_digest=packet_digest)


def bind_final(root: Path | str, final: Any, *, source_id: str = FIXTURE_SOURCE,
               raw_source: bytes = b"<fixture official final source bytes>",
               receipt_overrides: Mapping[str, Any] | None = None) -> Any:
    """Write an official-final source receipt for ``final``; return it with its source receipt digest set."""

    receipt = {"receipt_kind": FINAL_RECEIPT, "source_id": source_id, "contest_id": final.contest_id,
               "home_team": final.home_team, "away_team": final.away_team, "home_points": final.home_points,
               "away_points": final.away_points, "lifecycle": final.lifecycle,
               "observed_at": _iso(final.observed_at), "corrected_at": _iso(final.corrected_at),
               "neutral_site": final.neutral_site}
    receipt.update(receipt_overrides or {})
    digest, _payload = write_fixture_receipt(root, receipt, raw_source)
    return dataclasses.replace(final, source_receipt_digest=digest)


def prior_receipt(root: Path | str, *, priors: list[str] | str, published_at: datetime, known_at: datetime,
                  source_id: str = FIXTURE_SOURCE, publication: bytes | None = None,
                  extra: Mapping[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    """Write one prior-publication receipt; return (digest, the receipt as stored)."""

    content: dict[str, Any] = {"receipt_kind": PRIOR_RECEIPT, "source_id": source_id,
                               "published_at_utc": published_at.isoformat(), "known_at_utc": known_at.isoformat()}
    if isinstance(priors, str):
        content["prior_game_id"] = priors
    else:
        content["prior_observation_ids"] = list(priors)
    content.update(extra or {})
    payload = publication if publication is not None else json.dumps({"published": priors}).encode("utf-8")
    digest, payload_digest = write_fixture_receipt(root, content, payload)
    return digest, dict(content, payload_sha256=payload_digest)
