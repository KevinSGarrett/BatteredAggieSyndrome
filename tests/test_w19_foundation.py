from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
import hashlib
from aggie_analytics.data.adapters import CsvSourceAdapter
from aggie_analytics.data.snapshots import RawSnapshotStore
from aggie_analytics.entities.contracts import SourceEntityKey
from aggie_analytics.entities.resolution import AliasRecord, EntityResolver
from aggie_analytics.temporal.contracts import TemporalObservation, ForecastCutoff
from aggie_analytics.temporal.state import build_pit_state
from aggie_analytics.features.factory import FeatureSpec, build_features

ROOT=Path(__file__).resolve().parents[1]
def dt(s): return datetime.fromisoformat(s.replace('Z','+00:00'))

def test_raw_snapshot_is_content_addressed_and_immutable():
    src=ROOT/'fixtures/w19/recon_real/schedules_real_row.csv'
    rows=CsvSourceAdapter('SRC-001','schedules').read(src)
    with TemporaryDirectory() as td:
        store=RawSnapshotStore(Path(td)); a=store.ingest_file('SRC-001','schedules',src,retrieved_at=dt('2026-08-08T20:00:00Z'),source_uri='recon://sportsdataverse/real_game_401628455',row_count=len(rows),schema_fields=tuple(rows[0].payload))
        b=store.ingest_file('SRC-001','schedules',src,retrieved_at=dt('2026-08-08T20:00:00Z'),source_uri='recon://sportsdataverse/real_game_401628455',row_count=len(rows),schema_fields=tuple(rows[0].payload))
        assert a.snapshot_id==b.snapshot_id and a.raw_sha256==hashlib.sha256(src.read_bytes()).hexdigest()
        assert (Path(td)/a.relative_path).read_bytes()==src.read_bytes()

def test_entity_resolution_fail_closed():
    resolver=EntityResolver([AliasRecord('team','Texas A&M','team_'+'a'*32,'SRC-001')])
    ok=resolver.resolve(SourceEntityKey('SRC-001','team','atm'),'Texas A&M','resdec_'+'b'*32)
    miss=resolver.resolve(SourceEntityKey('SRC-001','team','zzz'),'Unknown College','resdec_'+'c'*32)
    assert ok.decision_state=='RESOLVED' and ok.selected_canonical_id
    assert miss.decision_state=='UNRESOLVED' and miss.selected_canonical_id is None

def test_pit_excludes_future_game_and_feature_uses_only_eligible_parent():
    prior=TemporalObservation.from_mapping({'observation_id':'obs_prior','source_observation_id':'src_prior','domain':'HISTORICAL_GAME_OUTPUT','retrieved_at':'2026-09-06T00:00:00Z','first_known_at':'2026-09-06T00:00:00Z','temporal_policy_version':'w08-v1.0','game_end_at':'2026-09-05T04:00:00Z','points_for':31})
    future=TemporalObservation.from_mapping({'observation_id':'obs_future','source_observation_id':'src_future','domain':'HISTORICAL_GAME_OUTPUT','retrieved_at':'2026-09-13T05:00:00Z','first_known_at':'2026-09-13T05:00:00Z','temporal_policy_version':'w08-v1.0','game_end_at':'2026-09-13T04:00:00Z','points_for':28})
    cutoff=ForecastCutoff('w19-cutoff','FORECAST_SNAPSHOT',dt('2026-09-11T12:00:00Z'),dt('2026-09-12T17:00:00Z'),'PURE_FOOTBALL','w08-v1.0','snap_test')
    state=build_pit_state([prior,future],cutoff)
    assert [o.observation_id for o in state.observations]==['obs_prior']
    fv=build_features(state,[FeatureSpec('f_points','HISTORICAL_GAME_OUTPUT','points_for','MEAN')])
    assert fv.values['f_points']==31.0
    assert fv.lineage[0].parent_ids==('obs_prior',)
