r"""TP37-S path lifecycle tests.

Each test here corresponds to a way the previous fixed-root/hardcoded-seed
code could destroy or silently misuse a directory:

* a missing or mislabelled seed used to be read anyway (it was a literal),
* a fixed scratch root used to be ``rmtree``'d with ``ignore_errors=True``,
* a root too long for MAX_PATH used to fail as a "qualification failure",
* two concurrent runs used to share one path,
* a reparse point inside a scratch root used to be a way out of it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.workspace.paths import (  # noqa: E402
    MAX_ROOT_LENGTH,
    PATH_BUDGET_TOTAL,
    WORST_CASE_RELATIVE_LENGTH,
    PathBudgetExceeded,
    SeedContractError,
    UnownedWorkspace,
    UnsafeNameComponent,
    WorkspaceBoundaryError,
    WorkspaceError,
    allocate_run_workspace,
    assert_within,
    atomic_write_bytes,
    atomic_write_json,
    check_path_budget,
    clear_owned_subtree,
    prepare_explicit_workspace,
    require_free_bytes,
    resolve_layout,
    resolve_seed,
    seed_entry_digests,
)


def make_directory_reparse_point(link: Path, target: Path) -> str:
    """Create a directory reparse point, by whichever route this host allows.

    A symbolic link needs ``SeCreateSymbolicLinkPrivilege``, which an ordinary
    session does not hold, so the reparse-point coverage used to skip on this
    machine -- on exactly the boundary MF37-01 and MF37-02 are about. A
    directory *junction* is also a reparse point and needs no privilege, so it
    is tried next and the cases actually execute.

    Cycle #37 — Attempt #3 — the junction is made in-process first
    (``_winapi.CreateJunction``, the call ``mklink /J`` itself makes). The
    attempt's lanes run tests under the canonical write guard, which refuses a
    shell child, and the ``cmd`` route alone turned these three cases into
    skips there. The shell route stays as the fallback.

    Returns the mechanism used, or raises ``OSError`` if neither is available.
    """

    try:
        link.symlink_to(target, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        pass
    if os.name != "nt":
        raise OSError("no reparse-point mechanism available on this platform")
    try:
        import _winapi

        _winapi.CreateJunction(str(target), str(link))
        if link.exists():
            return "junction"
    except (ImportError, AttributeError, OSError):
        pass
    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0 or not link.exists():
        raise OSError(
            f"mklink /J failed: rc={completed.returncode} "
            f"{(completed.stdout + completed.stderr).strip()}"
        )
    return "junction"


class LayoutResolutionTests(unittest.TestCase):
    """A root must say where it came from, not just what it is."""

    def test_declared_defaults_are_the_existing_directory_family(self) -> None:
        layout = resolve_layout(env={})
        self.assertEqual(
            str(layout.root("data")), r"C:\BatteredAggieSyndrome.data"
        )
        self.assertEqual(layout.source("data"), "declared_default")
        # No C:\bas* root may become a default again.
        for name, root in layout.roots.items():
            self.assertNotRegex(
                str(root).lower(),
                r"^c:\\bas(?!ic)",
                f"{name} resolved to a short drive-root alias",
            )

    def test_environment_overrides_default_and_is_recorded(self) -> None:
        layout = resolve_layout(env={"AGGIE_ANALYTICS_DATA_ROOT": r"D:\lake"})
        self.assertEqual(str(layout.root("data")), r"D:\lake")
        self.assertEqual(layout.source("data"), "env:AGGIE_ANALYTICS_DATA_ROOT")

    def test_explicit_override_wins_over_environment(self) -> None:
        layout = resolve_layout(
            overrides={"validation": r"D:\explicit"},
            env={"BAS_VALIDATION_ROOT": r"D:\from-env"},
        )
        self.assertEqual(str(layout.root("validation")), r"D:\explicit")
        self.assertEqual(layout.source("validation"), "explicit")

    def test_registry_file_supplies_roots_and_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            registry = Path(tmp) / "registry.json"
            registry.write_text(
                json.dumps({"roots": {"validation": str(Path(tmp) / "scratch")}}),
                encoding="utf-8",
            )
            layout = resolve_layout(env={"BAS_PATH_REGISTRY": str(registry)})
            self.assertEqual(
                layout.root("validation"), Path(tmp) / "scratch"
            )
            self.assertTrue(layout.source("validation").startswith("registry:"))

    def test_missing_registry_fails_closed(self) -> None:
        with self.assertRaises(WorkspaceError):
            resolve_layout(env={"BAS_PATH_REGISTRY": r"C:\definitely\not\here.json"})

    def test_unknown_root_name_is_an_error_not_a_guess(self) -> None:
        with self.assertRaises(WorkspaceError):
            resolve_layout(env={}).root("somewhere_else")


class PathBudgetTests(unittest.TestCase):
    """The MAX_PATH constraint that produced C:\\bas* is enforced, not evaded."""

    def test_budget_arithmetic_is_declared(self) -> None:
        self.assertEqual(
            MAX_ROOT_LENGTH, PATH_BUDGET_TOTAL - WORST_CASE_RELATIVE_LENGTH
        )
        self.assertEqual(MAX_ROOT_LENGTH, 86)

    def test_designated_validation_run_root_fits_the_budget(self) -> None:
        # This is the concrete claim that makes C:\basc36lane unnecessary:
        # a run-namespaced directory under the declared .validation root fits.
        candidate = Path(
            r"C:\BatteredAggieSyndrome.validation\c36_15\20260922T031500Z_ab12cd34"
        )
        self.assertLessEqual(len(str(candidate)), MAX_ROOT_LENGTH)
        check_path_budget(candidate)  # must not raise

    def test_over_budget_root_is_refused_with_the_arithmetic(self) -> None:
        too_long = Path("C:\\" + ("x" * MAX_ROOT_LENGTH))
        with self.assertRaises(PathBudgetExceeded) as caught:
            check_path_budget(too_long)
        message = str(caught.exception)
        self.assertIn(str(PATH_BUDGET_TOTAL), message)
        self.assertIn(str(WORST_CASE_RELATIVE_LENGTH), message)

    def test_allocation_refuses_an_over_budget_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            deep = Path(tmp) / ("d" * 120)
            layout = resolve_layout(overrides={"validation": deep}, env={})
            with self.assertRaises(PathBudgetExceeded):
                allocate_run_workspace("c36_15", layout=layout)


class RunWorkspaceLifecycleTests(unittest.TestCase):
    """Ownership, uniqueness and refusal to delete what we did not create."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.scratch = Path(self._tmp.name)
        self.layout = resolve_layout(overrides={"validation": self.scratch}, env={})

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_allocation_creates_an_owned_unique_namespace(self) -> None:
        workspace = allocate_run_workspace("tool_a", layout=self.layout)
        self.assertTrue(workspace.root.is_dir())
        marker = json.loads(workspace.marker_path.read_text(encoding="utf-8"))
        self.assertEqual(marker["tool"], "tool_a")
        self.assertEqual(marker["run_id"], workspace.run_id)
        self.assertEqual(marker["pid"], os.getpid())

    def test_two_concurrent_runs_do_not_share_or_delete_each_other(self) -> None:
        first = allocate_run_workspace("c36_15", layout=self.layout, run_id="run-1")
        second = allocate_run_workspace("c36_15", layout=self.layout, run_id="run-2")
        self.assertNotEqual(first.root, second.root)

        (first.root / "evidence.json").write_text("{}", encoding="utf-8")
        second.release()

        # The old code would have deleted the shared fixed root out from under
        # the first run. The first run's evidence must survive.
        self.assertTrue((first.root / "evidence.json").is_file())
        self.assertFalse(second.root.exists())
        first.release()

    def test_existing_directory_is_never_adopted(self) -> None:
        occupied = self.scratch / "c36_15" / "run-1"
        occupied.mkdir(parents=True)
        (occupied / "someone_elses_data.txt").write_text("keep me", encoding="utf-8")
        with self.assertRaises(UnownedWorkspace):
            allocate_run_workspace("c36_15", layout=self.layout, run_id="run-1")
        self.assertTrue((occupied / "someone_elses_data.txt").is_file())

    def test_release_refuses_a_directory_without_our_marker(self) -> None:
        workspace = allocate_run_workspace("c36_15", layout=self.layout)
        workspace.marker_path.unlink()
        with self.assertRaises(UnownedWorkspace):
            workspace.release()
        self.assertTrue(workspace.root.is_dir())

    def test_release_refuses_a_marker_owned_by_another_run(self) -> None:
        workspace = allocate_run_workspace("c36_15", layout=self.layout)
        marker = json.loads(workspace.marker_path.read_text(encoding="utf-8"))
        marker["run_id"] = "some-other-run"
        workspace.marker_path.write_text(json.dumps(marker), encoding="utf-8")
        with self.assertRaises(UnownedWorkspace):
            workspace.release()
        self.assertTrue(workspace.root.is_dir())

    def test_release_of_absent_workspace_is_explicit_by_default(self) -> None:
        workspace = allocate_run_workspace("c36_15", layout=self.layout)
        workspace.release()
        with self.assertRaises(WorkspaceError):
            workspace.release()
        self.assertEqual(
            workspace.release(missing_ok=True)["state"], "ALREADY_ABSENT"
        )

    def test_release_stays_inside_the_declared_scratch_root(self) -> None:
        workspace = allocate_run_workspace("c36_15", layout=self.layout)
        # Point the workspace at somewhere outside the declared root and prove
        # the boundary check, not the marker, stops it.
        with tempfile.TemporaryDirectory() as outside:
            escaped = Path(outside) / "not-ours"
            escaped.mkdir()
            workspace.root = escaped
            with self.assertRaises(WorkspaceError):
                workspace.release()
            self.assertTrue(escaped.is_dir())


