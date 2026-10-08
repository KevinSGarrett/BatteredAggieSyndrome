"""BAT-716 service-aware archive capture (Cycle #44 TP44-A01): the explicit --capture-policy mode stops the whole
acquisition at the first HTTP 429, resumes only on a later explicit eligible invocation and keeps one bound journal,
request ceiling and owner. Every case runs the actual CLI (``main``) through the real urllib transport with a fake
opener at the ``urllib.request.build_opener`` boundary and a controlled clock. Synthetic worlds and fixture policies in
owned temporary roots only; they never authorize a real request and are not acquisition evidence.

JournalTailTests and BodyLimitTests (C44-CONT-01, findings MF44A01-01 and MF44A01-02): a line after the anchored head
is authority only when the anchor announced exactly that line, every decision-bearing line must be its own derivation
from the recorded observations, and an observed 429 stays a 429 when its bounded body is oversized or unreadable."""
from __future__ import annotations

import contextlib
import datetime as dt
import email.message
import hashlib
import http.client
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import national_archived_publication_expansion_fixture as xfx  # noqa: E402
import national_archived_publication_fixture as apfx  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "configs" / "national_archived_publication_capture_policy.json"
EXPANSION_CONTRACT_PATH = ROOT / "configs" / "national_archived_publication_2019_expansion_contract.json"
BUSY_BODY = b"<html><body><h1>429 Too Many Requests</h1>fixture</body></html>\n"
STATE: dict[str, Any] = {}
FMT = "%Y-%m-%dT%H:%M:%S.%fZ"


class SimulatedCrash(BaseException):
    """A process interruption: not an Exception, so nothing in the producer can catch or record it."""


def setUpModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"] = tempfile.TemporaryDirectory()
    STATE["base"] = Path(STATE["tmp"].name)
    STATE["world"] = xfx.build_expansion_world(STATE["base"] / "w")
    STATE["b"] = xfx.builder()
    STATE["n"] = 0


def tearDownModule() -> None:  # noqa: N802 - unittest hook
    STATE["tmp"].cleanup()


def utc(text: str) -> dt.datetime:
    return dt.datetime.strptime(text, FMT).replace(tzinfo=dt.timezone.utc)


class Reply:
    """One scripted HTTP answer: status, header pairs and body; ``crash`` interrupts the process instead;
    ``fail_after``/``fail_with`` lose the connection after that many body bytes (the status and headers were already
    received); ``network_error`` fails before any status."""

    def __init__(self, status: int = 429, headers: list[list[str]] | None = None, body: bytes = BUSY_BODY,
                 crash: bool = False, fail_after: int | None = None, fail_with: BaseException | None = None,
                 network_error: bool = False) -> None:
        self.status, self.headers, self.body, self.crash = status, headers or [], body, crash
        self.fail_after, self.fail_with, self.network_error = fail_after, fail_with, network_error


class FailingBody(io.BytesIO):
    """A response body whose connection is lost at byte ``after`` (``after`` None: never): like a buffered socket read,
    a read that would cross that point raises ``error`` and returns nothing of its own partial data (an
    ``http.client.IncompleteRead`` may carry what it got in ``partial``)."""

    def __init__(self, body: bytes, after: int | None = None, error: BaseException | None = None) -> None:
        super().__init__(body)
        self.after, self.error = after, error

    def read(self, size: int | None = -1) -> bytes:
        if self.after is not None and (size is None or size < 0 or self.tell() + size > self.after):
            raise self.error or ConnectionResetError("fixture: connection lost mid-body")
        return super().read(size)


class FakeResponse(FailingBody):
    def __init__(self, status: int, reason: str, headers: list[list[str]], body: bytes, after: int | None = None,
                 error: BaseException | None = None) -> None:
        super().__init__(body, after, error)
        self.status, self.reason = status, reason
        message = email.message.Message()
        for key, value in headers:
            message[key] = value
        self.headers = message

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: Any) -> bool:
        return False


