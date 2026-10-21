r"""Generate the committed national site/calendar association research/data contract and the reader's pinned anchors
(BAT-734, Cycle #63 TP63-A01).

``python -B tools/cycle63/make_site_calendar_contract.py --data-root <data> --contract-out <contract.json>
[--module src/aggie_analytics/retrospective_baseline/context_association.py] [--profile <build receipt.json>]``

Source only: the generator verifies every pinned accepted input under the explicitly named data root (whole-file
SHA-256 and bytes, manifests, metas, block indexes), qualifies every 2016-2023 target from the raw inputs and derives
the expected collections that qualification determines -- the 5,875 targets, the excluded games with their reasons
(the frozen common cohort), the parent witness digest, the counts and every key-sequence digest. It never fits, never
estimates or scores and never writes the data root. The contract carries the module's complete frozen rules
(``rules_document()``); ``--module`` rewrites only the module's GENERATED ANCHORS block with the contract SHA-256 and
the same inputs, parent contracts and expected collections. ``--profile`` (a first canonical build receipt) pins the
canonical profile in that block and requires the contract on disk to be byte-identical to the regenerated one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.retrospective_baseline import context_association as ca  # noqa: E402
from aggie_analytics.retrospective_baseline import context_association_build as cab  # noqa: E402

GOVERNING_PLAN = {
    "path": r"C:\BatteredAggieSyndrome.data\ops\manager_reviews\cycle63\attempt01\preparation-20261020"
            r"\TECHNICAL_PLAN_TP63_A01.md",
    "sha256": "67fb381aa1f679d704622aa9d0ea7e5517129c62b209974c53f2d01ba1e9d254"}
POPULATION = ("canonical/national_di_population_2016_2025/sha256/"
              "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27")
HISTORY = ("canonical/national_history_prefix_2016_2023/sha256/"
           "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b")
REFERENCE = ("canonical/national_retrospective_reference_2016_2023/sha256/"
             "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8")
#: The accepted parents' relative locators and declared identities (TP63 section 2; INPUT_BINDINGS.final.json).
ACCEPTED_INPUTS = {
    "population_database": {"relative_path": f"{POPULATION}/national_population.sqlite",
                            "identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
                            "contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
                            "program_season_identity": "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e",
                            "role": "ACCEPTED_C38_PARENT_POPULATION_CONTEST_ROWS_2016_2023"},
    "population_manifest": {"relative_path": "manifests/national_di_population_2016_2025/sha256/"
                                             "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27/"
                                             "run_manifest.json",
                            "identity": "3baff07fac99831a2b0d06db408ea0ae513566757d763dfd58571d3c958b5f27",
                            "role": "ACCEPTED_C38_POPULATION_RUN_MANIFEST"},
    "participant_bindings": {"relative_path": "canonical/national_di_population_2016_2025/sha256/"
                                              "711e9dfcc35a181d51206099f41aa576424fc30ed61600811ab464074fb8f81e/"
                                              "identity_bindings.jsonl.gz",
                             "header_contract_sha256": "3b27a454269127806b4930466dcb7c11de089a9479ccc41b7b2500dc606dc903",
                             "role": "ACCEPTED_C38_PARTICIPANT_PROVIDER_IDENTITY_BINDINGS"},
    "history_database": {"relative_path": f"{HISTORY}/national_history.sqlite",
                         "identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
                         "content_identity": "58c2bf7d6e9c70c2ba2a9e4dd583a89ace10062cc49aafe00d2f9675c84afe63",
                         "contract_sha256": "2646a5cbe9a1daff7135671b85c98239b250d493c53c4bc066f57805e1e4f76c",
                         "role": "ACCEPTED_C39_HISTORY_PREFIX_TARGETS_AND_ELIGIBLE_PRIORS"},
    "history_manifest": {"relative_path": "manifests/national_history_prefix_2016_2023/sha256/"
                                          "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b/"
                                          "run_manifest.json",
                         "identity": "aba0384f027776bac4bd0fded3e5ba15354f4005f786f7495b3660236914661b",
                         "role": "ACCEPTED_C39_HISTORY_RUN_MANIFEST"},
    "reference_database": {"relative_path": f"{REFERENCE}/national_retrospective_reference.sqlite",
                           "identity": "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
                           "content_identity": "fe303a90d8753956b914d3c7c2adfe2d33d9816bfb45689b0361f8e36e2e6cc0",
                           "contract_sha256": "3cfeff255bb29801b482b02611ad2c72c725d069e9f89d3911e86711af34bb31",
                           "role": "ACCEPTED_C56_REFERENCE_FEATURES_LABELS_AND_PARENT_GAME_SCORES"},
    "reference_manifest": {"relative_path": "manifests/national_retrospective_reference_2016_2023/sha256/"
                                            "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8/"
                                            "run_manifest.json",
                           "identity": "ad01a42f203435627232af9e9ba1a73d29154650553f37926756d821711582d8",
                           "role": "ACCEPTED_C56_REFERENCE_RUN_MANIFEST"},
}
#: The eight retained full FBS provider game captures and their capture receipts (season -> response SHA-256,
#: receipt file).
ACCEPTED_CAPTURES = {
    "2016": ("9bc85c6f9768a2469864cb844e6cc98cdfce06f23b02a8bfb8f03004cad12613", "cap_7ba1e63b5c96b95ad908ac2e"),
    "2017": ("6ca1a9cc367b6c70eb4fb2bd2a71fb83b05dc536028857f60b94fdd57062eda2", "cap_8c237a06fcc4fb0fa489e819"),
    "2018": ("c96dbf7384af57300d6a3eb927ddb8fdc29e4e5d4bccd15babc4c32366829837", "cap_fca8ffe34583265bdedb6a66"),
    "2019": ("b361354f331cd9a419ebec756833c65a480f2431fd6044fb9e96e06cf4b6f14f", "cap_1dc1b866dd56f02e217b6305"),
    "2020": ("6fde848c1b58a2a0c2ca831bbf6f93e7bb5a4398c9746682438e96095846a63f", "cap_b89826898fcbb575790bde15"),
    "2021": ("09f2f4613dc4dc83d38e14757bb28695b4532463a0b788cb12c4d13347a2d19a", "cap_3c3beda43b160118d56777b1"),
    "2022": ("9c50d7465d2d74f6c0e9d9bf79c4b593a0b70db790207109d1c2f675e6e70fdf", "cap_d8794bdadba655a1c4136e59"),
    "2023": ("ebf9ea175c3332102dd4555fd8cd126cbd2cbc6cef4aebe95c6c5ae7af1dea03", "cap_2c82aa5161f3ad63b5abb3c3"),
}
PARENT_CONTRACT_PATHS = ("configs/national_di_population_2016_2025_contract.json",
                         "configs/national_history_prefix_2016_2023_contract.json",
                         "configs/national_retrospective_reference_2016_2023_contract.json")
BEGIN = "# ---- BEGIN GENERATED ANCHORS (tools/cycle63/make_site_calendar_contract.py; never hand edited) ----\n"
END = "# ---- END GENERATED ANCHORS ----\n"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pinned_inputs(data_root: Path, accepted: dict[str, dict[str, Any]] | None = None,
                  captures: dict[str, tuple[str, str]] | None = None) -> dict[str, Any]:
    """Every declared input with its observed whole-file SHA-256 and bytes (refused when a declared identity's file is
    absent); the provider captures and receipts are keyed by season."""
    root = Path(data_root)
    out: dict[str, Any] = {}
    for name, spec in (accepted or ACCEPTED_INPUTS).items():
        path = root / Path(*spec["relative_path"].split("/"))
        out[name] = {**spec, "sha256": _sha(path), "bytes": path.stat().st_size}
    games: dict[str, Any] = {}
    receipts: dict[str, Any] = {}
    for season, (response_sha, capture_id) in sorted((captures or ACCEPTED_CAPTURES).items()):
        game_rel = f"raw/SRC-002/games/sha256_{response_sha}.json"
        receipt_rel = f"manifests/captures/SRC-002/{capture_id}.json"
        game_path, receipt_path = root / Path(*game_rel.split("/")), root / Path(*receipt_rel.split("/"))
        rows = json.loads(game_path.read_bytes().decode("utf-8"))
        receipt = json.loads(receipt_path.read_bytes().decode("utf-8"))
        games[season] = {"relative_path": game_rel, "sha256": _sha(game_path), "bytes": game_path.stat().st_size,
                         "rows": len(rows), "role": f"RETAINED_FULL_FBS_PROVIDER_GAME_CAPTURE_{season}"}
        receipts[season] = {"relative_path": receipt_rel, "sha256": _sha(receipt_path),
                            "bytes": receipt_path.stat().st_size, "capture_id": receipt["capture_id"],
                            "capture_known_at_utc": receipt["capture_known_at_utc"],
                            "retrieved_at_utc": receipt["retrieved_at_utc"], "source_uri": receipt["source_uri"],
                            "upstream_lineage": receipt["upstream_lineage"],
                            "role": f"RETAINED_PROVIDER_CAPTURE_RECEIPT_{season}"}
    out["provider_games"] = games
    out["capture_receipts"] = receipts
    return out


def contract_document(inputs: dict[str, Any], parent_contracts: dict[str, str], expected: dict[str, Any]
                      ) -> dict[str, Any]:
    return {
        "schema_version": "1.0", "contract_id": ca.CONTRACT_ID, "jira_key": "BAT-734", "cycle_number": 63,
        "attempt_number": 1, "governing_plan": GOVERNING_PLAN,
        "classification": "RETROSPECTIVE_SOURCE_CLAIM_SITE_CALENDAR_ASSOCIATION_RESEARCH_NOT_FORECAST_NOT_PIT",
        "population_id": ca.POPULATION,
        "purpose": "Qualify every accepted 2016-2023 target and both oriented views for the agreed designated source "
                   "site and the latest strictly earlier eligible same-season calendar interval from the accepted "
                   "parents and the retained provider captures, freeze the complete-case common cohort, fit exactly "
                   "CTX-HISTORY-LOGIT-V1 (h) and CTX-SITE-CALENDAR-LOGIT-V1 (h, s, c) on its 2016-2022 games with the "
                   "unchanged accepted lambda-1 solver, score every target once per model, project the five unchanged "
                   "C56 game-score comparators on the same cohort and serve six grains through the explicit "
                   "--context-association mode; adverse and null results are completed results.",
        "research_authority": {
            "grant": "CREATE_ONLY_RESEARCH_AND_TWO_FROZEN_FITS (Cycle #63 Attempt #1 sealed contract)",
            "fits": list(ca.NEW_MODELS), "fit_seasons": list(ca.FIT_SEASONS),
            "comparison": "2023, ALREADY_EXPOSED_RETROSPECTIVE_2023_NOT_BLIND",
            "exposure": ca.LABELS["support_design_exposure"],
            "not_granted": ["PIT admission", "forecast", "calibration", "champion selection", "causal claim",
                            "protected 2024/2025 evaluation", "production training", "parent rewrite",
                            "default activation"]},
        "inputs": inputs, "parent_contracts": parent_contracts, "expected": expected, "rules": ca.rules_document(),
        "outputs": {"database": ca.DB_FILE, "population": ca.POPULATION,
                    "canonical_root": f"canonical/{ca.POPULATION}", "manifest_root": f"manifests/{ca.POPULATION}"},
        "consumer": {"command": "bas-retrospective-baseline-query --context-association <database>",
                     "module": "python -m aggie_analytics.retrospective_baseline.query --context-association <database>",
                     "grains": list(ca.GRAINS), "default": "never a default; explicit selection only",
                     "selectors": ca.SELECTOR_MATRIX}}


def contract_bytes(document: dict[str, Any]) -> bytes:
    return (json.dumps(document, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def generate(data_root: Path, repo_root: Path = REPO_ROOT, *, accepted: dict[str, Any] | None = None,
             captures: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """(contract document, qualification) from the pinned inputs under ``data_root`` (source only, no fit)."""
    inputs = pinned_inputs(data_root, accepted, captures)
    parent_contracts = {rel: _sha(Path(repo_root) / rel) for rel in PARENT_CONTRACT_PATHS}
    draft = {"contract_id": ca.CONTRACT_ID, "contract_sha256": None, "inputs": inputs,
             "parent_contracts": parent_contracts, "expected": {}}
    loaded = cab.load_inputs(data_root, draft)
    qualified = cab.qualify(loaded, draft)
    expected = cab.expected_from_qualification(qualified)
    return contract_document(inputs, parent_contracts, expected), qualified


def anchors_block(contract: dict[str, Any], contract_sha: str, profile: dict[str, Any] | None) -> str:
    anchors = {"contract_id": contract["contract_id"], "contract_sha256": contract_sha, "inputs": contract["inputs"],
               "parent_contracts": contract["parent_contracts"], "expected": contract["expected"]}
    text = json.dumps(anchors, indent=1, ensure_ascii=True)
    profile_text = "None" if profile is None else "json.loads(r'''" + json.dumps(profile, indent=1,
                                                                                  ensure_ascii=True) + "''')"
    if "'''" in text:
        raise SystemExit("anchors text holds a triple quote")
    return (BEGIN +
            "#: The pinned authority of the reader: the committed contract SHA-256, every accepted parent input "
            "(relative locator\n"
            "#: under the explicitly named data root, SHA-256, bytes, identities), the parent contracts and the "
            "expected collection\n"
            "#: of every grain (the targets, the frozen excluded games with their reasons, the parent witness digest "
            "and every key\n"
            "#: sequence digest). Generated from the accepted parents by the contract generator; never hand edited.\n"
            "ANCHORS: dict[str, Any] = json.loads(r'''" + text + "''')\n"
            "#: The canonical release profile the create-only build reproduces (identities and counts only; None until "
            "the first\n#: canonical write).\n"
            "CONTEXT_PROFILE: dict[str, Any] | None = " + profile_text + "\n" + END)


def profile_from_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    return {"database_identity": receipt["database_identity"], "content_identity": receipt["content_identity"],
            "database_sha256": receipt["database_sha256"], "database_bytes": receipt["database_bytes"],
            "contract_sha256": receipt["contract_sha256"], "rules_sha256": receipt["rules_sha256"],
            "row_counts": receipt["row_counts"], "table_counts": receipt["table_counts"],
            "lines_sha256": receipt["lines_sha256"], "summary_sha256": receipt["summary_sha256"],
            "census_sha256": receipt["census_sha256"]}


def patch_module(module: Path, block: str) -> None:
    text = Path(module).read_text(encoding="utf-8")
    start, end = text.index(BEGIN), text.index(END) + len(END)
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise SystemExit("the module must hold exactly one GENERATED ANCHORS block")
    Path(module).write_bytes((text[:start] + block + text[end:]).encode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="make_site_calendar_contract", allow_abbrev=False,
                                     description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--contract-out", required=True, type=Path)
    parser.add_argument("--module", type=Path, default=None)
    parser.add_argument("--profile", type=Path, default=None, help="a first canonical build receipt to pin")
    args = parser.parse_args(argv)
    contract, qualified = generate(args.data_root)
    data = contract_bytes(contract)
    contract_sha = hashlib.sha256(data).hexdigest()
    profile = None
    if args.profile is not None:
        if not args.contract_out.is_file() or args.contract_out.read_bytes() != data:
            raise SystemExit("--profile requires the committed contract to be byte-identical to the regenerated one")
        receipt = json.loads(args.profile.read_text(encoding="utf-8"))
        if receipt.get("contract_sha256") != contract_sha:
            raise SystemExit("the build receipt names another contract")
        profile = profile_from_receipt(receipt)
    else:
        args.contract_out.write_bytes(data)
    if args.module is not None:
        patch_module(args.module, anchors_block(contract, contract_sha, profile))
    counts = contract["expected"]["counts"]
    print(json.dumps({"contract": str(args.contract_out), "contract_sha256": contract_sha,
                      "rules_sha256": ca.rules_sha256(), "counts": counts, "profile_pinned": profile is not None,
                      "fits_run": 0}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