class BoundaryTests(unittest.TestCase):
    def test_assert_within_accepts_descendants(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = root / "a" / "b"
            child.mkdir(parents=True)
            self.assertEqual(assert_within(root, child), child.resolve())

    def test_assert_within_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "inside"
            root.mkdir()
            with self.assertRaises(WorkspaceBoundaryError):
                assert_within(root, root / ".." / "outside")

    def test_reparse_point_cannot_carry_a_delete_out_of_the_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "scratch"
            root.mkdir()
            target = Path(tmp) / "canonical"
            target.mkdir()
            (target / "precious.json").write_text("{}", encoding="utf-8")
            link = root / "escape"
            try:
                make_directory_reparse_point(link, target)
            except OSError as error:  # pragma: no cover
                self.skipTest(f"no reparse-point mechanism available: {error}")
            with self.assertRaises(WorkspaceBoundaryError):
                assert_within(root, link / "precious.json")
            self.assertTrue((target / "precious.json").is_file())


class AtomicWriteTests(unittest.TestCase):
    r"""The defect that destroyed a canonical content-addressed payload.

    ``features/tamu_official_historical_coverage_inventory/sha256/d39d35ff.../
    inventory.json`` was truncated to zero bytes while its identity directory
    kept its original creation time. A truncating rewrite is how that happens.
    """

    def test_write_is_visible_only_when_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload.json"
            atomic_write_json(target, {"b": 2, "a": 1})
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")), {"a": 1, "b": 2}
            )

    def test_failed_write_leaves_the_previous_bytes_intact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload.json"
            atomic_write_bytes(target, b'{"original": true}')
            with self.assertRaises(WorkspaceError):
                # A write that cannot fit must not open the destination at all.
                require_free_bytes(target.parent, 1 << 60)
                atomic_write_bytes(target, b"x" * 16, reserve=1 << 60)
            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")), {"original": True}
            )

    def test_no_temporary_files_are_left_behind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "payload.json"
            atomic_write_json(target, {"a": 1})
            leftovers = [p.name for p in Path(tmp).iterdir() if p.name.startswith(".tmp-")]
            self.assertEqual(leftovers, [])

    def test_capacity_guard_refuses_an_impossible_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(WorkspaceError):
                atomic_write_bytes(Path(tmp) / "big.bin", b"x", reserve=1 << 60)