class Harness:
    """One owned acquisition root with its own fixture policy, a programmable archive at the urllib opener boundary
    and a controlled clock (the expansion fixture's clock model: sleep and perf_counter advance it, now does not)."""

    def __init__(self, contract_patch: Any = None, v12: bool = False) -> None:
        STATE["n"] += 1
        self.b, self.world = STATE["b"], STATE["world"]
        self.dir = STATE["base"] / f"h{STATE['n']:02d}"
        self.v12 = v12
        self.out = self.dir / "canonical" / "ape"
        self.manifests = self.dir / "manifests" / "ape"
        self.contract_path = Path(self.world["contract"] if v12 else self.world["x_contract"])
        if contract_patch is not None:
            doc = json.loads(self.contract_path.read_text(encoding="utf-8"))
            contract_patch(doc)
            self.contract_path = apfx.write(self.dir / "contract.json",
                                            (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        self.policy_path = self.dir / "policy.json"
        self.binding = self.expected_binding()
        self.write_policy()
        self.script: list[tuple[str, list[Reply]]] = []
        self.calls: list[str] = []
        self.t = 0.0
        self.base_clock = dt.datetime(2026, 10, 7, 15, 0, tzinfo=dt.timezone.utc)
        self.hold: threading.Event | None = None
        self.entered: threading.Event | None = None

    # ---- identities -------------------------------------------------------------------------------------------
    def expected_binding(self) -> dict[str, Any]:
        b = self.b
        if self.v12:
            contract, csha = b.load_contract(self.contract_path)
            pid, keys = b.policy_id(contract), [k["contest_key"] for k in contract["scope"]["keys"]]
        else:
            contract, csha = b.load_expansion_contract(self.contract_path)
            view = b.acquisition_view(contract)
            pid, keys = b.policy_id(view), [k["contest_key"] for k in view["scope"]["keys"]]
        return {"label": "fixture acquisition", "contract_id": contract["contract_id"], "contract_sha256": csha,
                "acquisition_policy_id": pid, "ordered_keys": keys,
                "total_requests": contract["acquisition"]["limits"]["total_requests"], "output_root": str(self.out)}

    def write_policy(self, binding: dict[str, Any] | None = None, rules: dict[str, Any] | None = None,
                     **top: Any) -> None:
        committed = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        doc = {**committed, "rules": rules if rules is not None else committed["rules"],
               "acquisitions": [binding if binding is not None else self.binding], **top}
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        self.policy_path.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")

    @property
    def pid(self) -> str:
        return self.binding["acquisition_policy_id"]

    @property
    def jdir(self) -> Path:
        return self.out / "acquisition" / "journal" / self.pid

    def lines(self) -> list[dict[str, Any]]:
        return [json.loads(x) for x in (self.jdir / "journal.jsonl").read_text(encoding="utf-8").splitlines()]

    def types(self) -> list[str]:
        return [x["type"] for x in self.lines()]

    # ---- clock ------------------------------------------------------------------------------------------------
    def now(self) -> str:
        return (self.base_clock + dt.timedelta(seconds=self.t)).strftime(FMT)

    def set_now(self, text: str) -> None:
        self.t = (utc(text) - self.base_clock).total_seconds()

    def sleep(self, seconds: float) -> None:
        self.t += seconds

    def perf(self) -> float:
        self.t += 0.25
        return self.t

    # ---- urllib opener boundary -------------------------------------------------------------------------------
    def reply(self, fragment: str, *replies: Reply) -> None:
        self.script.append((fragment, list(replies)))

    def answer(self, url: str) -> Any:
        self.calls.append(url)
        if self.entered is not None:
            self.entered.set()
        if self.hold is not None:
            self.hold.wait(30)
        for fragment, replies in self.script:
            if fragment in url and replies:
                return replies.pop(0)
        response = self.world["archive"](url, {}, 60.0)
        return Reply(response.status, response.headers, response.body)

    def opener(self, *handlers: Any) -> Any:
        harness = self

        class Opener:
            def open(self, request: Any, timeout: float) -> Any:
                found = harness.answer(request.full_url)
                if found.crash:
                    raise SimulatedCrash(request.full_url)
                if getattr(found, "network_error", False):
                    raise urllib.error.URLError("fixture: connection refused before any status")
                after, error = getattr(found, "fail_after", None), getattr(found, "fail_with", None)
                if found.status < 300:
                    return FakeResponse(found.status, "OK", found.headers, found.body, after, error)
                message = email.message.Message()
                for key, value in found.headers:
                    message[key] = value
                raise urllib.error.HTTPError(request.full_url, found.status, "fixture", message,
                                             FailingBody(found.body, after, error))
        return Opener()

    # ---- the actual CLI ---------------------------------------------------------------------------------------
    def argv(self, policy: bool = True, ack: int | None = None, stage: str = "capture") -> list[str]:
        w = self.world
        args = ["--contract", str(self.contract_path), "--source-database", str(w["st_db"]), "--source-bindings",
                str(w["bindings"] if self.v12 else w["x_bindings"]), "--tranche", str(w["tranche"]),
                "--output-root", str(self.out), "--manifest-root", str(self.manifests), "--stage", stage,
                "--no-network-audit"]
        if not self.v12:
            args += ["--cohort", str(w["cohort"]), "--retained-root", str(w["out"])]
        if policy:
            args += ["--capture-policy", str(self.policy_path)]
        if ack is not None:
            args += ["--acknowledge-unknown-intent", str(ack)]
        return args

    def patches(self) -> contextlib.ExitStack:
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(self.b.urllib.request, "build_opener", self.opener))
        stack.enter_context(mock.patch.object(self.b, "utc_now", self.now))
        stack.enter_context(mock.patch.object(self.b.time, "sleep", self.sleep))
        stack.enter_context(mock.patch.object(self.b.time, "perf_counter", self.perf))
        return stack

    def run(self, policy: bool = True, ack: int | None = None, stage: str = "capture",
            extra_patches: list[Any] | None = None) -> tuple[int, dict[str, Any] | None, str]:
        out, err = io.StringIO(), io.StringIO()
        with self.patches() as stack, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            for patch in extra_patches or []:
                stack.enter_context(patch)
            try:
                code = self.b.main(self.argv(policy, ack, stage))
            except SystemExit as exc:
                code = exc.code
        text = out.getvalue()
        return code, (json.loads(text) if text.strip() else None), err.getvalue()

    def refusal(self, stderr: str) -> str | None:
        return apfx.refusal(stderr)

    def snapshot(self) -> dict[str, bytes]:
        return {str(p.relative_to(self.out)): p.read_bytes() for p in sorted(self.out.rglob("*")) if p.is_file()}


def first_key(h: Harness) -> str:
    return h.binding["ordered_keys"][0]


def meta_fragment(h: Harness, key: str) -> str:
    """The URL fragment that matches every availability request of one key (the contract scope's candidate URL)."""
    specs = {k["contest_key"]: k for k in json.loads(h.contract_path.read_text(encoding="utf-8"))["scope"]["keys"]}
    return "wayback/available?" + urllib.parse.urlencode({"url": specs[key]["candidate_url"]})


class PolicyAndBindingTests(unittest.TestCase):
    def test_committed_policy_binds_the_issued_acquisition_and_authorizes_nothing(self) -> None:
        b = STATE["b"]
        loaded = b.load_capture_policy(POLICY_PATH)
        policy = loaded["policy"]
        self.assertIs(policy["authorizes_requests"], False)
        self.assertEqual(policy["rules"]["retry_after_fallback_seconds"], 900)
        self.assertEqual(policy["rules"]["service_pause_statuses"], [429])
        (binding,) = policy["acquisitions"]
        contract, csha = b.load_expansion_contract(EXPANSION_CONTRACT_PATH)
        view = b.acquisition_view(contract)
        self.assertEqual((binding["contract_id"], binding["contract_sha256"]), (contract["contract_id"], csha))
        self.assertEqual(binding["acquisition_policy_id"], b.policy_id(view))
        self.assertEqual(binding["ordered_keys"], contract["scope"]["cohort_keys"])
        self.assertEqual(len(binding["ordered_keys"]), 70)
        self.assertEqual(binding["total_requests"], contract["acquisition"]["limits"]["total_requests"])
        self.assertTrue(binding["output_root"].endswith("national_archived_publication_2019_expansion"))

    def test_unbound_roots_contracts_keys_limits_and_policies_refuse_before_any_write(self) -> None:
        h = Harness()
        cases = {
            "CAPTURE_ROOT_NOT_BOUND": dict(h.binding, output_root=str(h.dir / "fresh" / "canonical" / "ape")),
            "CAPTURE_CONTRACT_MISMATCH": dict(h.binding, contract_sha256="0" * 64),
            "CAPTURE_ACQUISITION_POLICY_MISMATCH": dict(h.binding, acquisition_policy_id="0" * 64),
            "CAPTURE_KEYSET_DUPLICATE": dict(h.binding, ordered_keys=h.binding["ordered_keys"] +
                                             h.binding["ordered_keys"][:1]),
            "CAPTURE_LIMIT_MISMATCH": dict(h.binding, total_requests=h.binding["total_requests"] + 1)}
        keys = h.binding["ordered_keys"]
        for code, binding in list(cases.items()) + [
                ("CAPTURE_KEYSET_MISMATCH", dict(h.binding, ordered_keys=keys[:-1])),
                ("CAPTURE_KEYSET_MISMATCH", dict(h.binding, ordered_keys=keys + ["ncaa:424242"])),
                ("CAPTURE_KEYSET_MISMATCH", dict(h.binding, ordered_keys=list(reversed(keys))))]:
            h.write_policy(binding)
            got = h.run()
            self.assertEqual((got[0], h.refusal(got[2])), (2, code), got[2])
            self.assertFalse(h.out.exists(), f"{code}: nothing may be written to an unbound or mismatched root")
        for code, kwargs in (("CAPTURE_POLICY_INVALID", {"authorizes_requests": True}),
                             ("CAPTURE_POLICY_INVALID", {"rules": dict(json.loads(POLICY_PATH.read_text(
                                 encoding="utf-8"))["rules"], service_pause_statuses=[429, 503])}),
                             ("CAPTURE_POLICY_INVALID", {"rules": dict(json.loads(POLICY_PATH.read_text(
                                 encoding="utf-8"))["rules"], retry_after_fallback_seconds=0)})):
            h.write_policy(**kwargs)
            got = h.run()
            self.assertEqual((got[0], h.refusal(got[2])), (2, code), got[2])
        h.write_policy()
        self.assertEqual(h.refusal(h.run(stage="materialize")[2]), "ARGUMENT_INVALID")
        self.assertEqual(h.refusal(h.run(policy=False, ack=1)[2]), "ARGUMENT_INVALID")
        self.assertEqual(h.calls, [])
        self.assertFalse(h.out.exists())


class ServicePauseTests(unittest.TestCase):
    def test_default_invocation_keeps_the_frozen_per_key_retry(self) -> None:
        # the default capture binds its real clock and spacing at definition: a 4-request ceiling keeps this short
        h = Harness(contract_patch=lambda c: c["acquisition"]["limits"].update(total_requests=4))
        k1, k2 = h.binding["ordered_keys"][:2]
        h.reply(meta_fragment(h, k1), Reply(), Reply())
        h.reply(meta_fragment(h, k2), Reply(), Reply())
        code, result, err = h.run(policy=False)
        self.assertEqual(code, 0, err)
        capture = result["capture"]
        self.assertEqual(capture["state"], "FINALIZED")
        doc = json.loads(Path(capture["path"]).read_text(encoding="utf-8"))
        self.assertEqual([(r["contest_key"], r["purpose"], r["http_status"]) for r in doc["requests"]],
                         [(k1, "PROBE_1", 429), (k1, "RETRY", 429), (k2, "PROBE_1", 429), (k2, "RETRY", 429)],
                         "the default mode retries and moves on to the next key after HTTP 429")
        self.assertEqual((capture["outcomes"][k1], capture["outcomes"][k2]),
                         ("METADATA_REQUEST_FAILED", "METADATA_REQUEST_FAILED"))
        self.assertEqual(json.loads((h.jdir / "journal.jsonl").read_text(encoding="utf-8").splitlines()[0])["header"][
            "schema"], "BAS-NATIONAL-ARCHIVED-PUBLICATION-JOURNAL-1")

    def test_metadata_429_pauses_the_whole_acquisition_and_keeps_the_response(self) -> None:
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[0]), Reply(headers=[["Retry-After", "120"]]))
        code, result, err = h.run()
        self.assertEqual(code, 4, err)
        cap = result["capture"]
        self.assertEqual(result["state"], "CAPTURE_PAUSED_SERVICE_429")
        self.assertEqual((cap["new_requests"], cap["requests_used"], len(h.calls)), (1, 1, 1))
        self.assertEqual(cap["keys"], {"completed": {}, "attempted_failed_pending": keys[:1],
                                       "pending_unattempted": keys[1:]})
        pause = cap["pause"]
        self.assertEqual((pause["seq"], pause["kind"], pause["purpose"], pause["http_status"]),
                         (1, "METADATA", "PROBE_1", 429))
        self.assertEqual((pause["retry_after_raw"], pause["retry_after_rule"], pause["delay_seconds"]),
                         (["120"], "DELTA_SECONDS", "120.000000"))
        self.assertEqual(utc(cap["eligible_utc"]) - utc(pause["response_clock_utc"]), dt.timedelta(seconds=120))
        self.assertEqual([t for t in h.types() if t not in ("OWNER_START", "OWNER_END")],
                         ["HEADER", "INTENT", "RESULT", "PAUSE"])
        record = h.lines()[3]["request"]
        self.assertEqual((record["http_status"], record["body_bytes"]), (429, len(BUSY_BODY)))
        self.assertEqual((h.out / "raw" / "sha256" / record["body_sha256"]).read_bytes(), BUSY_BODY)
        self.assertEqual(list((h.out / "acquisition" / "sha256").glob("*/acquisition.json")).__len__(), 1,
                         "only the retained acquisition exists: nothing is finalized or turned into no-capture")

    def test_replay_and_redirect_hop_429_pause_after_exactly_that_request(self) -> None:
        h = Harness()
        k4 = "ncaa:1004"
        h.reply("id_/https://www.espn.com", Reply(headers=[["Retry-After", "30"]]))
        code, result, err = h.run()
        self.assertEqual(code, 4, err)
        cap = result["capture"]
        self.assertEqual(cap["pause"]["kind"], "REPLAY")
        self.assertEqual(cap["pause"]["contest_key"], k4)
        self.assertEqual(cap["keys"]["completed"], {"ncaa:1002": "RETAINED_VERSION_REUSED"})
        self.assertEqual(cap["keys"]["attempted_failed_pending"], [k4])
        self.assertEqual(cap["requests_used"], 3)
        h2 = Harness()
        row = h2.world["cby"][k4]
        game = row["cfbd_game_id"]["value"]
        hop_ts = "20190910030000"
        h2.reply("20190910020000id_/", Reply(302, [["Location", f"https://web.archive.org/web/{hop_ts}id_/"
                                                                f"{apfx.game_url(game)}"]], b""))
        h2.reply(f"{hop_ts}id_/", Reply(headers=[["Retry-After", "45"]]))
        code, result, err = h2.run()
        self.assertEqual(code, 4, err)
        pause = result["capture"]["pause"]
        self.assertEqual((pause["kind"], pause["purpose"], pause["seq"]), ("REPLAY", "REDIRECT_HOP", 4))
        self.assertEqual(len(h2.calls), 4, "no request after the redirect hop's 429")

    def test_retry_after_rules_against_the_response_receipt_clock(self) -> None:
        b = STATE["b"]
        receipt = "2026-10-07T14:30:11.193284Z"

        def pause(*values: str, name: str = "Retry-After") -> dict[str, Any]:
            return b.service_pause({"ended_utc": receipt, "headers": [[name, v] for v in values]}, 900)
        fallback = (utc(receipt) + dt.timedelta(seconds=900)).strftime(FMT)
        table = [
            (("120",), "DELTA_SECONDS", (utc(receipt) + dt.timedelta(seconds=120)).strftime(FMT)),
            ((" 120\t",), "DELTA_SECONDS", (utc(receipt) + dt.timedelta(seconds=120)).strftime(FMT)),
            (("120", "120"), "DELTA_SECONDS", (utc(receipt) + dt.timedelta(seconds=120)).strftime(FMT)),
            (("0",), "DELTA_SECONDS", receipt),
            (("86400",), "DELTA_SECONDS", (utc(receipt) + dt.timedelta(days=1)).strftime(FMT)),
            (("9" * 30,), "DELTA_SECONDS", "9999-12-31T23:59:59.999999Z"),
            (("9" * 5000,), "DELTA_SECONDS", "9999-12-31T23:59:59.999999Z"),
            (("Wed, 07 Oct 2026 15:00:00 GMT",), "HTTP_DATE", "2026-10-07T15:00:00.000000Z"),
            (("Wednesday, 07-Oct-26 15:00:00 GMT",), "HTTP_DATE", "2026-10-07T15:00:00.000000Z"),
            (("Wed Oct  7 15:00:00 2026",), "HTTP_DATE", "2026-10-07T15:00:00.000000Z"),
            (("Wed, 07 Oct 2026 14:00:00 GMT",), "FALLBACK_PAST_DATE", fallback),
            (("Thursday, 07-Oct-77 15:00:00 GMT",), "FALLBACK_PAST_DATE", fallback),
            (("Wed, 07 Oct 2026 15:00:00 EST",), "FALLBACK_MALFORMED", fallback),
            (("Wed, 31 Feb 2026 15:00:00 GMT",), "FALLBACK_MALFORMED", fallback),
            (("soon",), "FALLBACK_MALFORMED", fallback),
            (("1.5",), "FALLBACK_MALFORMED", fallback),
            (("",), "FALLBACK_MALFORMED", fallback),
            (("-5",), "FALLBACK_NEGATIVE", fallback),
            ((), "FALLBACK_MISSING", fallback),
            (("120", "60"), "FALLBACK_CONFLICTING", fallback)]
        for values, rule, eligible in table:
            got = pause(*values)
            self.assertEqual((got["retry_after_rule"], got["eligible_utc"]), (rule, eligible), values)
            self.assertEqual(got["retry_after_raw"], list(values))
        self.assertEqual(pause("300", name="retry-after")["retry_after_rule"], "DELTA_SECONDS")
        self.assertEqual(pause("Wed, 07 Oct 2026 15:00:00 GMT")["delay_seconds"], "1788.806716")

    def test_resume_before_eligibility_defers_with_zero_requests_and_no_writes(self) -> None:
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[0]), Reply(headers=[["Retry-After", "600"]]))
        code, paused, err = h.run()
        self.assertEqual(code, 4, err)
        eligible = paused["capture"]["eligible_utc"]
        before = h.snapshot()
        calls = len(h.calls)
        h.set_now((utc(eligible) - dt.timedelta(microseconds=1)).strftime(FMT))
        code, result, err = h.run()
        self.assertEqual(code, 4, err)
        cap = result["capture"]
        self.assertEqual((result["state"], cap["reason"], cap["new_requests"]),
                         ("CAPTURE_DEFERRED", "SERVICE_PAUSE_NOT_ELIGIBLE", 0))
        self.assertEqual(cap["seconds_until_eligible"], "0.000001")
        self.assertEqual(len(h.calls), calls)
        after = h.snapshot()
        self.assertEqual({k: v for k, v in after.items() if not k.endswith("OWNER.lock")},
                         {k: v for k, v in before.items() if not k.endswith("OWNER.lock")})

    def test_exact_boundary_resumes_under_the_same_ceiling_and_finishes_idempotently(self) -> None:
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[0]), Reply(headers=[["Retry-After", "600"]]))
        code, paused, err = h.run()
        self.assertEqual(code, 4, err)
        eligible = paused["capture"]["eligible_utc"]
        h.set_now(eligible)
        code, result, err = h.run()
        self.assertEqual(code, 0, err)
        cap = result["capture"]
        self.assertEqual(cap["state"], "FINALIZED")
        doc = json.loads(Path(cap["path"]).read_text(encoding="utf-8"))
        self.assertEqual([(r["contest_key"], r["purpose"], r["http_status"]) for r in doc["requests"][:2]],
                         [(keys[0], "PROBE_1", 429), (keys[0], "RETRY", 200)])
        self.assertEqual(doc["totals"]["requests"], 10)
        self.assertEqual(doc["totals"]["limit"], 320)
        self.assertEqual(cap["outcomes"], {"ncaa:1002": "RETAINED_VERSION_REUSED", "ncaa:1004": "CAPTURED",
                                           "ncaa:1005": "NO_ARCHIVE_CAPTURE_REPORTED", "ncaa:1007": "CAPTURED"})
        self.assertGreaterEqual(utc(doc["requests"][1]["started_utc"]), utc(eligible))
        self.assertIn("RESUME", h.types())
        urls = [r["url"] for r in doc["requests"] if r["http_status"] == 200]
        self.assertEqual(len(urls), len(set(urls)), "no successful observation is requested twice")
        before, calls = h.snapshot(), len(h.calls)
        code, again, err = h.run()
        self.assertEqual((code, again["capture"]["state"], again["capture"]["new_requests"]),
                         (0, "ALREADY_FINALIZED", 0), err)
        self.assertEqual((h.snapshot(), len(h.calls)), (before, calls))

    def test_a_second_429_pauses_again_and_an_exhausted_ceiling_finalizes_honestly(self) -> None:
        h = Harness(contract_patch=lambda c: c["acquisition"]["limits"].update(total_requests=2))
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[0]), Reply(headers=[["Retry-After", "60"]]), Reply())
        self.assertEqual(h.run()[0], 4)
        h.t += 3600
        code, result, err = h.run()
        self.assertEqual((code, result["capture"]["state"]), (4, "PAUSED_SERVICE_429"), err)
        cap = result["capture"]
        self.assertEqual((cap["new_requests"], cap["requests_used"], cap["requests_remaining"]), (1, 2, 0))
        self.assertEqual(cap["pause"]["retry_after_rule"], "FALLBACK_MISSING")
        self.assertEqual(len(cap["pauses"]), 2)
        h.t += 3600
        code, result, err = h.run()
        self.assertEqual(code, 0, err)
        cap = result["capture"]
        self.assertEqual((cap["state"], cap["new_requests"], cap["totals"]["requests"]), ("FINALIZED", 0, 2))
        self.assertEqual(cap["outcomes"][keys[0]], "METADATA_REQUEST_FAILED")
        self.assertEqual({cap["outcomes"][k] for k in keys[1:]}, {"NOT_ATTEMPTED_TOTAL_BUDGET_EXHAUSTED"})
        self.assertEqual(len(h.calls), 2)

    def test_genuine_200_no_capture_and_404_are_not_pauses_and_match_the_default_document(self) -> None:
        h = Harness()
        k5 = "ncaa:1005"
        missing = Reply(404, [["Content-Type", "text/html"]], b"<html>not found</html>")
        h.reply(meta_fragment(h, k5), missing, Reply(404, [["Content-Type", "text/html"]], b"<html>not found</html>"))
        code, result, err = h.run()
        self.assertEqual(code, 0, err)
        cap = result["capture"]
        self.assertEqual(cap["outcomes"][k5], "METADATA_REQUEST_FAILED", "HTTP 404 at both probes is a key failure")
        self.assertEqual(cap["outcomes"]["ncaa:1004"], "CAPTURED")
        self.assertEqual(cap["outcomes"]["ncaa:1007"], "CAPTURED")
        self.assertEqual(cap["pauses"], [])
        legacy = Harness()
        legacy.reply(meta_fragment(legacy, k5), *(Reply(404, [["Content-Type", "text/html"]],
                                                        b"<html>not found</html>") for _ in range(2)))
        contract, _ = legacy.b.load_expansion_contract(legacy.contract_path)
        control = legacy.b.verify_control(contract, legacy.world["route"])
        retained = legacy.b.import_retained(contract, legacy.world["out"], legacy.out)
        with legacy.patches():
            default = legacy.b.capture_expansion(contract, legacy.out, control, retained["document"],
                                                 sleep=legacy.sleep, monotonic=legacy.perf, now=legacy.now,
                                                 audit=False)
        self.assertEqual(default["state"], "FINALIZED")
        self.assertEqual(cap["acquisition_identity"], default["acquisition_identity"],
                         "without a pause the service mode writes the default mode's acquisition document")
        self.assertEqual(Path(cap["path"]).read_bytes(), Path(default["path"]).read_bytes())


