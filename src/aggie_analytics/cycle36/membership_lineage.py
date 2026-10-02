"""Exact request/response/transform/row lineage for membership derivatives.

MR35R-03: the Cycle #35 prover
(``tools/cycle35/r35_27_national_population_authority.prove_receipt_linkage``)
binds a seasonless derivative file to a declared acquisition year when
*exactly one* cached ``/teams`` payload contains every program ID in the
file. The manager broke it with two synthetic probes:

* a one-ID derivative was "PROVED" by a two-row payload, because a subset
  satisfies "covers every program in the file";
* adding a second, unrelated cached year flipped the same derivative from
  PROVED to REFUSED, so an existing row's authority depended on what else
  happened to be sitting in the cache.

Both failures come from the same modelling error: coverage of an ID set is
a *similarity* test, and similarity is not lineage. This module proves
lineage the only way a derivative's provenance can actually be proved --
by re-executing the declared transformation on the declared response bytes
and requiring the result to equal the derivative exactly:

    receipt.raw_sha256 == sha256(cached payload bytes)          (1) bytes
    request_identity   == sha256_json(endpoint, parameters)     (2) request
    transform(payload) == derivative rows, row for row          (3) transform

Under (1)-(3) a subset cannot bind, because a subset is not an equality;
and an unrelated cached year cannot change an existing row's authority,
because the proof never consults any payload except the one whose
transformation reproduces this file. A year that fails is reported with the
exact residual -- which rows the transform produced that the file lacks, and
which the file holds that the transform did not produce -- so a reviewer can
see why, rather than being told a count matched.

The transformation is declared, versioned data, not a guess: a derivative
records which transform produced it, and the transform is applied from that
declaration. An undeclared transform is ``UNDECLARED``, never "probably the
obvious one".

MF36-05 (Cycle #37) found two ways this was still weaker than it claimed.

* **Multiplicity and order were not compared.** ``exact_set_match`` was set
  equality, so a derivative whose rows were duplicated or reordered relative
  to the transform's output still "PROVED". A set is not a row-for-row
  reproduction, and the docstring above claimed the latter. The binding test
  is now sequence equality, with the first divergent index and the
  per-identifier multiplicity residual reported so a reviewer can see which
  it was.
* **The declared request identity was never checked.** A receipt carrying any
  string in ``request_identity_sha256`` was accepted, so an identity that
  belongs to no request at all could carry the proof. An identity is now
  recomputed from the route and parameters the receipt itself records, under
  the named conventions this repository actually used; one that recomputes to
  nothing is ``REQUEST_IDENTITY_DOES_NOT_RECOMPUTE`` and cannot bind.

A third distinction MF36-05 names is kept rather than repaired, because it is
a real difference and not a defect: a cache filename that equals a request
identity proves *which request these bytes answer*, but no filename attests
that a request was issued and returned them. A file reconstructed from the
cache carries no status and no retrieval time, so it binds under
``PROVED_BY_EXACT_TRANSFORM_REPRODUCTION_WITHOUT_ATTESTED_ACQUISITION``,
which says so in its name.
"""

from __future__ import annotations

import collections
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

#: Bumped for MF36-05: binding moved from set equality to row-for-row
#: reproduction, and a declared request identity must now recompute.
#: The predecessor version is named so a stored lineage record made
#: under the weaker rule is never mistaken for one made under this one.
LINEAGE_VERSION = "BAS-MEMBERSHIP-EXACT-LINEAGE-v37.1"
PREDECESSOR_LINEAGE_VERSION = "BAS-MEMBERSHIP-EXACT-LINEAGE-v36.1"

PROVED = "PROVED_BY_EXACT_TRANSFORM_REPRODUCTION"

#: The bytes reproduce the derivative row for row, but the only receipt that
#: does so was reconstructed from a cache filename: nothing attests that a
#: request was issued, only which request these bytes would answer.
PROVED_UNATTESTED = (
    "PROVED_BY_EXACT_TRANSFORM_REPRODUCTION_WITHOUT_ATTESTED_ACQUISITION"
)

REFUSED_NO_TRANSFORM = "REFUSED_NO_DECLARED_TRANSFORM"
REFUSED_NO_RECEIPT = "REFUSED_NO_RECEIPT_REPRODUCES_THIS_FILE"
REFUSED_BYTES = "REFUSED_RECEIPT_BYTES_DO_NOT_MATCH_DECLARED_DIGEST"
REFUSED_AMBIGUOUS = "REFUSED_MORE_THAN_ONE_RECEIPT_REPRODUCES_THIS_FILE"