class SeedContractTests(unittest.TestCase):
    r"""``SEED = Path(r"C:\bas35q")`` replaced by a declared, verified input."""

    CONTRACT = "CYCLE35-FAMILY-B-COMPOSED-SEED-V1"

    def _seed(
        self,
        tmp: str,
        *,
        contract_id: str | None = None,
        schema: str = "BAS_SEED_CONTRACT_V1",
        entry_digests: dict | None = None,
        pin: bool = True,
    ):
        """Build a fixture seed and its contract.

        MF37-03 correction. This helper used to write a contract with *no*
        ``entry_digests`` and the positive tests below passed against it,
        which is precisely the hole the manager found: a contract that names
        a directory without identifying its bytes was accepted. The fixture
        was wrong, not the new refusal, so the fixture now pins the real
        digests and an unpinned contract is an explicit negative control
        (``pin=False``) rather than the default shape.
        """

        seed = Path(tmp) / "seed"
        (seed / "repo").mkdir(parents=True)
        (seed / "repo" / "declaration.json").write_text('{"n": 1}\n', encoding="utf-8")
        (seed / "data").mkdir(parents=True)
        (seed / "data" / "payload.json").write_text('{"n": 2}\n', encoding="utf-8")
        document = {"schema": schema, "contract_id": contract_id or self.CONTRACT}
        if pin:
            document["entry_digests"] = (
                entry_digests
                if entry_digests is not None
                else seed_entry_digests(seed, ("repo", "data"))
            )
        (seed / "SEED_CONTRACT.json").write_text(
            json.dumps(document), encoding="utf-8"
        )
        return seed

    def test_no_seed_configured_fails_closed_with_guidance(self) -> None:
        with self.assertRaises(SeedContractError) as caught:
            resolve_seed(self.CONTRACT, env={})
        self.assertIn("--seed", str(caught.exception))
        self.assertIn("BAS_FAMILY_B_SEED", str(caught.exception))

    def test_missing_seed_directory_is_reported(self) -> None:
        with self.assertRaises(SeedContractError):
            resolve_seed(self.CONTRACT, explicit=r"C:\definitely\not\here")

    def test_unlabelled_directory_is_not_accepted_as_a_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / "bare"
            bare.mkdir()
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=bare)
            self.assertIn("SEED_CONTRACT.json", str(caught.exception))

    def test_wrong_contract_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp, contract_id="SOME-OTHER-CONTRACT-V9")
            with self.assertRaises(SeedContractError):
                resolve_seed(self.CONTRACT, explicit=seed)

    def test_wrong_schema_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp, schema="SOMETHING_ELSE_V1")
            with self.assertRaises(SeedContractError):
                resolve_seed(self.CONTRACT, explicit=seed)

    def test_missing_required_entries_are_named(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(
                    self.CONTRACT, explicit=seed, required_entries=("repo", "absent")
                )
            self.assertIn("absent", str(caught.exception))

    def test_valid_seed_resolves_and_records_its_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            resolved, contract = resolve_seed(
                self.CONTRACT, explicit=seed, required_entries=("repo", "data")
            )
            self.assertEqual(resolved, seed)
            self.assertEqual(contract["contract_id"], self.CONTRACT)
            self.assertEqual(contract["resolved_from"], "explicit")

    def test_environment_supplies_the_seed_and_is_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            _, contract = resolve_seed(
                self.CONTRACT, env={"BAS_FAMILY_B_SEED": str(seed)}
            )
            self.assertEqual(contract["resolved_from"], "env:BAS_FAMILY_B_SEED")

    def test_seed_is_not_modified_by_resolution(self) -> None:
        """Source immutability: resolving must never write into the seed."""
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            before = {
                p.relative_to(seed).as_posix(): p.stat().st_mtime_ns
                for p in sorted(seed.rglob("*"))
                if p.is_file()
            }
            resolve_seed(self.CONTRACT, explicit=seed, required_entries=("repo",))
            after = {
                p.relative_to(seed).as_posix(): p.stat().st_mtime_ns
                for p in sorted(seed.rglob("*"))
                if p.is_file()
            }
            self.assertEqual(before, after)


class SeedDigestGateTests(unittest.TestCase):
    """MF37-03: a contract that does not identify the bytes is not a contract.

    The real Cycle 35 contract pins digests, so the supplied path was safe
    while the *general* consumer was not: any well-formed contract carrying
    the right id and schema and no ``entry_digests`` was accepted. Each case
    below is one of the manager's named rejection classes.
    """

    CONTRACT = "CYCLE35-FAMILY-B-COMPOSED-SEED-V1"

    def _seed(self, tmp: str, **kwargs):
        return SeedContractTests._seed(self, tmp, **kwargs)  # type: ignore[arg-type]

    def test_a_contract_with_no_entry_digests_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp, pin=False)
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=seed, required_entries=("repo",))
            self.assertIn("entry_digests", str(caught.exception))

    def test_an_empty_entry_digests_object_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp, entry_digests={})
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=seed, required_entries=("repo",))
            self.assertIn("empty", str(caught.exception))

    def test_a_partial_contract_that_omits_a_required_entry_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            digests = seed_entry_digests(seed, ("repo", "data"))
            seed_partial = self._seed(tmp + "_p", entry_digests={"repo": digests["repo"]})
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(
                    self.CONTRACT, explicit=seed_partial, required_entries=("repo", "data")
                )
            self.assertIn("unpinned", str(caught.exception))

    def test_a_malformed_digest_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp, entry_digests={"repo": "not-a-digest", "data": "0" * 64})
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=seed, required_entries=("repo",))
            self.assertIn("malformed", str(caught.exception))

    def test_a_pinned_path_that_escapes_the_seed_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            digests = dict(seed_entry_digests(seed, ("repo", "data")))
            digests["../outside"] = "0" * 64
            escaping = self._seed(tmp + "_e", entry_digests=digests)
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=escaping, required_entries=("repo",))
            self.assertIn("traverse outside", str(caught.exception))

    def test_a_changed_entry_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            (seed / "repo" / "declaration.json").write_text('{"n": 99}\n', encoding="utf-8")
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=seed, required_entries=("repo",))
            self.assertIn("differ from the declared digests", str(caught.exception))

    def test_a_pinned_entry_absent_from_the_seed_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            digests = dict(seed_entry_digests(seed, ("repo", "data")))
            digests["gone"] = "e" * 64
            broken = self._seed(tmp + "_g", entry_digests=digests)
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(self.CONTRACT, explicit=broken, required_entries=("repo",))
            self.assertIn("missing entries", str(caught.exception))

    def test_disabling_verification_without_a_reason_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            with self.assertRaises(SeedContractError) as caught:
                resolve_seed(
                    self.CONTRACT,
                    explicit=seed,
                    required_entries=("repo",),
                    verify_digests=False,
                )
            self.assertIn("unverified_reason", str(caught.exception))

    def test_disabling_verification_with_a_reason_records_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            _, contract = resolve_seed(
                self.CONTRACT,
                explicit=seed,
                required_entries=("repo",),
                verify_digests=False,
                unverified_reason="operator decision recorded in the receipt",
            )
            self.assertFalse(contract["digests_verified"])
            self.assertIn("operator decision", contract["digests_unverified_reason"])

    def test_a_complete_correct_contract_still_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            resolved, contract = resolve_seed(
                self.CONTRACT, explicit=seed, required_entries=("repo", "data")
            )
            self.assertEqual(resolved, seed)
            self.assertTrue(contract["digests_verified"])
            self.assertEqual(
                contract["entry_digests"], contract["observed_entry_digests"]
            )

    def test_top_level_entries_the_contract_does_not_pin_are_allowed(self) -> None:
        """The real seed carries leftover tamper fixtures beside repo/data.

        Requiring a digest for every directory that happens to be present
        would break the pinned positive case, so the rule is that every
        *required* entry must be pinned, not that nothing else may exist.
        """

        with tempfile.TemporaryDirectory() as tmp:
            seed = self._seed(tmp)
            (seed / "t_leftover").mkdir()
            (seed / "t_leftover" / "x.json").write_text("{}\n", encoding="utf-8")
            _, contract = resolve_seed(
                self.CONTRACT, explicit=seed, required_entries=("repo", "data")
            )
            self.assertTrue(contract["digests_verified"])


