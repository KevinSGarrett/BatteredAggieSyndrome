"""Play-calling responsibility statements, classified in their own sentence.

R37-06 successor to the Cycle 36 responsibility scan (MF36-06), which
admitted any text that matched a play-calling pattern. A pattern match is a
mention; whether it is a statement that a named person held the job depends
on the sentence around it:

* **negated** -- "did not call plays", "no longer the play-caller";
* **relinquished** -- "relinquished play-calling duties", "was stripped of";
* **hypothetical** -- "if he were to call plays", "could call plays";
* **future or announced** -- "will call the plays", "is expected to";
* **evaluative** -- "fans criticized his play-calling": it implies someone
  called plays, but it is an opinion about them, not an assignment;
* **another sense** -- "play-calling signals", a wristband system;
* **another league** -- a professional-football episode is not a college
  responsibility;
* **another person** -- "Malzahn's play-calling" on Chizik's page is about
  Malzahn;
* **unnamed** -- no person the statement can be attached to.

Only what survives all of that is an explicit statement, and an
encyclopedia narrative is still a *historical* episode with the years and
programs it names as written -- never a current responsibility. A current
responsibility needs an official staff title for that season.

A coordinator or head-coach title is never a play-calling statement.
Every rule is a declared list, every disposition is a declared enum, and
counts are taken over the enum, not over whatever strings appear.
"""

from __future__ import annotations

import html
import re
from typing import Any

RESPONSIBILITY_VERSION = "BAS-RESPONSIBILITY-CONTEXT-v37.2"
#: The v37.1 rules, named so a comparison can say which rules it measured.
PRIOR_RESPONSIBILITY_VERSION = "BAS-RESPONSIBILITY-CONTEXT-v37.1"
PREDECESSOR_VERSION = "BAS-RESPONSIBILITY-SCAN-v36.1"

# ------------------------------------------------------------ dispositions
CURRENT_TITLE = "ADMITTED_CURRENT_OFFICIAL_TITLE_STATEMENT"
HISTORICAL = "CANDIDATE_HISTORICAL_EXPLICIT_STATEMENT"
FUTURE = "CANDIDATE_FUTURE_OR_ANNOUNCED_NOT_REALIZED"
OTHER_PERSON = "CANDIDATE_STATEMENT_ABOUT_ANOTHER_PERSON"
NEGATED = "REJECTED_NEGATED"
RELINQUISHED = "REJECTED_RELINQUISHED_OR_REMOVED"
HYPOTHETICAL = "REJECTED_HYPOTHETICAL"
EVALUATIVE = "REJECTED_EVALUATIVE_MENTION_NOT_AN_ASSIGNMENT"
OTHER_SENSE = "REJECTED_NOT_A_RESPONSIBILITY_SENSE"
NON_COLLEGE = "REJECTED_NON_COLLEGE_CONTEXT"
TITLE_NOT_RESPONSIBILITY = "REJECTED_TITLE_IS_NOT_A_RESPONSIBILITY_STATEMENT"
UNNAMED = "RETAINED_UNNAMED_PERSON"
UNATTRIBUTABLE = "RETAINED_UNATTRIBUTABLE_NO_PROGRAM_BINDING"
MENTION_ONLY = "RETAINED_MENTION_WITHOUT_ASSIGNMENT_VERB"
TEXT_COPY = "RETAINED_TEXT_COPY_OF_A_TITLE_STATEMENT"

DISPOSITIONS = (CURRENT_TITLE, HISTORICAL, FUTURE, OTHER_PERSON, NEGATED, RELINQUISHED, HYPOTHETICAL,
                EVALUATIVE, OTHER_SENSE, NON_COLLEGE, TITLE_NOT_RESPONSIBILITY, UNNAMED, UNATTRIBUTABLE,
                MENTION_ONLY, TEXT_COPY)
#: Only this disposition is a current responsibility. Everything else is
#: evidence about a source, kept and counted, never promoted.
CURRENT_RESPONSIBILITY = frozenset({CURRENT_TITLE})

