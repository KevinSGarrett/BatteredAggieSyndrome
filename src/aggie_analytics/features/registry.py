from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv

BANNED_HANDOFF={"BANNED_FROM_PREGAME","TEMPORAL_REVIEW_REQUIRED","EVIDENCE_OR_METADATA_ONLY","HISTORICAL_OR_LIVE_DERIVATION_ONLY"}

@dataclass(frozen=True)
class RawFieldRecord:
    raw_field_id:str
    source_id:str
    source:str
    dataset_or_model:str
    field_path:str
    normalized_temporal_class:str
    handoff_state:str
    pit_gateway_required:bool
    w10_candidate_experiment_allowed:bool

def _bool(v:str)->bool:
    return str(v).strip().lower()=="true"

def load_raw_field_registry(path:Path)->tuple[RawFieldRecord,...]:
    with path.open(newline="",encoding="utf-8") as fh:
        rows=[]
        for r in csv.DictReader(fh):
            rows.append(RawFieldRecord(r["raw_field_id"],r["source_id"],r["source"],r["dataset_or_model"],r["field_path"],r["normalized_temporal_class"],r["handoff_state"],_bool(r["pit_gateway_required"]),_bool(r["w10_candidate_experiment_allowed"])))
    return tuple(rows)

def candidate_handoff_allowed(field:RawFieldRecord)->bool:
    return field.w10_candidate_experiment_allowed and field.pit_gateway_required and field.handoff_state not in BANNED_HANDOFF
