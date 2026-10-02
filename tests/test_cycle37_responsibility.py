"""Cycle #37 - Attempt #2 - ACTUAL_STATE

R37-06: play-calling mentions are classified in their own sentence, and only
an official staff title bound to a program and season is a current
responsibility. Each case below is the shape of a sentence found in the
cached population; the rule it pins is named in the test.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aggie_analytics.cycle37 import responsibility as rs  # noqa: E402


def classify(sentence: str, subject: str | None = None) -> dict:
    match = rs.MENTION.search(sentence)
    assert match is not None, sentence
    return rs.classify_sentence(sentence, match.start(), match.group(0), page_subject=subject)


class ContextTests(unittest.TestCase):
    def test_negation_is_not_a_responsibility(self) -> None:
        self.assertEqual(classify("He did not call plays in 2019.", "A B")["disposition"], rs.NEGATED)

    def test_relinquishing_is_not_a_responsibility(self) -> None:
        self.assertEqual(classify("He relinquished play-calling duties in 2020.", "A B")["disposition"],
                         rs.RELINQUISHED)

    def test_an_announcement_is_future_not_realized(self) -> None:
        verdict = classify("The head coach announced that Smith would call the offensive plays in the bowl.",
                           "John Smith")
        self.assertEqual(verdict["disposition"], rs.FUTURE)

    def test_a_hypothetical_is_rejected(self) -> None:
        self.assertEqual(classify("He said he was considering calling plays himself.", "A B")["disposition"],
                         rs.HYPOTHETICAL)

    def test_an_opinion_is_not_an_assignment(self) -> None:
        self.assertEqual(classify("Fans criticized his conservative play-calling.", "A B")["disposition"],
                         rs.EVALUATIVE)
        self.assertEqual(classify("Writers questioned Jones's play-calling that season.", "Tom Jones")["disposition"],
                         rs.EVALUATIVE)

    def test_signals_and_players_are_another_sense(self) -> None:
        self.assertEqual(classify("Penn had decoded the play-calling signals.")["disposition"], rs.OTHER_SENSE)
        self.assertEqual(classify("As a high school quarterback he called plays on the field.", "A B")["disposition"],
                         rs.OTHER_SENSE)

    def test_a_professional_league_is_not_college(self) -> None:
        self.assertEqual(classify("He called plays for the Carolina Panthers in 1999.", "A B")["disposition"],
                         rs.NON_COLLEGE)

    def test_a_college_nickname_is_not_a_professional_club(self) -> None:
        verdict = classify("In Cignetti's first season as Pittsburgh's play caller, the Panthers averaged 32 points.",
                           "Frank Cignetti")
        self.assertNotEqual(verdict["disposition"], rs.NON_COLLEGE)

    def test_another_named_person_is_not_the_page_subject(self) -> None:
        verdict = classify("Bobo took over play calling responsibilities during the bowl game.", "Mark Richt")
        self.assertEqual(verdict["disposition"], rs.OTHER_PERSON)
        self.assertEqual(verdict["subject"], "Bobo")

    def test_an_explicit_statement_is_historical_never_current(self) -> None:
        verdict = classify("In 1982, head coach LaVell Edwards named Chow as principal offensive play-caller.",
                           "Norm Chow")
        self.assertEqual(verdict["disposition"], rs.HISTORICAL)
        self.assertNotIn(verdict["disposition"], rs.CURRENT_RESPONSIBILITY)
        self.assertEqual(verdict["years_as_written"], ["1982"])

    def test_no_person_is_unnamed(self) -> None:
        self.assertEqual(classify("The offensive coordinator took over play-calling duties in 2010.")["disposition"],
                         rs.UNNAMED)


class TitleTests(unittest.TestCase):
    def test_a_coordinator_title_is_never_play_calling(self) -> None:
        for title in ("Offensive Coordinator/Quarterbacks", "Defensive Coordinator", "Head Coach",
                      "Passing Game Coordinator", "Run Game Coordinator"):
            with self.subTest(title=title):
                self.assertEqual(rs.classify_title(title)[1], rs.TITLE_NOT_RESPONSIBILITY)

    def test_a_play_caller_title_is_the_only_current_form(self) -> None:
        code, disposition = rs.classify_title("Co-Defensive Coordinator / Play Caller")
        self.assertEqual((code, disposition), ("TITLE_STATES_PLAY_CALLER", rs.CURRENT_TITLE))
        self.assertEqual(rs.CURRENT_RESPONSIBILITY, frozenset({rs.CURRENT_TITLE}))

    def test_every_disposition_is_declared_once(self) -> None:
        self.assertEqual(len(rs.DISPOSITIONS), len(set(rs.DISPOSITIONS)))


class TextTests(unittest.TestCase):
    def test_wiki_markup_keeps_link_text_and_drops_references(self) -> None:
        plain = rs.wiki_plain("He joined [[Texas Longhorns football|Texas]].<ref>{{cite web|date=2020}}</ref> Next.")
        self.assertIn("He joined Texas.", plain)
        self.assertNotIn("cite web", plain)

    def test_a_sentence_is_cut_at_its_own_boundaries(self) -> None:
        text = "First sentence here. He called plays in 1990. Last one."
        sentence, offset = rs.sentence_at(text, text.index("called"), text.index("plays") + 5)
        self.assertEqual(sentence, "He called plays in 1990.")
        self.assertEqual(sentence[offset:offset + 6], "called")



class HeldOutMissTests(unittest.TestCase):
    """v37.2: the systematic misses the held-out sample exposed (W37R-33)."""

    def test_the_verb_form_of_the_mention_is_the_assignment(self) -> None:
        verdict = classify("Molnar then called the offensive plays and coached quarterbacks at Western Carolina in 1989.",
                           "Charley Molnar")
        self.assertEqual(verdict["disposition"], rs.HISTORICAL)

    def test_an_elided_subject_takes_the_sentence_subject(self) -> None:
        verdict = classify("In the 2007 season, he shared the defensive coordinator position with Larry Mac Duff, "
                           "but called the defensive plays.", "Duane Akina")
        self.assertEqual((verdict["disposition"], verdict["subject"]), (rs.HISTORICAL, "Duane Akina"))

    def test_the_subject_comes_from_the_mention_s_own_clause(self) -> None:
        verdict = classify("Defensive coordinator Jim Hilles took over as interim head coach, and Jackson was given "
                           "the added responsibility of being the lead coach on offense and play-caller for the "
                           "1986 season.", "Fred Jackson")
        self.assertEqual((verdict["disposition"], verdict["subject"]), (rs.HISTORICAL, "Fred Jackson"))

    def test_a_clause_subject_beats_a_name_after_the_mention(self) -> None:
        verdict = classify("Rosenbach was the quarterbacks coach and offensive play caller at Washington State "
                           "University from 2003 to 2007 under head coach Bill Doba.", "Timm Rosenbach")
        self.assertEqual(verdict["disposition"], rs.HISTORICAL)

    def test_a_removed_duty_belongs_to_its_receiver(self) -> None:
        sentence = ("Following defensive struggles in 2021, defensive coordinator Kerry Coombs was stripped of "
                    "defensive play calling duties, which were given to Barnes.")
        self.assertEqual(classify(sentence, "Matt Barnes")["disposition"], rs.HISTORICAL)
        other = classify(sentence, "Kerry Coombs")
        self.assertEqual((other["disposition"], other["subject"]), (rs.OTHER_PERSON, "Barnes"))

    def test_a_pro_team_in_a_lead_in_clause_does_not_make_the_main_clause_professional(self) -> None:
        verdict = classify("After being linked to the Tennessee Titans offensive coordinator position in January "
                           "2018, Day was promoted to offensive coordinator and primary play caller at Ohio State.",
                           "Ryan Day")
        self.assertEqual(verdict["disposition"], rs.HISTORICAL)
        pro = classify("Day was promoted to primary play caller for the Tennessee Titans.", "Ryan Day")
        self.assertEqual(pro["disposition"], rs.NON_COLLEGE)

    def test_an_announcement_of_a_realized_act_is_not_future(self) -> None:
        verdict = classify("Head coach Ryan Day announced that secondary coach Matt Barnes had called the defensive "
                           "plays that week, rather than Coombs.", "Kerry Coombs")
        self.assertEqual((verdict["disposition"], verdict["subject"]), (rs.OTHER_PERSON, "Matt Barnes"))
        future = classify("The head coach announced that Barnes would call the defensive plays.", "Kerry Coombs")
        self.assertEqual(future["disposition"], rs.FUTURE)

    def test_a_single_play_call_is_not_the_job(self) -> None:
        verdict = classify("In the post game interview, Dantonio was asked what the play call was.", None)
        self.assertEqual(verdict["disposition"], rs.OTHER_SENSE)

    def test_a_sentence_final_name_drops_its_full_stop(self) -> None:
        verdict = classify("Smith was removed from play-calling duties, which were handed to Jones.", "Bob Jones")
        self.assertEqual(verdict["subject"], "Bob Jones")


if __name__ == "__main__":
    unittest.main()
