from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.data.ncaa_contest_reconciliation import normalize_team_name, stable_hash  # noqa: E402
from aggie_analytics.data.tamu_official_historical_boxscores import (  # noqa: E402
    AuthorityViolation,
    GATE_RELATIVE,
    PASS_CLASSIFICATION,
    PINNED_COUNTS,
    PROTECTED_LANE,
    SOURCE_ID,
    availability_from_participation,
    availability_from_roster_membership,
    compute_gate_identity,
    load_json,
    parse_official_box_page,
    parse_season_index_rows,
    refuse_name_only_player_merge,
    sha256_bytes,
    validate_artifact,
)


DATA_ROOT = Path(os.environ.get("AGGIE_ANALYTICS_DATA_ROOT", r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = (DATA_ROOT / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores").is_dir()


def _box_page(
    *,
    season: int = 2010,
    visitor: str = "Stephen F. Austin",
    home: str = "Texas A&M",
    date: str = "Sep 04, 2010",
    site: str = "College Station, TX",
    visitor_points: int = 7,
    home_points: int = 48,
    officials: bool = True,
    pbp: bool = True,
) -> bytes:
    official_line = "Officials: Referee: A; Umpire: B; Linesman: C;" if officials else ""
    pbp_row = "<tr><td>Tamu 1-10 at Tamu20 Tannehill, Ryan rush for 4 yards.</td></tr>" if pbp else ""
    return f"""<html><body>
    <h3>{visitor} vs {home} ({date} at {site})</h3>
    {season} Texas A&M Football
    {visitor} vs {home} ({date} at {site})
    Date: {date} Site: {site} Stadium: Kyle Field Attendance: 81287
    <table>
    <tr><td>Score by Quarters</td><td>1</td><td>Score</td></tr>
    <tr><td>{visitor}</td><td>0</td><td>{visitor_points}</td></tr>
    <tr><td>{home}</td><td>7</td><td>{home_points}</td></tr>
    </table>
    Kickoff time: 6:00 PM End of Game: 9:00 PM Total elapsed time: 3:00
    {official_line}
    Temperature: 90 Wind: S 5 Weather: Clear
    <a name="GAME.TEM"></a>
    <table>
    <tr><td>Team Totals</td><td>VIS</td><td>TAMU</td></tr>
    <tr><td>FIRST DOWNS</td><td>10</td><td>20</td></tr>
    <tr><td>Penalties-Yards</td><td>5-40</td><td>4-30</td></tr>
    <tr><td>Fumbles-Lost</td><td>1-1</td><td>0-0</td></tr>
    </table>
    <a name="GAME.IND"></a>
    <table><tr><td>Texas A&M</td></tr></table>
    <table>
    <tr><td>RUSHING</td><td>No.</td></tr>
    <tr><td>Gray, Cyrus</td><td>10</td></tr>
    <tr><td>Hunter, Justin</td><td>2</td></tr>
    </table>
    <a name="GAME.NEW"></a>
    Scoring Summary:
    1st 10:00 TAMU - Gray, Cyrus 1 yd run, SFA 0 - TAMU 7
    Officials: Referee: A; Umpire: B; Linesman: C;
    Game Starters:
    Texas A&M
    POS  ## OFFENSE
    QB   17 Tannehill, Ryan
    RB   2 Gray, Cyrus
    WR   2 Hunter, Justin
    Player participation:
    Texas A&M: 17-Tannehill, Ryan, 2-Gray, Cyrus, 2-Hunter, Justin.
    <a name="GAME.PLY"></a>
    <table>{pbp_row}</table>
    </body></html>""".encode("utf-8")


def _index_page() -> bytes:
    return b"""<html><body><h2>Football: 2010 Season Stats</h2>
    <table>
    <tr><th>Date</th><th>Opponent</th><th>Location</th><th>Result</th><th>Box Score</th></tr>
    <tr><td>Sep 4</td><td>Stephen F. Austin</td><td>College Station</td><td>W, 48-7</td>
    <td><a href="../stats/2010-2011/ta01-sfa.html">Box Score</a></td></tr>
    <tr><td>Sep 11</td><td>Louisiana Tech</td><td>College Station</td><td>W, 48-16</td>
    <td><a href="../stats/2010-2011/ta02-lat.html">Box Score</a></td></tr>
    <tr><td>Sep 18</td><td>FIU</td><td>College Station</td><td>W, 27-20</td>
    <td><a href="../stats/2010-2011/ta03-fiu.html">Box Score</a></td></tr>
    <tr><td>Sep 30</td><td>*Oklahoma State</td><td>Stillwater, Okla.</td><td>L, 35-38</td>
    <td><a href="../stats/2010-2011/ta04-osu.html">Box Score</a></td></tr>
    <tr><td>Oct 9</td><td>%vs. Arkansas</td><td>Arlington, Texas</td><td>L, 17-24</td>
    <td><a href="../stats/2010-2011/ta05-ark.html">Box Score</a></td></tr>
    <tr><td>Oct 16</td><td>*Missouri</td><td>College Station</td><td>L, 9-30</td>
    <td><a href="../stats/2010-2011/ta06-miz.html">Box Score</a></td></tr>
    <tr><td>Oct 23</td><td>*Kansas</td><td>Lawrence, Kan.</td><td>W, 45-10</td>
    <td><a href="../stats/2010-2011/ta07-ku.html">Box Score</a></td></tr>
    <tr><td>Oct 30</td><td>*Texas Tech</td><td>College Station</td><td>W, 45-27</td>
    <td><a href="../stats/2010-2011/ta08-ttu.html">Box Score</a></td></tr>
    <tr><td>Nov 6</td><td>*Oklahoma</td><td>College Station</td><td>W, 33-19</td>
    <td><a href="../stats/2010-2011/ta09-ou.html">Box Score</a></td></tr>
    <tr><td>Nov 13</td><td>*Baylor</td><td>Waco, Texas</td><td>W, 42-30</td>
    <td><a href="../stats/2010-2011/ta10-bu.html">Box Score</a></td></tr>
    <tr><td>Nov 20</td><td>*Nebraska</td><td>College Station</td><td>W, 9-6</td>
    <td><a href="../stats/2010-2011/ta11-nu.html">Box Score</a></td></tr>
    <tr><td>Nov 25</td><td>*Texas</td><td>Austin, Texas</td><td>W, 24-17</td>
    <td><a href="../stats/2010-2011/ta12-ut.html">Box Score</a></td></tr>
    <tr><td>Dec 31</td><td>!vs. LSU</td><td>Arlington, Texas</td><td>L, 24-41</td>
    <td><a href="../stats/2010-2011/ta13-lsu.html">Box Score</a></td></tr>
    </table></body></html>"""


def _mutated(gate: dict, **changes) -> dict:
    tampered = json.loads(json.dumps(gate))
    tampered.update(changes)
    if "games" in changes:
        tampered["games_identity"] = stable_hash(tampered.get("games"))
        tampered["coverage_identity"] = stable_hash(tampered.get("domain_coverage"))
    tampered["dataset_identity"] = stable_hash(
        {"games": tampered.get("games"), "counts": tampered.get("counts"), "domain_coverage": tampered.get("domain_coverage")}
    )
    tampered["gate_identity"] = compute_gate_identity(tampered)
    return tampered


class OfficialHistoricalBoxscoreTests(unittest.TestCase):
    def test_wrong_season_page_is_rejected(self) -> None:
        body = _box_page(season=2011)
        with self.assertRaises(AuthorityViolation):
            parse_official_box_page(
                body,
                url="https://files.12thman.com/history/football/stats/2010-2011/ta01-sfa.html",
                source_season=2010,
                raw_sha256=sha256_bytes(body),
            )

    def test_calendar_year_is_not_football_season(self) -> None:
        body = _box_page(season=2010, visitor="LSU", date="Jan 07, 2011", site="Arlington, Texas", visitor_points=41, home_points=24)
        parsed = parse_official_box_page(
            body,
            url="https://files.12thman.com/history/football/stats/2010-2011/ta13-lsu.html",
            source_season=2010,
            raw_sha256=sha256_bytes(body),
        )
        self.assertEqual(2010, parsed["football_season"])
        self.assertEqual("2011-01-07", parsed["calendar_date"])
        with self.assertRaises(AuthorityViolation):
            parse_official_box_page(
                body,
                url="https://files.12thman.com/history/football/stats/2011-2012/ta13-lsu.htm",
                source_season=2011,
                raw_sha256=sha256_bytes(body),
            )

    def test_swapped_team_orientation_does_not_reassign_tamu_score(self) -> None:
        body = _box_page()
        parsed = parse_official_box_page(
            body,
            url="https://files.12thman.com/history/football/stats/2010-2011/ta01-sfa.html",
            source_season=2010,
            raw_sha256=sha256_bytes(body),
        )
        self.assertEqual(48, parsed["tamu_points"])
        self.assertEqual(7, parsed["opponent_points"])
        self.assertEqual("home", parsed["tamu_side"])

    def test_duplicate_jersey_numbers_remain_candidates(self) -> None:
        body = _box_page()
        parsed = parse_official_box_page(
            body,
            url="https://files.12thman.com/history/football/stats/2010-2011/ta01-sfa.html",
            source_season=2010,
            raw_sha256=sha256_bytes(body),
        )
        jerseys = [row["jersey_raw"] for row in parsed["starters"]]
        self.assertGreaterEqual(jerseys.count("2"), 2)
        self.assertTrue(all(row["availability"] == "NOT_ESTABLISHED" for row in parsed["starters"]))
        self.assertTrue(all(row["identity_status"] == "SOURCE_PLAYER_CANDIDATE" for row in parsed["participation"]))

    def test_name_only_player_merge_is_forbidden(self) -> None:
        with self.assertRaises(AuthorityViolation):
            refuse_name_only_player_merge([{"name_raw": "Tannehill, Ryan", "jersey_raw": "17"}])

    def test_participation_does_not_establish_availability(self) -> None:
        with self.assertRaises(AuthorityViolation):
            availability_from_participation({"name_raw": "Tannehill, Ryan"})

    def test_roster_membership_does_not_establish_availability(self) -> None:
        with self.assertRaises(AuthorityViolation):
            availability_from_roster_membership({"name_raw": "Tannehill, Ryan"})

    def test_missing_officials_are_classified_absent_not_inferred(self) -> None:
        body = _box_page(officials=False).replace(b"Officials: Referee: A; Umpire: B; Linesman: C;", b"")
        parsed = parse_official_box_page(
            body,
            url="https://files.12thman.com/history/football/stats/2010-2011/ta01-sfa.html",
            source_season=2010,
            raw_sha256=sha256_bytes(body),
        )
        self.assertEqual("ABSENT", parsed["domain_coverage"]["officials"])

    def test_missing_play_by_play_is_classified_absent(self) -> None:
        body = _box_page(pbp=False)
        parsed = parse_official_box_page(
            body,
            url="https://files.12thman.com/history/football/stats/2010-2011/ta01-sfa.html",
            source_season=2010,
            raw_sha256=sha256_bytes(body),
        )
        self.assertEqual("ABSENT", parsed["domain_coverage"]["play_by_play"])

    def test_changed_raw_source_hash_is_rejected(self) -> None:
        body = _box_page()
        with self.assertRaises(AuthorityViolation):
            parse_official_box_page(
                body,
                url="https://files.12thman.com/history/football/stats/2010-2011/ta01-sfa.html",
                source_season=2010,
                raw_sha256="00" * 32,
            )

    def test_season_index_rows_bind_box_urls_not_guessed_names(self) -> None:
        rows = parse_season_index_rows(
            _index_page(),
            2010,
            "https://files.12thman.com/history/football/years/2010.html",
        )
        self.assertEqual(13, len(rows))
        self.assertTrue(rows[0]["box_url"].endswith("/ta01-sfa.html"))
        self.assertEqual("lsu", rows[-1]["opponent_normalized"])
        self.assertEqual("2010-12-31", rows[-1]["index_date_candidate"])

    def test_committed_gate_is_src014_not_ncaa(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        self.assertEqual(SOURCE_ID, gate["source_id"])
        self.assertEqual(PASS_CLASSIFICATION, gate["classification"])
        self.assertEqual(PROTECTED_LANE, gate["protected_lane"])
        self.assertEqual(PINNED_COUNTS, gate["counts"])
        self.assertEqual(0, gate["counts"]["ncaa_contest_ids_created"])
        self.assertEqual(26, gate["counts"]["captured_pages_total"])
        self.assertEqual(25, gate["counts"]["matched_strong_tuple"])
        self.assertEqual(1, gate["counts"]["date_conflicts"])
        texas = next(item for item in gate["games"] if item["source_season"] == 2011 and item["opponent_normalized"] == normalize_team_name("Texas"))
        self.assertEqual("2011-11-24", texas["calendar_date"])
        self.assertEqual(25, texas["tamu_points"])
        self.assertEqual(27, texas["opponent_points"])
        self.assertEqual("Kyle Field", texas["stadium"])
        self.assertIsNone(texas["ncaa_contest_id"])
        lsu = next(item for item in gate["games"] if item["source_season"] == 2010 and item["opponent_normalized"] == normalize_team_name("LSU"))
        self.assertEqual("2011-01-07", lsu["calendar_date"])
        self.assertEqual(2010, lsu["football_season"])
        self.assertEqual("SEASON_INDEX_DATE_VS_BOX_PLAYED_DATE", lsu["conflict_status"])
        self.assertTrue(all(item.get("historical_publication_time") is None for item in gate["games"]))
        self.assertTrue(all(item.get("availability_claim") is False for item in gate["games"]))

    def test_truthful_gate_validates(self) -> None:
        result = validate_artifact(
            data_root=DATA_ROOT if LAKE_READY else Path(tempfile.mkdtemp()),
            repo_root=ROOT,
            require_rebuild=LAKE_READY,
        )
        self.assertEqual("PASS", result["result"])

    def test_altered_score_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["tamu_points"] = 999
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_altered_opponent_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["opponent_candidate"] = "Fabricated State"
        games[0]["opponent_normalized"] = "fabricated state"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_altered_date_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["calendar_date"] = "1999-01-01"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_duplicate_page_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games.append(json.loads(json.dumps(games[0])))
        counts = json.loads(json.dumps(gate["counts"]))
        counts["captured_pages_total"] = 27
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games, counts=counts))

    def test_changed_raw_hash_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["source_sha256"] = "00" * 32
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_incomplete_domain_reclassified_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["domain_coverage"]["officials"] = "ABSENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_fabricated_domain_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["domain_coverage"]["invented_domain"] = "PRESENT"
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_availability_claim_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["availability_claim"] = True
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, games=games))

    def test_ncaa_contest_id_invention_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        counts = json.loads(json.dumps(gate["counts"]))
        counts["ncaa_contest_ids_created"] = 1
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, counts=counts))

    def test_protected_lane_opened_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=DATA_ROOT, repo_root=ROOT, require_rebuild=False, gate=_mutated(gate, protected_lane="OPEN"))

    def test_forged_completion_after_rehash_fails(self) -> None:
        gate = load_json(ROOT / GATE_RELATIVE)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(
                data_root=DATA_ROOT,
                repo_root=ROOT,
                require_rebuild=False,
                gate=_mutated(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"),
            )


REPO_SENTINELS = (
    GATE_RELATIVE,
    "artifacts/data_lake/tamu_official_historical_archive_gate.json",
    "artifacts/pit/historical_tamu_official_gamebook_reconciliation_gate.json",
    "configs/tamu_official_historical_boxscore_contract.json",
    "jira/reconciliation/BAT_AUXILIARY_ISSUE_REGISTRY.json",
)
DATA_SENTINELS = (
    "manifests/acquisition/BAT-580-TAMU-OFFICIAL-HISTORICAL-BOXSCORES-V1/manifest.json",
    "features/tamu_official_historical_boxscores/sha256/normalized.json",
    "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive",
)


def _file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(str(path.stat().st_size).encode("ascii"))
    digest.update(b"\0")
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _snapshot_relevant(repo_root: Path, data_root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for relative in REPO_SENTINELS:
        path = repo_root / relative
        snapshot[f"repo:{relative}"] = _file_fingerprint(path)
    for relative in DATA_SENTINELS:
        path = data_root / relative
        if path.is_file():
            snapshot[f"data:{relative}"] = _file_fingerprint(path)
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file():
                snapshot[f"data:{child.relative_to(data_root).as_posix()}"] = _file_fingerprint(child)
    return snapshot


def _copy_isolated_roots() -> tuple[Path, Path]:
    repo = Path(tempfile.mkdtemp(prefix="bat584-repo-"))
    data = Path(tempfile.mkdtemp(prefix="bat584-data-"))
    for relative in REPO_SENTINELS:
        dest = repo / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, dest)
    for relative in DATA_SENTINELS:
        source = DATA_ROOT / relative
        dest = data / relative
        if source.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
        else:
            shutil.copytree(source, dest)
    return repo, data


@unittest.skipUnless(LAKE_READY, "external BAT-580 payloads are not mounted")
class ValidatorPurityTests(unittest.TestCase):
    def _assert_byte_identical(self, before: dict[str, str], after: dict[str, str]) -> None:
        self.assertEqual(before, after)

    def test_passing_validation_does_not_mutate_files(self) -> None:
        repo, data = _copy_isolated_roots()
        before = _snapshot_relevant(repo, data)
        result = validate_artifact(data_root=data, repo_root=repo, require_rebuild=True)
        self.assertEqual("PASS", result["result"])
        self.assertEqual("MOUNTED", result["external_reconstruction"])
        self._assert_byte_identical(before, _snapshot_relevant(repo, data))

    def test_tampered_score_failure_does_not_mutate_files(self) -> None:
        repo, data = _copy_isolated_roots()
        gate = load_json(repo / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["tamu_points"] = 999
        (repo / GATE_RELATIVE).write_text(json.dumps(_mutated(gate, games=games), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        before = _snapshot_relevant(repo, data)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=data, repo_root=repo, require_rebuild=True)
        self._assert_byte_identical(before, _snapshot_relevant(repo, data))

    def test_missing_raw_file_failure_does_not_mutate_files(self) -> None:
        repo, data = _copy_isolated_roots()
        raw_dir = data / "raw/SRC-014/tamu_official_gamebook_equivalent/historical_archive/box_scores"
        victim = next(raw_dir.rglob("*.html"))
        victim.unlink()
        before = _snapshot_relevant(repo, data)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=data, repo_root=repo, require_rebuild=True)
        self._assert_byte_identical(before, _snapshot_relevant(repo, data))

    def test_changed_domain_coverage_failure_does_not_mutate_files(self) -> None:
        repo, data = _copy_isolated_roots()
        gate = load_json(repo / GATE_RELATIVE)
        games = json.loads(json.dumps(gate["games"]))
        games[0]["domain_coverage"]["officials"] = "ABSENT"
        (repo / GATE_RELATIVE).write_text(json.dumps(_mutated(gate, games=games), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        before = _snapshot_relevant(repo, data)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=data, repo_root=repo, require_rebuild=True)
        self._assert_byte_identical(before, _snapshot_relevant(repo, data))

    def test_forged_completion_failure_does_not_mutate_files(self) -> None:
        repo, data = _copy_isolated_roots()
        gate = load_json(repo / GATE_RELATIVE)
        (repo / GATE_RELATIVE).write_text(
            json.dumps(_mutated(gate, result="FORGED_DONE", classification="PRODUCTION_CHAMPION"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        before = _snapshot_relevant(repo, data)
        with self.assertRaises(AuthorityViolation):
            validate_artifact(data_root=data, repo_root=repo, require_rebuild=True)
        self._assert_byte_identical(before, _snapshot_relevant(repo, data))


if __name__ == "__main__":
    unittest.main()