MENTION = re.compile(
    r"play[\s-]*call(?:er|ers|ing)?\b|\bcall(?:s|ed|ing)?\s+(?:the\s+)?(?:offensive\s+|defensive\s+)?plays\b",
    re.I,
)
TITLE_PLAY_CALLER = re.compile(r"\bplay[\s-]*caller\b", re.I)
TITLE_NOT_PLAY_CALLING = (
    (re.compile(r"\bpass(?:ing)?[\s-]*game\s+coordinator\b", re.I), "PASS_GAME_COORDINATOR_IS_NOT_PLAY_CALLING"),
    (re.compile(r"\brun(?:ning)?[\s-]*game\s+coordinator\b", re.I), "RUN_GAME_COORDINATOR_IS_NOT_PLAY_CALLING"),
    (re.compile(r"\b(?:offensive|defensive|special\s+teams)\s+coordinator\b", re.I), "COORDINATOR_TITLE_IS_NOT_PLAY_CALLING"),
    (re.compile(r"\bhead\s+coach\b", re.I), "HEAD_COACH_TITLE_IS_NOT_PLAY_CALLING"),
)

NEGATION = re.compile(r"\b(?:not|never|no\s+longer|without|nor|neither)\b|n't\b", re.I)
RELINQUISH = re.compile(r"\b(?:relinquish\w*|gave\s+up|give\s+up|handed\s+(?:over|off)|stripped|removed\s+from|"
                        r"took\s+(?:away|over)\s+.{0,40}\bfrom\b|lost\s+(?:his|the)\s+play)", re.I)
HYPOTHETICAL_CUE = re.compile(r"\b(?:if|could|might|should|whether|rumou?r\w*|speculat\w*|consider(?:ing|ed)|"
                              r"possibly|perhaps)\b", re.I)
FUTURE_CUE = re.compile(r"\b(?:will|would|is\s+expected|was\s+expected|is\s+set\s+to|was\s+set\s+to|plans?\s+to|"
                        r"going\s+to|announced\s+that)\b", re.I)
EVALUATIVE_CUE = re.compile(r"\b(?:criticiz\w*|criticis\w*|critic\w*|prais\w*|question(?:ed|able)|scrutiny|blam\w*|"
                            r"credit\w*|innovative|lauded|poor|conservative|aggressive|creative|genius|"
                            r"controversial|struggl\w*|fans|writers|media)\b", re.I)
#: Senses in which "calling plays" is not a coach's job: signals, a player
#: at the line or in the huddle, fans on a participation platform.
OTHER_SENSE_CUE = re.compile(r"play[\s-]*call(?:ing)?\s+(?:signals?|system|sheet|wristband|headset|clock|"
                             r"terminology|codes?)|decoded|\bfans?\b|\bhigh\s+school\b|\bcaptain\b|"
                             r"\bfrom\s+his\s+position\b|\bquarterback\b(?!s?\s+coach)", re.I)
#: Professional context from league words or "City Nickname" pairs only. A bare
#: nickname is not enough: Pittsburgh's college team is also the Panthers.
NON_COLLEGE_CUE = re.compile(
    r"\b(?:NFL|AFL|CFL|XFL|USFL|UFL|AAF|Super\s+Bowl|Pro\s+Bowl|Canadian\s+Football\s+League|"
    r"Pittsburgh\s+Steelers|Atlanta\s+Falcons|San\s+Francisco\s+49ers|New\s+England\s+Patriots|"
    r"Dallas\s+Cowboys|Green\s+Bay\s+Packers|Chicago\s+Bears|New\s+York\s+(?:Giants|Jets)|"
    r"Philadelphia\s+Eagles|Washington\s+(?:Redskins|Commanders)|(?:Oakland|Las\s+Vegas)\s+Raiders|"
    r"(?:San\s+Diego|Los\s+Angeles)\s+(?:Chargers|Rams)|Denver\s+Broncos|Kansas\s+City\s+Chiefs|"
    r"(?:Baltimore|Indianapolis)\s+Colts|Tennessee\s+Titans|Houston\s+(?:Texans|Oilers)|"
    r"Jacksonville\s+Jaguars|Miami\s+Dolphins|Buffalo\s+Bills|Baltimore\s+Ravens|Cincinnati\s+Bengals|"
    r"Cleveland\s+Browns|Detroit\s+Lions|Minnesota\s+Vikings|New\s+Orleans\s+Saints|"
    r"Tampa\s+Bay\s+Buccaneers|Carolina\s+Panthers|Seattle\s+Seahawks|(?:Arizona|St\.\s+Louis|Phoenix)\s+Cardinals|"
    r"Toronto\s+Argonauts|Winnipeg\s+Blue\s+Bombers|Atlanta\s+Legends|"
    # Bare nicknames only where no college football program uses the name.
    r"Steelers|Packers|Chiefs|Colts|Ravens)\b")
