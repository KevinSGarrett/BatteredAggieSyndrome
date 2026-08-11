from __future__ import annotations

import unittest

from aggie_analytics.data.sec_availability import extract_candidate_rows, parse_article


def article(table_label: str, headers: list[str], rows: list[list[str]], published: str = "2024-09-12T00:38:18.395Z") -> str:
    header_html = "".join(f"<th>{value}</th>" for value in headers)
    row_html = "".join("<tr>" + "".join(f"<td>{value}</td>" for value in row) + "</tr>" for row in rows)
    return (
        '<script type="application/ld+json">'
        + '{"@type":"NewsArticle","headline":"Report","datePublished":"'
        + published
        + '"}</script><p><b>'
        + table_label
        + "</b></p><table><thead><tr>"
        + header_html
        + "</tr></thead><tbody>"
        + row_html
        + "</tbody></table>"
    )


def source(**overrides):
    base = {
        "source_record_id": "TEST-REPORT",
        "source_class": "MEDIA_REPRODUCTION_OF_OFFICIAL_REPORT",
        "url": "https://example.test/report",
        "season": 2024,
        "game_label": "Texas A&M at Florida",
        "target_game_date": "2024-09-14",
        "report_version": "WEDNESDAY_INITIAL",
        "table_heading_contains": "Texas A&M Availability Report",
    }
    base.update(overrides)
    return base


class SecAvailabilityTest(unittest.TestCase):
    def test_table_and_publication_are_parsed(self) -> None:
        parsed = parse_article(
            article("Texas A&M Availability Report (Sept. 11)", ["Player", "Position", "Status"], [["Rueben Owens", "RB", "Out"]])
        )
        self.assertEqual(parsed.date_published, "2024-09-12T00:38:18.395Z")
        self.assertEqual(parsed.tables[0].label, "Texas A&M Availability Report (Sept. 11)")
        self.assertEqual(parsed.tables[0].rows, [["Rueben Owens", "RB", "Out"]])

    def test_candidate_is_source_scoped_and_never_admitted(self) -> None:
        rows, findings, _ = extract_candidate_rows(
            document=article("Texas A&M Availability Report", ["Player", "Position", "Status"], [["Scooby Williams", "LB", "Questionable"]]),
            source=source(),
            capture_sha256="a" * 64,
            captured_at_utc="2026-08-11T00:00:00Z",
        )
        self.assertEqual(findings, [])
        self.assertEqual(rows[0]["status"], "QUESTIONABLE")
        self.assertIsNone(rows[0]["canonical_player_id"])
        self.assertTrue(rows[0]["historical_known_at_candidate"])
        self.assertFalse(rows[0]["pit_state_admission"])
        self.assertFalse(rows[0]["absence_means_available"])

    def test_embedded_position_layout(self) -> None:
        rows, findings, _ = extract_candidate_rows(
            document=article("Texas A&M CFP First Round Availability Report", ["Player", "Status"], [["RB Le’Veon Moss", "PROBABLE"]]),
            source=source(
                position_embedded_in_player=True,
                table_heading_contains="Texas A&M CFP First Round Availability Report",
            ),
            capture_sha256="b" * 64,
            captured_at_utc="2026-08-11T00:00:00Z",
        )
        self.assertEqual(findings, [])
        self.assertEqual(rows[0]["player_name_normalized"], "Le'Veon Moss")
        self.assertEqual(rows[0]["position_raw"], "RB")

    def test_name_header_schema_drift_is_normalized(self) -> None:
        rows, findings, _ = extract_candidate_rows(
            document=article("Texas A&M Availability Report", ["Name", "Position", "Status"], [["A B", "DB", "Doubtful"]]),
            source=source(),
            capture_sha256="f" * 64,
            captured_at_utc="2026-08-11T00:00:00Z",
        )
        self.assertEqual(findings, [])
        self.assertEqual(rows[0]["player_name_normalized"], "A B")
        self.assertEqual(rows[0]["status"], "DOUBTFUL")

    def test_missing_publication_is_quarantined(self) -> None:
        document = "<p><b>Texas A&M Availability Report</b></p><table><tr><th>Player</th><th>Status</th></tr><tr><td>A B</td><td>Out</td></tr></table>"
        rows, findings, _ = extract_candidate_rows(
            document=document,
            source=source(),
            capture_sha256="c" * 64,
            captured_at_utc="2026-08-11T00:00:00Z",
        )
        self.assertEqual(rows, [])
        self.assertEqual(findings[0]["reason"], "PUBLICATION_TIME_MISSING")

    def test_unknown_status_is_quarantined_not_fabricated(self) -> None:
        rows, findings, _ = extract_candidate_rows(
            document=article("Texas A&M Availability Report", ["Player", "Status"], [["A B", "Healthy-ish"]]),
            source=source(),
            capture_sha256="d" * 64,
            captured_at_utc="2026-08-11T00:00:00Z",
        )
        self.assertEqual(rows, [])
        self.assertEqual(findings[0]["reason"], "ROW_VALUE_INVALID")

    def test_report_version_changes_identity(self) -> None:
        document = article("Texas A&M Availability Report", ["Player", "Status"], [["A B", "Out"]])
        first, _, _ = extract_candidate_rows(document=document, source=source(), capture_sha256="e" * 64, captured_at_utc="2026-08-11T00:00:00Z")
        second, _, _ = extract_candidate_rows(document=document, source=source(report_version="THURSDAY_UPDATE"), capture_sha256="e" * 64, captured_at_utc="2026-08-11T00:00:00Z")
        self.assertNotEqual(first[0]["availability_candidate_id"], second[0]["availability_candidate_id"])


if __name__ == "__main__":
    unittest.main()
