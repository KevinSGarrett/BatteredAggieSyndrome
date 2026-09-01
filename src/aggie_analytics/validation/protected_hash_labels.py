from __future__ import annotations

from hashlib import sha256
from pathlib import Path

PROTECTED_SPLIT = "governance/PROTECTED_SPLIT_REGISTRY.csv"
PROTECTED_JUDGING_CSV = "governance/PROTECTED_JUDGING_RULE_SEAL.csv"
JUDGING_RULE_JSON = "configs/judging_rule_seal.json"

EXPECTED = {
    PROTECTED_SPLIT: "6b90ef6fb09abd89d7a82a8b5835b00615671a7742839269c7401a2d0af5f764",
    PROTECTED_JUDGING_CSV: "7bf245d93d1d0fc6b87f55dddcacec76ced222279ffa09b7b1ab08ba36667356",
    JUDGING_RULE_JSON: "8e1cb61d850babc5e80bd156aa79f6bbd5575d461df0d83ec6f6eed2a71fe758",
}


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def protected_hash_label_report(repo_root: Path) -> dict[str, str]:
    return {
        "protected_split_registry_path": PROTECTED_SPLIT,
        "protected_split_registry_sha256": file_sha256(repo_root / PROTECTED_SPLIT),
        "protected_judging_rule_seal_csv_path": PROTECTED_JUDGING_CSV,
        "protected_judging_rule_seal_csv_sha256": file_sha256(
            repo_root / PROTECTED_JUDGING_CSV
        ),
        "judging_rule_seal_json_path": JUDGING_RULE_JSON,
        "judging_rule_seal_json_sha256": file_sha256(repo_root / JUDGING_RULE_JSON),
    }


def validate_protected_hash_labels(
    repo_root: Path, labels: dict[str, str] | None = None
) -> list[str]:
    report = labels if labels is not None else protected_hash_label_report(repo_root)
    findings: list[str] = []
    mapping = {
        "protected_split_registry_sha256": PROTECTED_SPLIT,
        "protected_judging_rule_seal_csv_sha256": PROTECTED_JUDGING_CSV,
        "judging_rule_seal_json_sha256": JUDGING_RULE_JSON,
    }
    for field, relative in mapping.items():
        actual = file_sha256(repo_root / relative)
        labeled = report.get(field)
        expected = EXPECTED[relative]
        if actual != expected:
            findings.append(f"protected_artifact_hash_drift:{relative}")
        if labeled != actual:
            findings.append(f"label_does_not_match_file:{field}")
        if labeled != expected:
            findings.append(f"label_does_not_match_pinned_identity:{field}")
    csv_hash = report.get("protected_judging_rule_seal_csv_sha256")
    json_hash = report.get("judging_rule_seal_json_sha256")
    split_hash = report.get("protected_split_registry_sha256")
    if csv_hash == json_hash:
        findings.append("protected_hash_labels_swapped_or_conflated:csv_json")
    if csv_hash == split_hash:
        findings.append("protected_hash_labels_swapped_or_conflated:csv_split")
    if json_hash == split_hash:
        findings.append("protected_hash_labels_swapped_or_conflated:json_split")
    if report.get("protected_judging_rule_seal_csv_path") == JUDGING_RULE_JSON:
        findings.append("protected_hash_labels_swapped:csv_path_points_at_json")
    if report.get("judging_rule_seal_json_path") == PROTECTED_JUDGING_CSV:
        findings.append("protected_hash_labels_swapped:json_path_points_at_csv")
    return findings