class RestartAndOwnerTests(unittest.TestCase):
    def test_crash_after_intent_requires_explicit_reconciliation_and_stays_counted(self) -> None:
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[1]), Reply(crash=True))
        with self.assertRaises(SimulatedCrash):
            h.run()
        lines = h.lines()
        self.assertEqual(lines[-1]["type"], "INTENT")
        seq = lines[-1]["seq"]
        before, calls = h.snapshot(), len(h.calls)
        code, result, err = h.run()
        self.assertEqual(code, 5, err)
        cap = result["capture"]
        self.assertEqual((result["state"], cap["new_requests"]), ("CAPTURE_RECONCILIATION_REQUIRED", 0))
        (unknown,) = cap["unknown_intents"]
        self.assertEqual((unknown["seq"], unknown["contest_key"], unknown["anchor_had_advanced"]),
                         (seq, keys[1], True))
        self.assertEqual(len(cap["stopped_owner"]), 1)
        self.assertEqual(cap["requests_used"], seq, "the interrupted request stays counted")
        self.assertEqual((h.snapshot(), len(h.calls)), (before, calls))
        self.assertEqual(h.refusal(h.run(ack=seq + 7)[2]), "CAPTURE_ACKNOWLEDGEMENT_INVALID")
        code, result, err = h.run(ack=seq)
        self.assertEqual(code, 0, err)
        doc = json.loads(Path(result["capture"]["path"]).read_text(encoding="utf-8"))
        interrupted = doc["requests"][seq - 1]
        self.assertEqual((interrupted["outcome"], interrupted["error"]), ("INTERRUPTED_UNKNOWN", "INTENT_WITHOUT_RESULT"))
        self.assertEqual((doc["requests"][seq]["contest_key"], doc["requests"][seq]["purpose"]), (keys[1], "RETRY"))
        acks = [x for x in h.lines() if x["type"] == "ACKNOWLEDGED"]
        self.assertEqual([(a["seq"], a["decision"]) for a in acks], [(seq, "COUNTED_RESULT_UNKNOWN")])
        starts = [x for x in h.lines() if x["type"] == "OWNER_START"]
        ends = [x for x in h.lines() if x["type"] == "OWNER_END"]
        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[1]["previous_owner_unreleased"], [starts[0]["owner"]],
                         "the crashed owner is recorded as stopped without release")
        self.assertEqual([e["owner"] for e in ends], [starts[1]["owner"]])

    def test_crash_before_the_anchor_update_reports_an_undispatched_intent(self) -> None:
        h = Harness()
        real = h.b._write_authority

        def crash_on_intent(journal: Any, *args: Any) -> None:
            if journal.rows[-1].get("type") == "INTENT":
                raise SimulatedCrash("before the anchor")
            real(journal, *args)
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[mock.patch.object(h.b, "_write_authority", crash_on_intent)])
        self.assertEqual(h.calls, [], "the request was never dispatched")
        code, result, err = h.run()
        self.assertEqual(code, 5, err)
        (unknown,) = result["capture"]["unknown_intents"]
        self.assertFalse(unknown["anchor_had_advanced"])
        code, result, err = h.run(ack=unknown["seq"])
        self.assertEqual((code, result["capture"]["state"]), (0, "FINALIZED"), err)

    def test_crash_after_a_429_result_before_its_pause_recovers_the_same_pause(self) -> None:
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[0]), Reply(headers=[["Retry-After", "300"]]))
        real = h.b._service_append

        def crash_on_pause(journal: Any, row: dict[str, Any], *args: Any) -> None:
            if row.get("type") == "PAUSE":
                raise SimulatedCrash("before the pause")
            real(journal, row, *args)
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[mock.patch.object(h.b, "_service_append", crash_on_pause)])
        result_line = h.lines()[-1]
        self.assertEqual((result_line["type"], result_line["request"]["http_status"]), ("RESULT", 429))
        h.t += 10
        code, result, err = h.run()
        self.assertEqual(code, 4, err)
        cap = result["capture"]
        self.assertEqual(result["state"], "CAPTURE_DEFERRED")
        (pause,) = cap["pauses"]
        self.assertTrue(pause["recovered"])
        self.assertEqual(utc(pause["eligible_utc"]), utc(result_line["request"]["ended_utc"]) +
                         dt.timedelta(seconds=300))
        self.assertEqual(len(h.calls), 1)

    def test_crash_after_a_success_result_resumes_without_repeating_it(self) -> None:
        h = Harness()
        real = h.b._service_append
        seen: list[int] = []

        def crash_after_success(journal: Any, row: dict[str, Any], *args: Any) -> None:
            real(journal, row, *args)
            if row.get("type") == "RESULT" and row["request"]["http_status"] == 200:
                seen.append(row["seq"])
                if len(seen) == 2:
                    raise SimulatedCrash("after a result")
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[mock.patch.object(h.b, "_service_append", crash_after_success)])
        done = list(h.calls)
        code, result, err = h.run()
        self.assertEqual(code, 0, err)
        cap = result["capture"]
        self.assertEqual(cap["totals"]["requests"], 9)
        self.assertEqual(h.calls[:len(done)], done)
        self.assertEqual(len(h.calls), 9, "the completed requests are not repeated")
        self.assertEqual(len(cap["stopped_owner"]), 1)

    def test_clock_rollback_cannot_shorten_a_pause(self) -> None:
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[0]), Reply(headers=[["Retry-After", "0"]]))
        real = h.b._service_append

        def crash_on_pause(journal: Any, row: dict[str, Any], *args: Any) -> None:
            if row.get("type") == "PAUSE":
                raise SimulatedCrash("before the pause")
            real(journal, row, *args)
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[mock.patch.object(h.b, "_service_append", crash_on_pause)])
        receipt = h.lines()[-1]["request"]["ended_utc"]
        h.t += 100
        code, result, err = h.run()
        self.assertEqual((code, result["capture"]["state"]), (0, "FINALIZED"), err)
        h2 = Harness()
        h2.reply(meta_fragment(h2, keys[0]), Reply(headers=[["Retry-After", "0"]]))
        with self.assertRaises(SimulatedCrash):
            h2.run(extra_patches=[mock.patch.object(h2.b, "_service_append", crash_on_pause)])
        h2.t += 100
        with mock.patch.object(h2.b, "_service_dispatch", side_effect=SimulatedCrash("stop after the recovery")):
            with self.assertRaises(SimulatedCrash):
                h2.run()
        recovered = [x for x in h2.lines() if x["type"] == "PAUSE"][0]
        self.assertTrue(recovered["recovered"])
        h2.set_now((utc(recovered["recorded_utc"]) - dt.timedelta(seconds=30)).strftime(FMT))
        self.assertGreaterEqual(utc(h2.now()), utc(receipt), "the clock is after the pause's eligible instant")
        code, result, err = h2.run()
        self.assertEqual((code, result["capture"]["reason"], result["capture"]["new_requests"]),
                         (4, "CLOCK_BEHIND_JOURNAL", 0), err)
        self.assertTrue(result["capture"]["clock_behind_journal"])
        h2.set_now((utc(receipt) - dt.timedelta(hours=1)).strftime(FMT))
        code, result, err = h2.run()
        self.assertEqual((code, result["capture"]["reason"]), (4, "SERVICE_PAUSE_NOT_ELIGIBLE"), err)

    def test_changed_policy_key_set_raw_journal_prefix_and_counter_refuse_for_their_cause(self) -> None:
        def paused() -> Harness:
            h = Harness()
            h.reply(meta_fragment(h, h.binding["ordered_keys"][0]), Reply(headers=[["Retry-After", "60"]]))
            self.assertEqual(h.run()[0], 4)
            h.t += 3600
            return h

        def refused(h: Harness, code: str, note: str = "") -> None:
            got = h.run()
            self.assertEqual((got[0], h.refusal(got[2])), (2, code), note or got[2])
            self.assertEqual(len(h.calls), 1, f"{code}: the refusal sent no request")

        def rewrite(h: Harness, change: Any, rechain: bool) -> None:
            path = h.jdir / "journal.jsonl"
            rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
            change(rows[[r["type"] for r in rows].index("RESULT")])
            lines: list[bytes] = []
            for i, row in enumerate(rows):
                if i and rechain:
                    row["prev"] = h.b.sha256_bytes(lines[-1])
                lines.append(json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
            path.write_bytes(b"".join(lines))
        h = paused()
        rules = dict(json.loads(POLICY_PATH.read_text(encoding="utf-8"))["rules"], retry_after_fallback_seconds=901)
        h.write_policy(rules=rules)
        refused(h, "CAPTURE_POLICY_CHANGED")
        h = paused()
        record = h.lines()[[x["type"] for x in h.lines()].index("RESULT")]["request"]
        (h.out / "raw" / "sha256" / record["body_sha256"]).write_bytes(b"<html>not busy</html>")
        refused(h, "RAW_ALTERED")
        h = paused()
        rewrite(h, lambda row: row["request"].update(http_status=200), rechain=False)
        refused(h, "CAPTURE_JOURNAL_PREFIX_CHANGED")
        h = paused()
        rewrite(h, lambda row: row["request"].update(http_status=200), rechain=True)
        refused(h, "CAPTURE_JOURNAL_PREFIX_CHANGED", "a coordinated rechain no longer hashes to the anchored head")
        h = paused()
        data = (h.jdir / "journal.jsonl").read_bytes().splitlines(keepends=True)
        (h.jdir / "journal.jsonl").write_bytes(b"".join(data[:-2]))
        refused(h, "CAPTURE_COUNTER_RESET", "a truncated journal is a reset counter")
        h = paused()
        (h.jdir / "AUTHORITY.json").unlink()
        refused(h, "CAPTURE_COUNTER_RESET", "a missing anchor beside recorded intents")
        h = paused()
        (h.jdir / "journal.jsonl").unlink()
        refused(h, "CAPTURE_COUNTER_RESET", "a missing journal beside its anchor")
        h = paused()
        (h.jdir / "journal.jsonl").unlink()
        (h.jdir / "AUTHORITY.json").unlink()
        refused(h, "CAPTURE_COUNTER_RESET", "a fresh journal beside retained raw evidence is not a renewed budget")
        h = paused()
        keys = h.binding["ordered_keys"]
        h.write_policy(dict(h.binding, ordered_keys=[keys[1], keys[0], *keys[2:]]))
        refused(h, "CAPTURE_KEYSET_MISMATCH")

    def test_mode_conflicts_refuse_in_both_directions(self) -> None:
        h = Harness()
        h.reply(meta_fragment(h, h.binding["ordered_keys"][0]), Reply(crash=True))
        with self.assertRaises(SimulatedCrash):
            h.run(policy=False)
        self.assertEqual(h.refusal(h.run()[2]), "CAPTURE_MODE_CONFLICT")
        h2 = Harness()
        h2.reply(meta_fragment(h2, h2.binding["ordered_keys"][0]), Reply())
        self.assertEqual(h2.run()[0], 4)
        self.assertEqual(h2.refusal(h2.run(policy=False)[2]), "REFUSED_STALE_JOURNAL")

    def test_a_finalization_by_another_owner_before_the_lock_is_seen_under_the_lock(self) -> None:
        h = Harness()
        self.assertEqual(h.run()[0], 0)
        before, calls = h.snapshot(), len(h.calls)
        real_is_dir = Path.is_dir
        hidden: list[str] = []

        def blind_once(path: Path) -> bool:
            if not hidden and path.parts[-2:] == ("acquisition", "sha256") and h.out in path.parents:
                hidden.append(str(path))
                return False
            return real_is_dir(path)
        code, result, err = h.run(extra_patches=[mock.patch.object(Path, "is_dir", blind_once)])
        self.assertEqual(hidden, [str(h.out / "acquisition" / "sha256")], "the unlocked check was bypassed")
        self.assertEqual((code, result["capture"]["state"], result["capture"]["new_requests"]),
                         (0, "ALREADY_FINALIZED", 0), err)
        self.assertEqual({k: v for k, v in h.snapshot().items() if not k.endswith("OWNER.lock")},
                         {k: v for k, v in before.items() if not k.endswith("OWNER.lock")})
        self.assertEqual(len(h.calls), calls)

    def test_two_concurrent_owners_spend_at_most_the_one_remaining_request(self) -> None:
        h = Harness(contract_patch=lambda c: c["acquisition"]["limits"].update(total_requests=1))
        h.hold, h.entered = threading.Event(), threading.Event()
        results: dict[str, Any] = {}
        sink = io.StringIO()

        def first() -> None:
            try:
                results["a"] = h.b.main(h.argv() + ["--receipt", str(h.dir / "a.json")])
            except BaseException as exc:  # noqa: BLE001 - reported to the main thread
                results["a"] = exc
        with h.patches(), contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            thread = threading.Thread(target=first)
            thread.start()
            self.assertTrue(h.entered.wait(30))
            results["b"] = h.b.main(h.argv() + ["--receipt", str(h.dir / "b.json")])
            h.hold.set()
            thread.join(60)
        self.assertEqual(results["b"], 2)
        self.assertIn("CAPTURE_OWNER_ACTIVE", sink.getvalue())
        self.assertFalse((h.dir / "b.json").exists())
        self.assertEqual(results["a"], 0)
        cap = json.loads((h.dir / "a.json").read_text(encoding="utf-8"))["capture"]
        self.assertEqual((cap["state"], cap["totals"]["requests"]), ("FINALIZED", 1))
        self.assertEqual(len(h.calls), 1, "one remaining allocation: at most one request")


class V12ContractTests(unittest.TestCase):
    def test_the_v1_2_contract_pauses_and_resumes_through_the_same_mode(self) -> None:
        h = Harness(v12=True)
        keys = h.binding["ordered_keys"]
        h.reply("wayback/available", Reply(headers=[["Retry-After", "Wed, 07 Oct 2026 16:00:00 GMT"]]))
        code, result, err = h.run()
        self.assertEqual(code, 4, err)
        cap = result["capture"]
        self.assertEqual((cap["pause"]["retry_after_rule"], cap["eligible_utc"]),
                         ("HTTP_DATE", "2026-10-07T16:00:00.000000Z"))
        self.assertEqual(cap["keys"]["attempted_failed_pending"], keys[:1])
        h.set_now("2026-10-07T16:00:00.000000Z")
        code, result, err = h.run()
        self.assertEqual((code, result["capture"]["state"]), (0, "FINALIZED"), err)
        self.assertEqual(result["capture"]["outcomes"][h.world["contract_doc"]["scope"]["control_contest_key"]],
                         "CONTROL_REUSED")


# --------------------------------------------------------------------------------------------- C44-CONT-01 helpers

TAIL = "CAPTURE_JOURNAL_TAIL_NOT_ANNOUNCED"
DERIVED = "CAPTURE_JOURNAL_LINE_NOT_DERIVED"
LIMIT = 65536


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def line_of(row: dict[str, Any]) -> bytes:
    return json.dumps(row, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n"


def raw_lines(h: Harness) -> list[bytes]:
    return (h.jdir / "journal.jsonl").read_bytes().splitlines(keepends=True)


def replace_tail(h: Harness, row: dict[str, Any]) -> None:
    """Replace only the last journal line (its ``prev`` kept): the anchored prefix and the anchor stay untouched."""
    (h.jdir / "journal.jsonl").write_bytes(b"".join(raw_lines(h)[:-1]) + line_of(row))


def append_chained(h: Harness, row: dict[str, Any]) -> None:
    """Append one correctly chained line without touching the anchor."""
    with (h.jdir / "journal.jsonl").open("ab") as handle:
        handle.write(line_of(dict(row, prev=sha(raw_lines(h)[-1]))))


def write_rechained(h: Harness, rows: list[dict[str, Any]]) -> None:
    """Rewrite the whole journal with every ``prev`` re-chained (a coordinated edit)."""
    lines: list[bytes] = []
    for index, row in enumerate(rows):
        if index:
            row["prev"] = sha(lines[-1])
        lines.append(line_of(row))
    (h.jdir / "journal.jsonl").write_bytes(b"".join(lines))


def reanchor(h: Harness, lines: int | None = None) -> None:
    """An adversary who also rewrites the request-authority anchor consistently with the journal bytes: line count
    (every line unless ``lines``), intent count, head and an announcement of any one following line."""
    data = raw_lines(h)
    count = len(data) if lines is None else lines
    rows = [json.loads(x) for x in data]
    doc = json.loads((h.jdir / "AUTHORITY.json").read_text(encoding="utf-8"))
    doc.update(lines=count, intents=sum(1 for r in rows[:count] if r["type"] == "INTENT"),
               head_sha256=sha(data[count - 1]), pending_sha256=sha(data[count]) if count < len(data) else None)
    (h.jdir / "AUTHORITY.json").write_bytes(h.b.canonical_json_bytes(doc) + b"\n")


def crash_after(h: Harness, kind: str, nth: int = 1) -> Any:
    """Interrupt the process right after the ``nth`` journal line of ``kind`` was appended and fsynced and before the
    request-authority anchor advanced to it (an announcement of that line, if the producer makes one, is kept)."""
    real = h.b._write_authority
    seen: list[int] = []

    def crash(journal: Any, *args: Any) -> None:
        advancing = len(args) < 3 or args[2] is None
        if advancing and journal.rows[-1].get("type") == kind:
            seen.append(1)
            if len(seen) == nth:
                raise SimulatedCrash(f"after {kind} #{nth}, before the anchor advanced")
        real(journal, *args)
    return mock.patch.object(h.b, "_write_authority", crash)


def paused_harness(retry_after: str = "600", **kwargs: Any) -> Harness:
    h = Harness(**kwargs)
    h.reply(meta_fragment(h, first_key(h)), Reply(headers=[["Retry-After", retry_after]]))
    return h


def limited() -> Harness:
    return Harness(contract_patch=lambda c: c["acquisition"]["limits"].update(max_body_bytes=LIMIT))


def busy_at(h: Harness, location: str, reply: Reply) -> int:
    """Script ``reply`` at the metadata, replay or redirect-hop request; returns that request's number."""
    if location == "metadata":
        h.reply(meta_fragment(h, first_key(h)), reply)
        return 1
    if location == "replay":
        h.reply("20190910020000id_/", reply)
        return 3
    game = h.world["cby"]["ncaa:1004"]["cfbd_game_id"]["value"]
    h.reply("20190910020000id_/", Reply(302, [["Location", "https://web.archive.org/web/20190910030000id_/"
                                                            + apfx.game_url(game)]], b""))
    h.reply("20190910030000id_/", reply)
    return 4


class JournalTailTests(unittest.TestCase):
    """MF44A01-01: the one-line append/anchor crash window and the decision-bearing lines."""

    def refused(self, h: Harness, code: str, contains: str = "") -> None:
        before = {k: v for k, v in h.snapshot().items() if not k.endswith("OWNER.lock")}
        calls = len(h.calls)
        got = h.run()
        self.assertEqual((got[0], h.refusal(got[2])), (2, code), got[2])
        self.assertIn(contains, got[2])
        self.assertEqual(len(h.calls), calls, f"{code}: the refusal sent no request")
        self.assertEqual({k: v for k, v in h.snapshot().items() if not k.endswith("OWNER.lock")}, before,
                         f"{code}: the refusal wrote nothing")

    def test_a_genuine_crash_after_each_decision_line_resumes_from_its_announced_tail(self) -> None:
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "PAUSE")])
        self.assertEqual(h.types()[-1], "PAUSE")
        record = next(x["request"] for x in h.lines() if x["type"] == "RESULT")
        h.t += 10
        code, result, err = h.run()
        cap = result["capture"]
        self.assertEqual((code, cap["state"], cap["new_requests"], len(h.calls)), (4, "DEFERRED", 0, 1), err)
        self.assertEqual(utc(cap["eligible_utc"]), utc(record["ended_utc"]) + dt.timedelta(seconds=600),
                         "the raw 600 s cooldown is kept")
        h.set_now(cap["eligible_utc"])
        code, result, err = h.run()
        self.assertEqual((code, result["capture"]["state"], result["capture"]["totals"]["requests"]),
                         (0, "FINALIZED", 10), err)
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "RESULT")])
        self.assertEqual(h.types()[-1], "RESULT")
        h.t += 10
        code, result, err = h.run()
        cap = result["capture"]
        self.assertEqual((code, cap["state"], cap["new_requests"], len(h.calls)), (4, "DEFERRED", 0, 1), err)
        self.assertTrue(cap["pauses"][0]["recovered"], "the announced 429 result is adopted and its pause derived")
        for kind, nth in (("KEY_DONE", 1), ("KEY_DONE", 4), ("OWNER_START", 1), ("FINALIZED", 1)):
            with self.subTest(kind=kind, nth=nth):
                h = Harness()
                with self.assertRaises(SimulatedCrash):
                    h.run(extra_patches=[crash_after(h, kind, nth)])
                done = list(h.calls)
                code, result, err = h.run()
                self.assertEqual(code, 0, err)
                self.assertEqual(result["capture"]["state"], "ALREADY_FINALIZED" if kind == "FINALIZED" else
                                 "FINALIZED")
                self.assertEqual(h.calls[:len(done)], done)
                self.assertEqual(len(h.calls), 9, "no completed request is repeated")
        h = paused_harness()
        self.assertEqual(h.run()[0], 4)
        h.set_now([x for x in h.lines() if x["type"] == "PAUSE"][0]["eligible_utc"])
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "RESUME")])
        self.assertEqual(h.types()[-1], "RESUME")
        code, result, err = h.run()
        self.assertEqual((code, result["capture"]["state"], result["capture"]["totals"]["requests"]),
                         (0, "FINALIZED", 10), err)

    def test_a_forged_unanchored_pause_cannot_shorten_the_cooldown(self) -> None:
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "PAUSE")])
        rows = h.lines()
        genuine = rows[-1]["eligible_utc"]
        record = next(x["request"] for x in rows if x["type"] == "RESULT")
        replace_tail(h, dict(rows[-1], eligible_utc=record["ended_utc"], delay_seconds="0.000000"))
        h.t += 10
        self.refused(h, TAIL)
        h.set_now(genuine)
        self.refused(h, TAIL, "is not the line the request-authority anchor announced")

    def test_a_forged_unanchored_key_done_cannot_invent_a_capture(self) -> None:
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "PAUSE")])
        rows = h.lines()
        genuine = rows[-1]["eligible_utc"]
        replace_tail(h, {"type": "KEY_DONE", "contest_key": first_key(h), "acquisition_outcome": "CAPTURED",
                         "prev": rows[-1]["prev"]})
        h.t += 10
        self.refused(h, TAIL)
        h.set_now(genuine)
        self.refused(h, TAIL)

    def test_an_appended_chained_key_done_after_a_closed_pause_refuses(self) -> None:
        h = paused_harness()
        code, paused, err = h.run()
        self.assertEqual(code, 4, err)
        append_chained(h, {"type": "KEY_DONE", "contest_key": first_key(h), "acquisition_outcome": "CAPTURED"})
        h.t += 10
        self.refused(h, TAIL)
        h.set_now(paused["capture"]["eligible_utc"])
        self.refused(h, TAIL)

    def test_a_forged_tail_with_a_rewritten_announcement_refuses_by_derivation(self) -> None:
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "PAUSE")])
        rows = h.lines()
        record = next(x["request"] for x in rows if x["type"] == "RESULT")
        replace_tail(h, dict(rows[-1], eligible_utc=record["ended_utc"], delay_seconds="0.000000"))
        reanchor(h, lines=len(rows) - 1)
        h.t += 10
        self.refused(h, DERIVED, "(PAUSE): delay_seconds")

    def test_forged_tail_observations_acknowledgements_and_transitions_refuse(self) -> None:
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "RESULT")])
        tail = h.lines()[-1]
        replace_tail(h, dict(tail, request=dict(tail["request"], http_status=200)))
        h.t += 10
        self.refused(h, TAIL)
        h = Harness()
        keys = h.binding["ordered_keys"]
        h.reply(meta_fragment(h, keys[1]), Reply(crash=True))
        with self.assertRaises(SimulatedCrash):
            h.run()
        seq = h.lines()[-1]["seq"]
        append_chained(h, {"type": "ACKNOWLEDGED", "seq": seq, "at": h.now(), "decision": "COUNTED_RESULT_UNKNOWN",
                           "anchor_had_advanced": True})
        self.refused(h, TAIL, "is not the line the request-authority anchor announced")
        for name, line in (("RESUME", lambda p: {"type": "RESUME", "after_pause_seq": 1,
                                                 "eligible_utc": p["eligible_utc"], "at": p["eligible_utc"]}),
                           ("FINALIZED", lambda p: {"type": "FINALIZED", "acquisition_identity": "0" * 64}),
                           ("INTENT", lambda p: {"type": "INTENT", "seq": 2, "contest_key": p["contest_key"],
                                                 "kind": "METADATA", "purpose": "RETRY", "url": p["url"],
                                                 "started_utc": p["recorded_utc"]})):
            with self.subTest(line=name):
                h = paused_harness()
                self.assertEqual(h.run()[0], 4)
                append_chained(h, line(next(x for x in h.lines() if x["type"] == "PAUSE")))
                h.t += 10
                self.refused(h, TAIL)

    def test_coordinated_rewrites_of_derived_lines_refuse_by_derivation(self) -> None:
        def closed_pause() -> tuple[Harness, list[dict[str, Any]]]:
            h = paused_harness()
            self.assertEqual(h.run()[0], 4)
            return h, h.lines()

        def index_of(rows: list[dict[str, Any]], kind: str) -> int:
            return [r["type"] for r in rows].index(kind)
        h, rows = closed_pause()
        record = rows[index_of(rows, "RESULT")]["request"]
        rows[index_of(rows, "PAUSE")].update(eligible_utc=record["ended_utc"], delay_seconds="0.000000")
        write_rechained(h, rows)
        reanchor(h)
        h.t += 10
        self.refused(h, DERIVED, "(PAUSE): delay_seconds")
        h, rows = closed_pause()
        append_chained(h, {"type": "KEY_DONE", "contest_key": first_key(h), "acquisition_outcome": "CAPTURED"})
        reanchor(h)
        h.t += 10
        self.refused(h, DERIVED, "(KEY_DONE): a key completion outside an eligible owner invocation")
        h, rows = closed_pause()
        pause = rows[index_of(rows, "PAUSE")]
        h.t += 10
        append_chained(h, {"type": "OWNER_START", "owner": "f" * 32, "pid": 1, "at": h.now(),
                           "previous_owner_unreleased": []})
        append_chained(h, {"type": "RESUME", "after_pause_seq": pause["seq"], "eligible_utc": pause["eligible_utc"],
                           "at": h.now()})
        reanchor(h)
        self.refused(h, DERIVED, "(OWNER_START): the owner started before the paused acquisition's eligible instant")
        h, rows = closed_pause()
        rows[index_of(rows, "RESULT")]["request"]["body_bytes"] += 1
        write_rechained(h, rows)
        reanchor(h)
        h.t += 10
        self.refused(h, DERIVED, "(RESULT): the result's derived fields do not match its own observation")
        h, rows = closed_pause()
        intent, result = rows[index_of(rows, "INTENT")], rows[index_of(rows, "RESULT")]["request"]
        moved = intent["url"].replace("timestamp=", "timestamp=1")
        intent["url"] = result["url"] = rows[index_of(rows, "PAUSE")]["url"] = moved
        write_rechained(h, rows)
        reanchor(h)
        h.t += 10
        self.refused(h, DERIVED, "(INTENT): the request")
        h = Harness()
        h.reply("id_/https://www.espn.com", Reply(headers=[["Retry-After", "30"]]))
        self.assertEqual(h.run()[0], 4)
        rows = h.lines()
        done = next(r for r in rows if r["type"] == "KEY_DONE")
        self.assertEqual(done["acquisition_outcome"], "RETAINED_VERSION_REUSED")
        done["acquisition_outcome"] = "CAPTURED"
        write_rechained(h, rows)
        reanchor(h)
        h.t += 3600
        self.refused(h, DERIVED, "(KEY_DONE): outcome 'CAPTURED' is not 'RETAINED_VERSION_REUSED'")
        h = Harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "KEY_DONE", 4)])
        append_chained(h, {"type": "FINALIZED", "acquisition_identity": "0" * 64})
        reanchor(h)
        self.refused(h, DERIVED, "(FINALIZED): the finalized identity is not the document of the recorded observations")

    def test_a_lost_announced_result_stays_counted_under_explicit_reconciliation(self) -> None:
        h = paused_harness()
        with self.assertRaises(SimulatedCrash):
            h.run(extra_patches=[crash_after(h, "RESULT")])
        (h.jdir / "journal.jsonl").write_bytes(b"".join(raw_lines(h)[:-1]))
        h.t += 10
        code, result, err = h.run()
        cap = result["capture"]
        self.assertEqual((code, result["state"], cap["new_requests"], cap["requests_used"], len(h.calls)),
                         (5, "CAPTURE_RECONCILIATION_REQUIRED", 0, 1, 1), err)
        (unknown,) = cap["unknown_intents"]
        self.assertTrue(unknown["anchor_had_advanced"], "the request may have been sent; it is not invented")