ASSIGNMENT_VERB = re.compile(r"\b(?:call(?:s|ed|ing)?|took\s+over|take\s+over|handl(?:e|ed|es|ing)|assum(?:e|ed|es)|"
                             r"given|gave|named|served|serve|was|is|as|duties|responsibilit(?:y|ies)|responsible|control|"
                             r"shar(?:e|ed|es|ing)|undert(?:ook|ake)|added|being|became|become|primary|principal|"
                             r"designated)\b", re.I)
YEAR = re.compile(r"\b(19[0-9]{2}|20[0-2][0-9])\b")
POSSESSIVE_SUBJECT = re.compile(r"([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,3})['’]s\s+(?:\w+\s+){0,2}play[\s-]*call")
ACTIVE_SUBJECT = re.compile(r"([A-Z][\w.'-]+(?:\s+(?:[A-Z][\w.'-]+|Jr\.|Sr\.|II|III)){0,3})\s+"
                            r"(?:(?:would|will|also|had|has|then|later|still|already|since|be|continued\s+to\s+be)\s+){0,3}"
                            r"(?:call(?:ed|s|ing)?|took\s+over|taken\s+over|handled|assumed|shar(?:ed|ing)|undertook|added|"
                            r"(?:was|is|be|became)\s+(?:the\s+)?(?:\w+\s+){0,2}play|responsible)")
APPOSITIVE_AFTER = re.compile(r"^[^.;]{0,80}?\b(?:coach|coordinator)\s+([A-Z][a-z]+(?:\s+[A-Z][\w.'-]+){1,2})")
PRONOUN_START = re.compile(r"^\s*(?:He|His|Him)\b")
#: v37.2. A clause's own grammatical subject: a name, or "he", at the start
#: of the clause (after an optional lead-in such as "In 1996,") followed by a
#: verb. On held-out text the subject of the mention's clause was passed over
#: for a name in another clause.
LEAD_IN = (r"(?:(?:In|During|From|After|Before|For|Following|By|At|Under|Despite|Although|While|When)\b"
           r"[^,;]{0,120},\s*)?")
CLAUSE_SUBJECT = re.compile(
    r"^\s*" + LEAD_IN + r"([A-Z][\w.'-]+(?:\s+(?:[A-Z][\w.'-]+|Jr\.|Sr\.|II|III)){0,2}|he|He)\s+"
    r"(?:(?:then|also|later|already|again|still|had|has|would)\s+){0,2}"
    r"(?:was|were|is|became|served|called|calls|took|had|has|handled|assumed|shared|spent|remained|returned|"
    r"continued|added|coached)\b")
#: Coordinating boundaries that open a clause with its own subject.
CLAUSE_BOUNDARY = re.compile(r",\s+(?:and|but|while|whereas)\s+|;\s+|\s+but\s+")
#: v37.2. A duty removed from one person and given to another: the receiver
#: holds it. "... was stripped of play-calling duties, which were given to Barnes."
TRANSFER_TO = re.compile(r"\b(?:given|handed|transferred|passed|assigned)\s+(?:over\s+)?to\s+"
                         r"([A-Z][\w.'-]+(?:\s+[A-Z][\w.'-]+){0,2})")
#: v37.2. A lead-in subordinate clause whose context does not carry into the
#: main clause: "After being linked to the Tennessee Titans ..., Day was
#: promoted to ... play caller at Ohio State."
SUBORDINATE_LEAD_IN = re.compile(r"^\s*(?:After|Before|Despite|Although|Following|Having|While|When)\b[^;]*?,\s")
#: v37.2. The verb form of the mention is itself the assignment verb.
VERB_FORM_MENTION = re.compile(r"^call(?:s|ed|ing)?\b", re.I)
#: v37.2. "The play call was ...", "his most notable play-call": one called
#: play, not the job of calling them.
SINGLE_PLAY_CALL = re.compile(r"^play[\s-]*call$", re.I)
#: A future cue does not make a realized past act future: "announced that
#: Barnes had called the defensive plays".
FUTURE_MODAL = re.compile(r"\b(?:will|would|shall|is\s+to|was\s+to|to\s+be|be\s+taking|expected|set\s+to|"
                          r"plans?\s+to|going\s+to|remain)\b", re.I)
