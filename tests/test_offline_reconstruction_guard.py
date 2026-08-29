from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from aggie_analytics.data.offline_reconstruction import (  # noqa: E402
    DATA_ROOT_ENV,
    FIXTURE_HASH_DRIFT,
    FIXTURE_MISSING,
    LAKE_ONLY_ENV,
    NETWORK_FORBIDDEN_ENV,
    NETWORK_NOT_PERMITTED,
    assert_network_permitted,
    data_root_is_mounted,
    network_forbidden,
    require_fixture,
)
from aggie_analytics.data.season_index_offline_reconstruction import (  # noqa: E402
    committed_gate,
    reconstruct_season_index,
)
from aggie_analytics.data.tamu_official_historical_archive import (  # noqa: E402
    AuthorityViolation,
    direct_http_get,
)

OFFLINE_SEASONS = (1996, 1997, 1998)
OFFICIAL_PROBE_URL = "https://files.12thman.com/history/football/years/1996.html"


class EnvironmentPredicateTests(unittest.TestCase):
    """A mounted lake authorizes reconstruction; it never authorizes a socket."""

    def setUp(self) -> None:
        self._saved = {
            name: os.environ.get(name)
            for name in (DATA_ROOT_ENV, NETWORK_FORBIDDEN_ENV, LAKE_ONLY_ENV)
        }

    def tearDown(self) -> None:
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_a_mounted_data_root_is_reported_as_mounted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ[DATA_ROOT_ENV] = td
            self.assertTrue(data_root_is_mounted())

    def test_an_unset_data_root_is_reported_as_unmounted(self) -> None:
        os.environ.pop(DATA_ROOT_ENV, None)
        self.assertFalse(data_root_is_mounted())

    def test_a_data_root_pointing_at_a_missing_directory_is_unmounted(self) -> None:
        os.environ[DATA_ROOT_ENV] = str(Path(tempfile.gettempdir()) / "absent-lake-27a91f")
        self.assertFalse(data_root_is_mounted())

    def test_a_mounted_data_root_does_not_authorize_network_access(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ[DATA_ROOT_ENV] = td
            os.environ[NETWORK_FORBIDDEN_ENV] = "1"
            self.assertTrue(data_root_is_mounted())
            self.assertTrue(network_forbidden())
            with self.assertRaisesRegex(AuthorityViolation, NETWORK_NOT_PERMITTED):
                assert_network_permitted("regression probe")

    def test_lake_only_reconstruction_also_refuses_acquisition(self) -> None:
        os.environ.pop(NETWORK_FORBIDDEN_ENV, None)
        os.environ[LAKE_ONLY_ENV] = "true"
        with self.assertRaisesRegex(AuthorityViolation, NETWORK_NOT_PERMITTED):
            assert_network_permitted("regression probe")

    def test_the_shared_choke_point_blocks_acquisition_under_either_flag(self) -> None:
        """Every official season-index fetch funnels through direct_http_get."""

        for flag in (NETWORK_FORBIDDEN_ENV, LAKE_ONLY_ENV):
            with self.subTest(flag=flag):
                os.environ.pop(NETWORK_FORBIDDEN_ENV, None)
                os.environ.pop(LAKE_ONLY_ENV, None)
                os.environ[flag] = "1"
                with self.assertRaises(AuthorityViolation):
                    direct_http_get(OFFICIAL_PROBE_URL)

    def test_a_mounted_lake_alone_never_unblocks_the_choke_point(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            os.environ[DATA_ROOT_ENV] = td
            os.environ[NETWORK_FORBIDDEN_ENV] = "1"
            self.assertTrue(data_root_is_mounted())
            with self.assertRaises(AuthorityViolation):
                direct_http_get(OFFICIAL_PROBE_URL)

    def test_an_explicitly_authorized_acquisition_command_is_not_blocked(self) -> None:
        """Operator builds keep their acquisition path; only the guard is checked here."""

        os.environ.pop(NETWORK_FORBIDDEN_ENV, None)
        os.environ.pop(LAKE_ONLY_ENV, None)
        assert_network_permitted("explicit operator acquisition command")


class FixtureContractTests(unittest.TestCase):
    def test_a_missing_fixture_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(AuthorityViolation, FIXTURE_MISSING):
                require_fixture(
                    Path(td) / "absent.html", expected_sha256=None, description="probe"
                )

    def test_an_altered_fixture_hash_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "capture.html"
            path.write_bytes(b"<html>original</html>")
            expected = hashlib.sha256(b"<html>original</html>").hexdigest()
            self.assertEqual(
                require_fixture(path, expected_sha256=expected, description="probe"),
                b"<html>original</html>",
            )
            path.write_bytes(b"<html>tampered</html>")
            with self.assertRaisesRegex(AuthorityViolation, FIXTURE_HASH_DRIFT):
                require_fixture(path, expected_sha256=expected, description="probe")

    def test_reading_a_fixture_does_not_modify_it(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "capture.html"
            path.write_bytes(b"<html>immutable</html>")
            before = (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
            require_fixture(path, expected_sha256=before[1], description="probe")
            after = (path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(before, after)


LAKE_ROOT = Path(os.environ.get(DATA_ROOT_ENV, r"C:\BatteredAggieSyndrome.data"))
LAKE_READY = bool(os.environ.get(DATA_ROOT_ENV)) and LAKE_ROOT.is_dir()


@unittest.skipUnless(LAKE_READY, "external data root is not mounted")
class OfflineSeasonIndexReconstructionTests(unittest.TestCase):
    """The deterministic read path works with the network forbidden and writes nothing."""

    def setUp(self) -> None:
        self._saved = os.environ.get(NETWORK_FORBIDDEN_ENV)
        os.environ[NETWORK_FORBIDDEN_ENV] = "1"

    def tearDown(self) -> None:
        if self._saved is None:
            os.environ.pop(NETWORK_FORBIDDEN_ENV, None)
        else:
            os.environ[NETWORK_FORBIDDEN_ENV] = self._saved

    def test_each_season_reproduces_its_committed_gate_without_network(self) -> None:
        for season in OFFLINE_SEASONS:
            with self.subTest(season=season):
                committed = committed_gate(season, repo_root=REPO_ROOT)
                rebuilt = reconstruct_season_index(
                    season, repo_root=REPO_ROOT, data_root=LAKE_ROOT, gate=committed
                )
                self.assertEqual(rebuilt["gate"], committed)

    def test_reconstruction_is_byte_stable_across_repeated_runs(self) -> None:
        for season in OFFLINE_SEASONS:
            with self.subTest(season=season):
                first = reconstruct_season_index(
                    season, repo_root=REPO_ROOT, data_root=LAKE_ROOT
                )["gate"]
                second = reconstruct_season_index(
                    season, repo_root=REPO_ROOT, data_root=LAKE_ROOT
                )["gate"]
                self.assertEqual(first, second)

    def test_an_unknown_season_has_no_offline_route(self) -> None:
        with self.assertRaisesRegex(AuthorityViolation, "no offline season-index route"):
            reconstruct_season_index(1899, repo_root=REPO_ROOT, data_root=LAKE_ROOT)

    def test_a_gate_without_a_capture_path_fails_closed(self) -> None:
        committed = committed_gate(1996, repo_root=REPO_ROOT)
        committed["capture"] = {}
        with self.assertRaisesRegex(AuthorityViolation, "missing raw_relative_path"):
            reconstruct_season_index(
                1996, repo_root=REPO_ROOT, data_root=LAKE_ROOT, gate=committed
            )

    def test_a_forged_capture_hash_fails_closed(self) -> None:
        committed = committed_gate(1996, repo_root=REPO_ROOT)
        committed["capture"] = dict(committed["capture"], raw_sha256="0" * 64)
        with self.assertRaisesRegex(AuthorityViolation, FIXTURE_HASH_DRIFT):
            reconstruct_season_index(
                1996, repo_root=REPO_ROOT, data_root=LAKE_ROOT, gate=committed
            )


if __name__ == "__main__":
    unittest.main()