class BodyLimitTests(unittest.TestCase):
    """MF44A01-02: an observed 429 whose bounded body is oversized or unreadable still pauses at that request."""

    def test_a_429_body_at_the_cap_pauses_with_its_whole_body(self) -> None:
        for location in ("metadata", "replay", "redirect"):
            with self.subTest(location=location):
                h = limited()
                body = b"y" * LIMIT
                at = busy_at(h, location, Reply(429, [["Retry-After", "600"]], body))
                code, result, err = h.run()
                cap = result["capture"]
                self.assertEqual((code, cap["state"], len(h.calls), cap["requests_used"]),
                                 (4, "PAUSED_SERVICE_429", at, at), err)
                record = [x for x in h.lines() if x["type"] == "RESULT"][-1]["request"]
                self.assertEqual((record["http_status"], record["body_bytes"], record["error"]), (429, LIMIT, None))
                self.assertEqual((h.out / "raw" / "sha256" / record["body_sha256"]).read_bytes(), body)

    def test_an_oversized_429_body_keeps_status_and_headers_and_pauses_at_the_first_429(self) -> None:
        for location in ("metadata", "replay", "redirect"):
            with self.subTest(location=location):
                h = limited()
                body = bytes(range(256)) * (LIMIT // 256) + b"z"
                at = busy_at(h, location, Reply(429, [["Retry-After", "600"]], body))
                code, result, err = h.run()
                cap = result["capture"]
                self.assertEqual((code, cap["state"], len(h.calls), cap["new_requests"], cap["requests_used"]),
                                 (4, "PAUSED_SERVICE_429", at, at, at), err)
                pause = cap["pause"]
                self.assertEqual((pause["seq"], pause["http_status"], pause["retry_after_raw"],
                                  pause["retry_after_rule"]), (at, 429, ["600"], "DELTA_SECONDS"))
                self.assertEqual(utc(cap["eligible_utc"]) - utc(pause["response_clock_utc"]),
                                 dt.timedelta(seconds=600))
                record = [x for x in h.lines() if x["type"] == "RESULT"][-1]["request"]
                self.assertEqual((record["outcome"], record["http_status"], record["body_bytes"]),
                                 ("RESPONSE", 429, LIMIT))
                self.assertTrue(record["error"].startswith(f"BODY_LIMIT_EXCEEDED: more than {LIMIT} bytes"))
                self.assertEqual((h.out / "raw" / "sha256" / record["body_sha256"]).read_bytes(), body[:LIMIT])
                self.assertEqual(cap["keys"]["attempted_failed_pending"], [record["contest_key"]])
                h.t += 10
                code, result, err = h.run()
                self.assertEqual((code, result["capture"]["state"], len(h.calls)), (4, "DEFERRED", at), err)

    def test_a_429_body_read_failure_after_the_status_pauses_at_the_first_429(self) -> None:
        for location, error, kept in (("metadata", ConnectionResetError("fixture: reset mid-body"), b""),
                                      ("replay", TimeoutError("fixture: body read timed out"), b""),
                                      ("redirect", http.client.IncompleteRead(b"x" * 1000), b"x" * 1000)):
            with self.subTest(location=location):
                h = limited()
                at = busy_at(h, location, Reply(429, [["Retry-After", "600"]], b"x" * 5000, fail_after=1000,
                                                fail_with=error))
                code, result, err = h.run()
                cap = result["capture"]
                self.assertEqual((code, cap["state"], len(h.calls), cap["requests_used"]),
                                 (4, "PAUSED_SERVICE_429", at, at), err)
                self.assertEqual((cap["pause"]["retry_after_raw"], cap["pause"]["retry_after_rule"]),
                                 (["600"], "DELTA_SECONDS"))
                record = [x for x in h.lines() if x["type"] == "RESULT"][-1]["request"]
                self.assertEqual((record["http_status"], record["body_bytes"]), (429, len(kept)))
                self.assertEqual((h.out / "raw" / "sha256" / record["body_sha256"]).read_bytes(), kept,
                                 "the bounded evidence actually read is retained, nothing invented")
                self.assertTrue(record["error"].startswith(f"BODY_READ_FAILED: {type(error).__name__}"))

    def test_non_429_incomplete_bodies_and_network_errors_stay_failures_not_pauses(self) -> None:
        big = b"{" + b" " * LIMIT + b"}"

        def script(h: Harness) -> None:
            keys = h.binding["ordered_keys"]
            h.reply(meta_fragment(h, keys[0]), *(Reply(200, [["Content-Type", "application/json"]], big)
                                                 for _ in range(2)))
            h.reply(meta_fragment(h, keys[1]), Reply(network_error=True))
            h.reply(meta_fragment(h, keys[2]), *(Reply(404, [["Content-Type", "text/html"]], b"n" * (LIMIT + 1))
                                                 for _ in range(2)))
            h.reply(meta_fragment(h, keys[3]), Reply(200, [["Content-Type", "application/json"]], big[:5000],
                                                     fail_after=100))
        h = limited()
        script(h)
        code, result, err = h.run()
        self.assertEqual(code, 0, err)
        cap = result["capture"]
        self.assertEqual((cap["state"], cap["pauses"]), ("FINALIZED", []))
        doc = json.loads(Path(cap["path"]).read_text(encoding="utf-8"))
        failed = [r for r in doc["requests"] if r["outcome"] != "RESPONSE"]
        self.assertEqual(len(failed), 6)
        for r in failed:
            self.assertEqual((r["http_status"], r["body_sha256"], r["headers"]), (None, None, []))
        self.assertEqual(sorted(r["error"].split(":")[0] for r in failed),
                         ["BODY_LIMIT_EXCEEDED"] * 4 + ["BODY_READ_FAILED", "URLError"])
        self.assertTrue(all("received; body not retained" in r["error"] for r in failed if "BODY" in r["error"]))
        legacy = limited()
        script(legacy)
        contract, _ = legacy.b.load_expansion_contract(legacy.contract_path)
        control = legacy.b.verify_control(contract, legacy.world["route"])
        retained = legacy.b.import_retained(contract, legacy.world["out"], legacy.out)
        with legacy.patches():
            default = legacy.b.capture_expansion(contract, legacy.out, control, retained["document"],
                                                 sleep=legacy.sleep, monotonic=legacy.perf, now=legacy.now,
                                                 audit=False)
        legacy_doc = json.loads(Path(default["path"]).read_text(encoding="utf-8"))
        shape = [(r["contest_key"], r["kind"], r["purpose"], r["url"], r["outcome"], r["http_status"],
                  r["body_sha256"]) for r in doc["requests"]]
        self.assertEqual(shape, [(r["contest_key"], r["kind"], r["purpose"], r["url"], r["outcome"],
                                  r["http_status"], r["body_sha256"]) for r in legacy_doc["requests"]],
                         "the service mode plans exactly the default mode's requests and failures")
        self.assertEqual(doc["outcomes"], legacy_doc["outcomes"])

    def test_the_default_mode_keeps_its_frozen_body_limit_network_error_for_a_429(self) -> None:
        h = Harness(contract_patch=lambda c: c["acquisition"]["limits"].update(max_body_bytes=LIMIT,
                                                                               total_requests=2))
        h.reply(meta_fragment(h, first_key(h)), *(Reply(429, [["Retry-After", "1"]], b"q" * (LIMIT + 1))
                                                  for _ in range(2)))
        code, result, err = h.run(policy=False)
        self.assertEqual(code, 0, err)
        doc = json.loads(Path(result["capture"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual([(r["purpose"], r["outcome"], r["http_status"], r["error"]) for r in doc["requests"]],
                         [(p, "NETWORK_ERROR", None, f"BODY_LIMIT_EXCEEDED: more than {LIMIT} bytes")
                          for p in ("PROBE_1", "RETRY")], "the default mode's frozen behaviour is unchanged")


if __name__ == "__main__":
    unittest.main()