#: A receipt's rows carry the same identifiers as the derivative but not in
#: the same order, or not the same number of times. Reported separately from
#: "nothing resembles this file", because the two mean different things: one
#: is an unproved derivative, the other is a derivative produced by some
#: transformation other than the declared one.
REFUSED_SET_MATCH_ONLY = (
    "REFUSED_SET_MATCHES_BUT_ROWS_ARE_NOT_REPRODUCED"
)

#: Per-receipt outcomes.
RECEIPT_REPRODUCES = "REPRODUCES_THE_FILE"
RECEIPT_SET_ONLY = "SET_MATCHES_BUT_ROWS_DIFFER"
RECEIPT_DOES_NOT = "DOES_NOT_REPRODUCE_THE_FILE"
RECEIPT_UNAUTHENTIC = "REFUSED_REQUEST_IDENTITY_IS_NOT_AUTHENTIC"

#: Request-identity authenticity.
IDENTITY_AUTHENTIC = "REQUEST_IDENTITY_RECOMPUTES"
IDENTITY_FORGED = "REQUEST_IDENTITY_DOES_NOT_RECOMPUTE"
IDENTITY_ABSENT = "REQUEST_IDENTITY_NOT_DECLARED"

#: How the receipt came to exist, which decides what it can attest.
BASIS_LEDGER = "DECLARED_ACQUISITION_ATTEMPT"
BASIS_CACHE_FILENAME = "RECONSTRUCTED_FROM_CACHE_FILENAME"

#: What the receipt attests about the acquisition itself.
ATTESTED = "DECLARED_ATTEMPT_WITH_SUCCESS_STATUS"
ATTESTED_NO_SUCCESS = "DECLARED_ATTEMPT_WITHOUT_SUCCESS_STATUS"
UNATTESTED = "CACHE_FILENAME_ONLY_NO_DECLARED_ATTEMPT"

#: Declared transformations. Each is (version, description, callable) and is
#: addressed by name from a derivative's declaration. Adding a transform is a
#: reviewable code change, not a runtime inference.
TransformFn = Callable[[Sequence[Mapping[str, Any]]], list[dict[str, Any]]]