class WorkspaceEscapeTests(unittest.TestCase):
    """MF37-02: a caller string must never decide where a directory is made."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        (self.base / "declared").mkdir()
        self.layout = resolve_layout(
            overrides={"validation": self.base / "declared"}, env={}
        )
        self.addCleanup(self._tmp.cleanup)

    def _nothing_escaped(self) -> None:
        outside = sorted(
            p.name for p in self.base.iterdir() if p.name != "declared"
        )
        self.assertEqual(outside, [], f"allocation created {outside} outside the root")

    def test_a_normal_name_allocates_inside_the_declared_root(self) -> None:
        workspace = allocate_run_workspace(
            "tool", layout=self.layout, run_id="normal", worst_case_relative=32
        )
        self.assertEqual(workspace.root.parent.parent, self.base / "declared")
        self.assertTrue(workspace.marker_path.is_file())

    def test_a_parent_traversal_tool_name_creates_nothing(self) -> None:
        with self.assertRaises(UnsafeNameComponent):
            allocate_run_workspace(
                "..", layout=self.layout, run_id="escaped", worst_case_relative=32
            )
        self._nothing_escaped()

    def test_an_absolute_run_id_creates_nothing(self) -> None:
        with self.assertRaises(UnsafeNameComponent):
            allocate_run_workspace(
                "tool",
                layout=self.layout,
                run_id=str(self.base / "absolute_escape"),
                worst_case_relative=32,
            )
        self._nothing_escaped()

    def test_a_drive_qualified_tool_name_creates_nothing(self) -> None:
        with self.assertRaises(UnsafeNameComponent):
            allocate_run_workspace(
                "C:", layout=self.layout, run_id="drive", worst_case_relative=32
            )
        self._nothing_escaped()

    def test_a_unc_run_id_creates_nothing(self) -> None:
        with self.assertRaises(UnsafeNameComponent):
            allocate_run_workspace(
                "tool",
                layout=self.layout,
                run_id=r"\\server\share\escaped",
                worst_case_relative=32,
            )
        self._nothing_escaped()

    def test_a_separator_inside_a_component_creates_nothing(self) -> None:
        for candidate in ("nested/child", r"nested\child"):
            with self.subTest(run_id=candidate):
                with self.assertRaises(UnsafeNameComponent):
                    allocate_run_workspace(
                        "tool",
                        layout=self.layout,
                        run_id=candidate,
                        worst_case_relative=32,
                    )
        self._nothing_escaped()

    def test_a_reserved_device_name_creates_nothing(self) -> None:
        with self.assertRaises(UnsafeNameComponent):
            allocate_run_workspace(
                "tool", layout=self.layout, run_id="NUL", worst_case_relative=32
            )
        self._nothing_escaped()

    def test_a_trailing_dot_name_creates_nothing(self) -> None:
        with self.assertRaises(UnsafeNameComponent):
            allocate_run_workspace(
                "tool", layout=self.layout, run_id="run.", worst_case_relative=32
            )
        self._nothing_escaped()

    def test_an_allocation_through_a_reparse_ancestor_is_refused(self) -> None:
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        link = self.base / "declared" / "tool"
        try:
            make_directory_reparse_point(link, elsewhere)
        except OSError as error:
            self.skipTest(f"no reparse-point mechanism available: {error}")
        with self.assertRaises(WorkspaceBoundaryError):
            allocate_run_workspace(
                "tool", layout=self.layout, run_id="through-link", worst_case_relative=32
            )
        self.assertEqual(sorted(p.name for p in elsewhere.iterdir()), [])


class ExplicitWorkspaceTests(unittest.TestCase):
    """MF37-01: an operator-named workspace is leased, never appropriated."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        (self.base / "declared").mkdir()
        self.layout = resolve_layout(
            overrides={"validation": self.base / "declared"}, env={}
        )
        self.addCleanup(self._tmp.cleanup)

    def test_a_fresh_explicit_workspace_is_created_and_marked(self) -> None:
        target = self.base / "fresh"
        workspace = prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        self.assertTrue(workspace.root.is_dir())
        self.assertTrue(workspace.marker_path.is_file())

    def test_an_existing_directory_with_foreign_content_is_refused(self) -> None:
        target = self.base / "occupied"
        (target / "repo").mkdir(parents=True)
        sentinel = target / "repo" / "SENTINEL.txt"
        sentinel.write_text("do not delete me\n", encoding="utf-8")
        with self.assertRaises(UnownedWorkspace) as caught:
            prepare_explicit_workspace(
                target, tool="probe", run_id="r1", layout=self.layout,
                worst_case_relative=32,
            )
        self.assertIn("carries no", str(caught.exception))
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "do not delete me\n")

    def test_a_workspace_owned_by_another_run_is_refused(self) -> None:
        target = self.base / "leased"
        first = prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        (first.root / "work.json").write_text("{}\n", encoding="utf-8")
        with self.assertRaises(UnownedWorkspace) as caught:
            prepare_explicit_workspace(
                target, tool="probe", run_id="r2", layout=self.layout,
                worst_case_relative=32,
            )
        self.assertIn("owned by", str(caught.exception))

    def test_the_same_run_may_reuse_its_own_workspace(self) -> None:
        target = self.base / "reused"
        prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        (target / "work.json").write_text("{}\n", encoding="utf-8")
        again = prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        self.assertEqual(again.root, target)

    def test_an_empty_existing_directory_may_be_leased(self) -> None:
        target = self.base / "empty"
        target.mkdir()
        workspace = prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        self.assertTrue(workspace.marker_path.is_file())

    def test_a_relative_workspace_is_refused(self) -> None:
        with self.assertRaises(WorkspaceBoundaryError):
            prepare_explicit_workspace(
                Path("relative/workspace"), tool="probe", run_id="r1",
                layout=self.layout, worst_case_relative=32,
            )

    def test_a_reparse_point_workspace_is_refused(self) -> None:
        elsewhere = self.base / "real"
        elsewhere.mkdir()
        (elsewhere / "keep.txt").write_text("keep\n", encoding="utf-8")
        link = self.base / "link"
        try:
            make_directory_reparse_point(link, elsewhere)
        except OSError as error:
            self.skipTest(f"no reparse-point mechanism available: {error}")
        with self.assertRaises(WorkspaceBoundaryError):
            prepare_explicit_workspace(
                link, tool="probe", run_id="r1", layout=self.layout,
                worst_case_relative=32,
            )
        self.assertEqual((elsewhere / "keep.txt").read_text(encoding="utf-8"), "keep\n")

    def test_clearing_a_subtree_requires_owning_the_workspace(self) -> None:
        target = self.base / "clearable"
        workspace = prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        (target / "repo").mkdir()
        (target / "repo" / "x.json").write_text("{}\n", encoding="utf-8")
        self.assertEqual(clear_owned_subtree(workspace, "repo")["state"], "REMOVED")

        foreign = self.base / "foreign"
        (foreign / "repo").mkdir(parents=True)
        (foreign / "repo" / "x.json").write_text("{}\n", encoding="utf-8")
        stolen = type(workspace)(
            root=foreign,
            tool="probe",
            run_id="r1",
            category="validation",
            layout=self.layout,
        )
        with self.assertRaises(UnownedWorkspace):
            clear_owned_subtree(stolen, "repo")
        self.assertTrue((foreign / "repo" / "x.json").is_file())

    def test_clearing_refuses_a_traversal_relative_name(self) -> None:
        target = self.base / "guarded"
        workspace = prepare_explicit_workspace(
            target, tool="probe", run_id="r1", layout=self.layout,
            worst_case_relative=32,
        )
        with self.assertRaises(UnsafeNameComponent):
            clear_owned_subtree(workspace, "..")