STOPWORDS = {"The", "In", "On", "After", "During", "Under", "When", "With", "As", "At", "For", "His", "He",
             "Head", "Coach", "Offensive", "Defensive", "Coordinator", "January", "February", "March", "April",
             "May", "June", "July", "August", "September", "October", "November", "December", "Before", "Since"}


# ----------------------------------------------------------------- text
def wiki_plain(wikitext: str) -> str:
    """Encyclopedia source text as plain sentences, link text kept."""

    text = re.sub(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", " ", wikitext, flags=re.S | re.I)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    for _ in range(3):
        text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"'''?", "", text)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"[ \t]+", " ", text))


def html_rendered(raw: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|template)\b.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<!--.*?-->", " ", text)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))


def sentence_at(text: str, start: int, end: int) -> tuple[str, int]:
    """The sentence containing [start, end), and the match offset inside it."""

    left = max(text.rfind(". ", 0, start), text.rfind("\n", 0, start), text.rfind("? ", 0, start),
               text.rfind("! ", 0, start))
    left = 0 if left < 0 else left + 1
    candidates = [i for i in (text.find(". ", end), text.find("\n", end), text.find("? ", end)) if i >= 0]
    right = min(candidates) + 1 if candidates else len(text)
    sentence = text[left:right]
    stripped = sentence.lstrip()
    return stripped.strip(), start - left - (len(sentence) - len(stripped))


def surname(name: str | None) -> str | None:
    if not name:
        return None
    parts = [p for p in re.split(r"\s+", re.sub(r"\(.*?\)", "", name)) if p and p not in ("Jr.", "Sr.", "II", "III", "IV")]
    return parts[-1].casefold() if parts else None


def clause_start(sentence: str, offset: int) -> int:
    """Where the clause holding the mention begins (v37.2)."""

    start = 0
    for boundary in CLAUSE_BOUNDARY.finditer(sentence[:offset]):
        start = boundary.end()
    return start


def _named(name: str, page_subject: str | None) -> tuple[str | None, str]:
    # A sentence-final name carries the full stop ("given to Barnes."); a
    # generational suffix keeps its own.
    if not re.search(r"\b(?:Jr|Sr)\.$", name):
        name = name.rstrip(".,;:")
    if name.casefold() == "he":
        if page_subject:
            return page_subject, "PAGE_SUBJECT_BY_CLAUSE_PRONOUN"
        return None, "PRONOUN_WITHOUT_PAGE_SUBJECT"
    if page_subject and surname(name) == surname(page_subject):
        return page_subject, "NAMED_PAGE_SUBJECT"
    return name, "NAMED_OTHER_PERSON"


def subject_of(sentence: str, offset: int, page_subject: str | None) -> tuple[str | None, str]:
    """Who the statement is about, and how that was decided.

    v37.2: the active-subject search is confined to the mention's own clause,
    and the clause's grammatical subject (then the sentence's) is tried
    before a name that merely follows the mention.
    """

    before = sentence[:offset + 40]
    match = None
    for found in POSSESSIVE_SUBJECT.finditer(before):
        match = found
    start = clause_start(sentence, offset)
    if match is None:
        for found in ACTIVE_SUBJECT.finditer(sentence[start:offset + 40]):
            match = found
    if match:
        name = " ".join(w for w in match.group(1).split() if w not in STOPWORDS).strip()
        if name:
            return _named(name, page_subject)
    for scope in (sentence[start:], sentence):
        grammatical = CLAUSE_SUBJECT.match(scope)
        if grammatical:
            name = " ".join(w for w in grammatical.group(1).split() if w not in STOPWORDS).strip()
            if name:
                return _named(name, page_subject)
    after = APPOSITIVE_AFTER.search(sentence[offset:])
    if after:
        name = after.group(1)
        if page_subject and surname(name) == surname(page_subject):
            return page_subject, "NAMED_PAGE_SUBJECT"
        return name, "NAMED_OTHER_PERSON"
    if page_subject:
        if surname(page_subject) and surname(page_subject) in sentence.casefold():
            return page_subject, "PAGE_SUBJECT_NAMED_IN_SENTENCE"
        if PRONOUN_START.search(sentence):
            return page_subject, "PAGE_SUBJECT_BY_LEADING_PRONOUN"
    return None, "NO_PERSON_IN_SENTENCE"