def _teams_fbs_fcs(payload_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Programs the source classifies as FBS or FCS, in source order.

    This is the transformation the Cycle #30 membership derivatives actually
    used: the CFBD ``/teams`` response carries every division, and the
    national football denominator keeps the two that play the scholarship
    subdivisions. The classification comes from the response *field*, never
    from the request's ``classification`` query parameter, which the source
    ignores (both the fbs and fcs 2013 requests returned identical bytes).
    """

    return [
        {"source_entity_id": str(row.get("id")), "classification": row.get("classification")}
        for row in payload_rows
        if row.get("classification") in {"fbs", "fcs"}
    ]


TRANSFORMS: dict[str, tuple[str, str, TransformFn]] = {
    "TEAMS_FBS_FCS_V1": (
        "v1",
        "Keep response rows whose response-field classification is fbs or fcs, "
        "preserving source order; project the source entity id.",
        _teams_fbs_fcs,
    ),
}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


#: The request-identity conventions this repository has actually written, each
#: named and recomputable from the route and parameters a receipt records.
#:
#: These are not guesses. ``tools/acquire_cycle30_national.py`` writes the
#: first two -- the cache-hit branch and the live branch -- and its
#: ``cache_path`` writes the third as the cache filename. Naming them here is
#: what makes a declared identity checkable: an identity that recomputes under
#: none of them was not produced by any acquisition path this repository has,
#: whatever string it happens to be.
#:
#: Adding a convention is a reviewable code change. A receipt is never
#: admitted by widening this table at runtime to fit the string it carries.
IDENTITY_CONVENTIONS: dict[str, Callable[[str, Mapping[str, Any]], str]] = {
    "CYCLE30_LEDGER_CACHE_HIT_PATH_PARAMETERS_V1": lambda endpoint, parameters: (
        _sha256_json({"path": endpoint, "parameters": dict(parameters)})
    ),
    "CYCLE30_LEDGER_LIVE_PATH_PARAMETERS_RUN_V1": lambda endpoint, parameters: (
        _sha256_json(
            {"path": endpoint, "parameters": dict(parameters), "run_id": "cycle30"}
        )
    ),
    "CYCLE30_CACHE_FILENAME_ENDPOINT_PARAMETERS_V1": lambda endpoint, parameters: (
        _sha256_json({"endpoint": endpoint, "parameters": dict(parameters)})
    ),
}


def authenticate_request_identity(
    endpoint: str, parameters: Mapping[str, Any], declared: str | None
) -> dict[str, Any]:
    """Whether a declared request identity recomputes from its own request.

    An identity that cannot be recomputed from the route and parameters the
    receipt itself records is not an identity for that request. It may be a
    typo, a copied value or an invention; the proof cannot tell which, and
    does not need to -- none of them is an acquisition receipt.
    """

    recomputed = {
        name: fn(endpoint, parameters) for name, fn in IDENTITY_CONVENTIONS.items()
    }
    if not declared:
        return {
            "state": IDENTITY_ABSENT,
            "convention": None,
            "declared": declared,
            "recomputed": recomputed,
        }
    matching = sorted(name for name, value in recomputed.items() if value == declared)
    return {
        "state": IDENTITY_AUTHENTIC if matching else IDENTITY_FORGED,
        "convention": matching[0] if matching else None,
        "all_matching_conventions": matching,
        "declared": declared,
        "recomputed": recomputed,
    }


@dataclass(frozen=True)
class Receipt:
    """One declared acquisition attempt bound to its cached bytes."""

    endpoint: str
    parameters: dict[str, Any]
    declared_digest: str
    request_identity: str | None
    cached_path: str | None
    actual_digest: str | None
    retrieved_at_utc: str | None
    http_status: Any
    payload_rows: int
    #: How this receipt came to exist. A declared attempt can attest that a
    #: request was issued; a cache filename cannot. Defaulted so that every
    #: existing construction keeps its meaning.
    identity_basis: str = BASIS_LEDGER

    @property
    def year(self) -> int | None:
        value = self.parameters.get("year")
        return int(value) if value is not None else None

    @property
    def bytes_match(self) -> bool:
        return bool(self.actual_digest) and self.actual_digest == self.declared_digest

    @property
    def identity_check(self) -> dict[str, Any]:
        return authenticate_request_identity(
            self.endpoint, self.parameters, self.request_identity
        )

    @property
    def identity_authentic(self) -> bool:
        return self.identity_check["state"] == IDENTITY_AUTHENTIC

    @property
    def attestation(self) -> str:
        """What this receipt attests about the acquisition, not the bytes."""

        if self.identity_basis != BASIS_LEDGER:
            return UNATTESTED
        try:
            status = int(self.http_status)
        except (TypeError, ValueError):
            return ATTESTED_NO_SUCCESS
        if not 200 <= status < 300 or not self.retrieved_at_utc:
            return ATTESTED_NO_SUCCESS
        return ATTESTED

    def as_dict(self) -> dict[str, Any]:
        check = self.identity_check
        return {
            "endpoint": self.endpoint,
            "parameters": self.parameters,
            "declared_raw_sha256": self.declared_digest,
            "actual_payload_sha256": self.actual_digest,
            "bytes_match": self.bytes_match,
            "request_identity_sha256": self.request_identity,
            "request_identity_state": check["state"],
            "request_identity_convention": check["convention"],
            "identity_basis": self.identity_basis,
            "acquisition_attestation": self.attestation,
            "cached_payload": self.cached_path,
            "retrieved_at_utc": self.retrieved_at_utc,
            "http_status": self.http_status,
            "payload_rows": self.payload_rows,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def payload_rows(payload: Any) -> list[Mapping[str, Any]]:
    """Rows of a source response, whatever envelope it arrived in."""

    if isinstance(payload, dict):
        payload = payload.get("data") or payload.get("teams") or []
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, Mapping)]


def load_receipts(
    ledger_path: Path, raw_dir: Path, endpoint: str = "/teams"
) -> list[Receipt]:
    """Every declared attempt for ``endpoint``, bound to its cached bytes.

    The binding is by content hash, never by filename: the cache is keyed by
    request identity while the ledger records a response digest, so the two
    names do not agree and only hashing settles which file is which.
    """

    if not ledger_path.is_file():
        return []
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    digest_to_bytes: dict[str, tuple[Path, list[Mapping[str, Any]]]] = {}
    for path in sorted(raw_dir.glob("*.json")):
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        digest = sha256_bytes(raw)
        try:
            rows = payload_rows(json.loads(raw.decode("utf-8")))
        except (UnicodeDecodeError, ValueError):
            rows = []
        digest_to_bytes[digest] = (path, rows)

    receipts: list[Receipt] = []
    for attempt in ledger.get("attempts") or []:
        if attempt.get("route") != endpoint:
            continue
        declared = str(attempt.get("raw_sha256") or "")
        found = digest_to_bytes.get(declared)
        receipts.append(
            Receipt(
                endpoint=endpoint,
                parameters=dict(attempt.get("parameters") or {}),
                declared_digest=declared,
                request_identity=attempt.get("request_identity_sha256"),
                cached_path=str(found[0]) if found else None,
                actual_digest=declared if found else None,
                retrieved_at_utc=attempt.get("retrieved_at_utc"),
                http_status=attempt.get("http_status") or attempt.get("status"),
                payload_rows=len(found[1]) if found else 0,
                identity_basis=BASIS_LEDGER,
            )
        )
    return receipts


def receipts_from_cache(
    raw_dir: Path,
    declared_years: Iterable[int],
    identity: Callable[[str, dict[str, Any]], str],
    endpoint: str = "/teams",
    parameter_shapes: Sequence[dict[str, Any]] = ({},),
) -> list[Receipt]:
    """Receipts reconstructed from the cache's own request-identity naming.

    Some years were acquired by a later tool that names its cache entries by
    ``sha256_json({endpoint, parameters})`` and does not appear in the Cycle
    #30 ledger. Those files are still bound acquisitions -- the filename *is*
    the request identity -- so they are admitted with that identity stated,
    and their digest is the file's own content hash rather than a separately
    declared one.
    """

    found: list[Receipt] = []
    for year in declared_years:
        for shape in parameter_shapes:
            parameters = {"year": int(year), **shape}
            request_identity = identity(endpoint, parameters)
            path = raw_dir / f"{request_identity}.json"
            if not path.is_file():
                continue
            raw = path.read_bytes()
            digest = sha256_bytes(raw)
            try:
                rows = payload_rows(json.loads(raw.decode("utf-8")))
            except (UnicodeDecodeError, ValueError):
                rows = []
            found.append(
                Receipt(
                    endpoint=endpoint,
                    parameters=parameters,
                    declared_digest=digest,
                    request_identity=request_identity,
                    cached_path=str(path),
                    actual_digest=digest,
                    retrieved_at_utc=None,
                    http_status=None,
                    payload_rows=len(rows),
                    identity_basis=BASIS_CACHE_FILENAME,
                )
            )
    return found


def _rows_of(receipt: Receipt) -> list[Mapping[str, Any]]:
    if not receipt.cached_path:
        return []
    try:
        raw = Path(receipt.cached_path).read_bytes()
    except OSError:
        return []
    try:
        return payload_rows(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, ValueError):
        return []


def compare_rows(
    produced: Sequence[Mapping[str, Any]], observed: Sequence[str]
) -> dict[str, Any]:
    """Exact row-for-row comparison with every residual named.

    ``exact_row_reproduction`` is the binding test: the transform's output and
    the derivative must be the same sequence of identifiers, in the same order
    and each appearing the same number of times. ``exact_set_match`` is kept
    beside it and is deliberately *not* the binding test -- it is the weaker
    statement the predecessor mistook for reproduction, retained so a report
    can say "the sets agreed and the rows did not", which is the difference
    between a derivative that was produced some other way and one that has
    nothing to do with these bytes.
    """

    produced_ids = [str(row["source_entity_id"]) for row in produced]
    observed_ids = list(observed)
    produced_set = set(produced_ids)
    observed_set = set(observed_ids)
    only_produced = sorted(produced_set - observed_set)
    only_observed = sorted(observed_set - produced_set)

    produced_counts = collections.Counter(produced_ids)
    observed_counts = collections.Counter(observed_ids)
    multiplicity = sorted(
        {
            identifier: {
                "in_transform_output": produced_counts.get(identifier, 0),
                "in_file": observed_counts.get(identifier, 0),
            }
            for identifier in set(produced_counts) | set(observed_counts)
            if produced_counts.get(identifier, 0) != observed_counts.get(identifier, 0)
        }.items()
    )
    divergent = next(
        (
            index
            for index, (left, right) in enumerate(zip(produced_ids, observed_ids))
            if left != right
        ),
        None,
    )
    if divergent is None and len(produced_ids) != len(observed_ids):
        divergent = min(len(produced_ids), len(observed_ids))

    exact_set = not only_produced and not only_observed and bool(observed_ids)
    exact_rows = bool(observed_ids) and produced_ids == observed_ids
    return {
        "produced_rows": len(produced_ids),
        "observed_rows": len(observed_ids),
        "exact_row_reproduction": exact_rows,
        "exact_set_match": exact_set,
        "set_matches_but_rows_do_not": exact_set and not exact_rows,
        "order_match": produced_ids == observed_ids,
        "duplicate_produced": len(produced_ids) != len(produced_set),
        "duplicate_observed": len(observed_ids) != len(observed_set),
        "multiplicity_differences": [
            {"source_entity_id": identifier, **counts}
            for identifier, counts in multiplicity[:50]
        ],
        "multiplicity_difference_count": len(multiplicity),
        "first_divergent_row_index": divergent,
        "in_transform_output_not_in_file": only_produced[:50],
        "in_file_not_in_transform_output": only_observed[:50],
        "in_transform_output_not_in_file_count": len(only_produced),
        "in_file_not_in_transform_output_count": len(only_observed),
    }


def prove_lineage(
    observed_entity_ids: Sequence[str],
    receipts: Sequence[Receipt],
    transform_name: str | None,
) -> dict[str, Any]:
    """Which declared request demonstrably produced this derivative file.

    Returns ``PROVED_BY_EXACT_TRANSFORM_REPRODUCTION`` only when a receipt
    whose request identity recomputes, and whose declared attempt carries a
    success status and a retrieval time, reproduces the file row for row
    under the declared transform -- same identifiers, same order, same
    multiplicity -- and every receipt that does so declares the same year.

    A subset never proves anything. A reordered or duplicated row set never
    proves anything. An identity that recomputes to nothing never proves
    anything. An unrelated cached year cannot disturb a receipt that does
    reproduce the file. Reproduction by cache-reconstructed receipts alone
    binds the season under the weaker
    ``PROVED_BY_EXACT_TRANSFORM_REPRODUCTION_WITHOUT_ATTESTED_ACQUISITION``.
    """

    base: dict[str, Any] = {
        "lineage_version": LINEAGE_VERSION,
        "declared_transform": transform_name,
        "observed_rows": len(observed_entity_ids),
        "candidate_receipts": len(receipts),
    }
    if not transform_name or transform_name not in TRANSFORMS:
        base.update(
            state=REFUSED_NO_TRANSFORM,
            bound_year=None,
            bound_receipt_sha256=None,
            why=(
                "The derivative does not declare a transformation this build "
                "can execute, so no reproduction can be attempted. Lineage is "
                "never inferred from a resemblance between row sets."
            ),
        )
        return base

    version, description, fn = TRANSFORMS[transform_name]
    base["transform_version"] = version
    base["transform_description"] = description

    evaluations: list[dict[str, Any]] = []
    reproducing: list[dict[str, Any]] = []
    set_only: list[dict[str, Any]] = []
    for receipt in receipts:
        record = {"receipt": receipt.as_dict()}
        check = receipt.identity_check
        if check["state"] != IDENTITY_AUTHENTIC:
            # Checked before the bytes on purpose. "These bytes reproduce the
            # file" is a statement about the payload; "this request produced
            # them" is the statement the derivative needs, and a receipt whose
            # identity does not recompute makes no such statement.
            record["result"] = RECEIPT_UNAUTHENTIC
            record["request_identity_check"] = check
            record["detail"] = (
                "The declared request identity does not recompute from this "
                "receipt's own route and parameters under any named "
                "convention, so it is not this request's identity and cannot "
                "carry a proof."
                if check["state"] == IDENTITY_FORGED
                else "The receipt declares no request identity, so there is "
                "no request for the bytes to be attributed to."
            )
            evaluations.append(record)
            continue
        if not receipt.bytes_match:
            record["result"] = REFUSED_BYTES
            record["detail"] = (
                "The declared response digest has no cached payload with those "
                "exact bytes, so nothing can be re-executed against it."
            )
            evaluations.append(record)
            continue
        produced = fn(_rows_of(receipt))
        comparison = compare_rows(produced, observed_entity_ids)
        record["comparison"] = comparison
        if comparison["exact_row_reproduction"]:
            record["result"] = RECEIPT_REPRODUCES
        elif comparison["exact_set_match"]:
            record["result"] = RECEIPT_SET_ONLY
            record["detail"] = (
                "The transform's output and the file carry the same "
                "identifiers but not as the same sequence of rows, so the "
                "file was produced by some transformation other than the "
                "declared one. A set is not a reproduction."
            )
        else:
            record["result"] = RECEIPT_DOES_NOT
        evaluations.append(record)
        if comparison["exact_row_reproduction"]:
            reproducing.append(record)
        elif comparison["exact_set_match"]:
            set_only.append(record)

    base["evaluations"] = evaluations
    base["receipts_matching_as_a_set_only"] = len(set_only)
    base["receipts_with_unauthentic_request_identity"] = sum(
        1 for record in evaluations if record["result"] == RECEIPT_UNAUTHENTIC
    )
    if reproducing:
        years = sorted({r["receipt"]["parameters"].get("year") for r in reproducing})
        base["reproducing_years"] = years
        base["reproducing_request_identities"] = sorted(
            {
                str(r["receipt"]["request_identity_sha256"])
                for r in reproducing
                if r["receipt"]["request_identity_sha256"]
            }
        )
        if len(years) != 1 or years[0] is None:
            # Different declared years reproducing the same file is a real
            # season ambiguity and must not be resolved by preference.
            base.update(
                state=REFUSED_AMBIGUOUS,
                bound_year=None,
                bound_receipt_sha256=None,
                why=(
                    "More than one declared YEAR reproduces this file exactly, "
                    "so which season it describes is genuinely unknown. A "
                    "season that cannot be proved must not be written."
                ),
            )
            return base
        # Prefer an attested attempt as the binding receipt when one
        # reproduces the file. A cache filename can say which request these
        # bytes answer; only a declared attempt says a request was issued.
        attested = [
            record
            for record in reproducing
            if record["receipt"]["acquisition_attestation"] == ATTESTED
        ]
        receipt_dict = (attested or reproducing)[0]["receipt"]
        base.update(
            state=PROVED if attested else PROVED_UNATTESTED,
            bound_year=years[0],
            bound_receipt_sha256=receipt_dict["declared_raw_sha256"],
            bound_request_identity=receipt_dict["request_identity_sha256"],
            bound_request_identity_convention=receipt_dict[
                "request_identity_convention"
            ],
            bound_acquisition_attestation=receipt_dict["acquisition_attestation"],
            attested_reproducing_receipts=len(attested),
            request_identity_unique=len(reproducing) == 1,
            why=(
                "Re-executing the declared transformation on this receipt's "
                "cached bytes reproduces the derivative row for row -- same "
                "identifiers, same order, same multiplicity -- and every "
                "reproducing receipt declares the same year. The season is "
                "that declared year parameter."
                + (
                    ""
                    if len(reproducing) == 1
                    else " Several requests of that same year returned "
                    "byte-identical payloads (the source ignores the "
                    "classification parameter), so which of them wrote the "
                    "file is unresolved while the season is not."
                )
                + (
                    ""
                    if attested
                    else " No declared acquisition attempt reproduces this "
                    "file; the only receipts that do were reconstructed from "
                    "cache filenames, which name a request without attesting "
                    "that one was issued."
                )
            ),
        )
        return base
    if set_only:
        base.update(
            state=REFUSED_SET_MATCH_ONLY,
            bound_year=None,
            bound_receipt_sha256=None,
            why=(
                "A receipt's transform output carries exactly the identifiers "
                "this file carries, but not as the same rows: the order or "
                "the number of times an identifier appears differs. The "
                "predecessor called that a proof. It is evidence that some "
                "other transformation produced the file, and the declared one "
                "is therefore not its lineage."
            ),
        )
        return base
    base.update(
        state=REFUSED_NO_RECEIPT,
        bound_year=None,
        bound_receipt_sha256=None,
        why=(
            "No declared request's bytes reproduce this file under its declared "
            "transformation. The per-receipt residuals above name exactly which "
            "rows differ."
        ),
    )
    return base