class FamilyBToolUsesTheSafeRoute(unittest.TestCase):
    """The repair has to reach the tool that carried the defect."""

    SOURCE = (
        Path(__file__).resolve().parents[1]
        / "tools"
        / "cycle35"
        / "r35_31_family_b_successor_qualification.py"
    )

    def test_the_explicit_workspace_route_is_leased(self) -> None:
        text = self.SOURCE.read_text(encoding="utf-8")
        self.assertIn("prepare_explicit_workspace(", text)
        self.assertNotIn("workspace.mkdir(parents=True, exist_ok=True)", text)

    def test_the_isolated_subtrees_are_cleared_through_the_ownership_gate(self) -> None:
        text = self.SOURCE.read_text(encoding="utf-8")
        self.assertIn('clear_owned_subtree(workspace, "repo")', text)
        self.assertIn('clear_owned_subtree(workspace, "data")', text)
        self.assertNotIn("shutil.rmtree(root)", text)


class RelocationIndependenceTests(unittest.TestCase):
    """The same work in two different roots must produce the same identities."""

    def test_identical_content_yields_identical_digests_across_roots(self) -> None:
        import hashlib

        digests = []
        for name in ("root_one", "a_much_longer_root_name_two"):
            with tempfile.TemporaryDirectory() as tmp:
                layout = resolve_layout(
                    overrides={"validation": Path(tmp) / name}, env={}
                )
                (Path(tmp) / name).mkdir(parents=True)
                # This probe writes one shallow file, not the content-addressed
                # lake, so it declares its own worst case rather than borrowing
                # the Family B figure.
                workspace = allocate_run_workspace(
                    "probe", layout=layout, worst_case_relative=32
                )
                payload = workspace.root / "result.json"
                atomic_write_json(payload, {"seasons": [1998, 1999], "rows": 2})
                digests.append(hashlib.sha256(payload.read_bytes()).hexdigest())
                workspace.release()
        self.assertEqual(digests[0], digests[1])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