def classify_sentence(sentence: str, offset: int, match_text: str, *, page_subject: str | None) -> dict[str, Any]:
    """The disposition of one mention in its sentence, with the reasons."""

    clause_start = max(sentence.rfind(",", 0, offset), sentence.rfind(";", 0, offset),
                       sentence.rfind(" but ", 0, offset), -1) + 1
    clause = sentence[clause_start: offset + len(match_text) + 30]
    near_before = sentence[max(clause_start, offset - 60): offset]
    reasons = []
    subject, subject_basis = subject_of(sentence, offset, page_subject)
    years = sorted(set(YEAR.findall(sentence)))

    def done(disposition: str) -> dict[str, Any]:
        return {"disposition": disposition, "reasons": reasons, "subject": subject,
                "subject_basis": subject_basis, "years_as_written": years}

    if OTHER_SENSE_CUE.search(sentence[max(0, offset - 20): offset + len(match_text) + 30]):
        reasons.append("play-calling in another sense (signals, system)")
        return done(OTHER_SENSE)
    lead_in = SUBORDINATE_LEAD_IN.match(sentence)
    pro_scope = sentence[lead_in.end():] if lead_in and lead_in.end() <= offset else sentence
    if NON_COLLEGE_CUE.search(pro_scope):
        reasons.append("professional-football context")
        return done(NON_COLLEGE)
    if SINGLE_PLAY_CALL.match(match_text):
        reasons.append("a single called play, not the job of calling plays")
        return done(OTHER_SENSE)
    if RELINQUISH.search(clause) or RELINQUISH.search(near_before):
        receiver = TRANSFER_TO.search(sentence[offset:])
        if receiver:
            subject, subject_basis = _named(receiver.group(1), page_subject)
            reasons.append("removed from one person and given to another: the receiver holds it")
            return done(HISTORICAL if subject_basis == "NAMED_PAGE_SUBJECT" else OTHER_PERSON)
        reasons.append("relinquished or removed")
        return done(RELINQUISHED)
    if NEGATION.search(near_before):
        reasons.append("negated in its clause")
        return done(NEGATED)
    if HYPOTHETICAL_CUE.search(near_before):
        reasons.append("hypothetical")
        return done(HYPOTHETICAL)
    window_start = max(0, offset - 120)
    future = None
    for found in FUTURE_CUE.finditer(sentence[window_start:offset]):
        future = found
    if future:
        between = sentence[window_start + future.end(): offset]
        realized = (future.group(0).casefold().startswith("announced")
                    and not FUTURE_MODAL.search(between)
                    and bool(re.search(r"\bhad\s+$", between) or match_text.casefold().startswith("called")))
        if not realized:
            reasons.append("future or announced, not realized")
            return done(FUTURE if subject else UNNAMED)
        reasons.append("an announcement of a realized past act, not a future one")
    if EVALUATIVE_CUE.search(sentence):
        reasons.append("an opinion about play-calling, not an assignment")
        return done(EVALUATIVE)
    around = sentence[max(0, offset - 50): offset] + " " + sentence[offset + len(match_text): offset + len(match_text) + 50]
    possessive = POSSESSIVE_SUBJECT.search(sentence[:offset + len(match_text) + 5]) is not None
    if not ASSIGNMENT_VERB.search(around) and not possessive and not VERB_FORM_MENTION.search(match_text):
        reasons.append("no assignment verb around the mention")
        return done(MENTION_ONLY)
    if subject is None:
        reasons.append("no person the statement can be attached to")
        return done(UNNAMED)
    if subject_basis == "NAMED_OTHER_PERSON":
        reasons.append("the statement names someone other than the page subject")
        return done(OTHER_PERSON)
    reasons.append("explicit statement in a narrative source: a historical episode, never current")
    return done(HISTORICAL)


def classify_title(title: str) -> tuple[str | None, str | None]:
    """A staff title: an explicit play-caller title, a title that is not one, or neither."""

    if TITLE_PLAY_CALLER.search(title or ""):
        return "TITLE_STATES_PLAY_CALLER", CURRENT_TITLE
    for pattern, code in TITLE_NOT_PLAY_CALLING:
        if pattern.search(title or ""):
            return code, TITLE_NOT_RESPONSIBILITY
    return None, None
