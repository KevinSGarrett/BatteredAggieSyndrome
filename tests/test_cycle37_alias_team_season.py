"""Cycle #37 - Attempt #2 - ACTUAL_STATE: the cache-only team-season route of the R37-04 alias crosswalk."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cycle37" / "r37_04_alias_crosswalk.py"


def _load():
    spec = importlib.util.spec_from_file_location("r37_04_alias_crosswalk", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _page(title: str, text: str, redirects: list[tuple[str, str]] | None = None) -> dict:
    return {"query": {"redirects": [{"from": a, "to": b} for a, b in redirects or []],
                      "pages": {"1": {"title": title, "revisions": [
                          {"revid": 7, "timestamp": "2026-01-01T00:00:00Z", "slots": {"main": {"*": text}}}]}}}}


class TeamSeasonRouteTests(unittest.TestCase):
    """A page binds an alias only by its own naming of its team, never by an opponent in its text."""

    def test_fold_removes_accents_case_and_punctuation(self) -> None:
        tool = _load()
        self.assertEqual(tool.fold("Louisiana–Lafayette Ragin' Cajuns"), "louisiana lafayette ragin cajuns")
        self.assertEqual(tool.fold("San José State"), "san jose state")

    def test_only_a_trailing_parenthesised_qualifier_is_dropped(self) -> None:
        tool = _load()
        self.assertEqual(tool.unqualified("Saint Mary's (CA)"), "Saint Mary's")
        self.assertEqual(tool.unqualified("Miami (OH)"), "Miami")
        self.assertEqual(tool.unqualified("Texas A&M-Commerce / East Texas A&M"), "Texas A&M-Commerce / East Texas A&M")
        self.assertEqual(tool.unqualified("St. John's (NY) Red Storm"), "St. John's (NY) Red Storm")

    def test_lead_definition_and_infobox_are_read_and_opponents_are_not(self) -> None:
        tool = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.json").write_text(json.dumps(_page(
                "2025 UT Rio Grande Valley Vaqueros football team",
                "{{Infobox\n| team = UT Rio Grande Valley Vaqueros\n}}\nThe 2025 team represented the "
                "[[University of Texas Rio Grande Valley]] (UTRGV) in 2025.",
                [("2025 UTRGV Vaqueros football team", "2025 UT Rio Grande Valley Vaqueros football team")])),
                encoding="utf-8")
            (root / "b.json").write_text(json.dumps(_page(
                "2012 Nicholls State Colonels football team",
                "{{Infobox\n| team = Nicholls State Colonels\n}}\nThe team represented [[Nicholls State University]]"
                " and lost to McNeese State (McNeese) and Southeastern Louisiana.")), encoding="utf-8")
            (root / "c.json").write_text(json.dumps(_page(
                "1999 Old Program football team", "represented the [[Old College]] (OC)")), encoding="utf-8")
            tool.WIKIMEDIA = root
            pages, redirects = tool.team_season_pages({2012, 2025})
            expected_sha = hashlib.sha256((root / "a.json").read_bytes()).hexdigest()
        rgv = pages[tool.fold("2025 UT Rio Grande Valley Vaqueros football team")]
        self.assertEqual(rgv["lead_defines"], "utrgv")
        self.assertEqual(rgv["infobox_team"], "UT Rio Grande Valley Vaqueros")
        self.assertEqual(rgv["revid"], 7)
        self.assertEqual(rgv["sha256"], expected_sha)
        nicholls = pages[tool.fold("2012 Nicholls State Colonels football team")]
        # an opponent's parenthesised short name is not the page's own definition
        self.assertIsNone(nicholls["lead_defines"])
        self.assertNotIn("mcneese", json.dumps(nicholls).casefold())
        # a season outside the requested set is never read
        self.assertNotIn(tool.fold("1999 Old Program football team"), pages)
        self.assertEqual(redirects[tool.fold("2025 UTRGV Vaqueros football team")],
                         tool.fold("2025 UT Rio Grande Valley Vaqueros football team"))

    def test_feed_names_come_from_the_canonical_cached_request(self) -> None:
        tool = _load()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = {"endpoint": "/teams", "parameters": {"year": 2009}}
            identity = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":"),
                                                 ensure_ascii=False).encode("utf-8")).hexdigest()
            (root / f"{identity}.json").write_text(json.dumps(
                [{"id": 309, "school": "Louisiana", "mascot": "Ragin' Cajuns"}, {"id": 1, "school": "No Mascot"}]),
                encoding="utf-8")
            tool.TEAMS = root
            feed = tool.season_feed_names([2009, 2010])
        self.assertEqual(feed, {(2009, "SRC-002:TEAM:309"): ("Louisiana", "Ragin' Cajuns")})


if __name__ == "__main__":
    unittest.main()
