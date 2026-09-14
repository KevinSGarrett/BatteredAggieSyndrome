"""Versioned coach role taxonomy and lossless title qualification.

A wide HC/OC/DC table is a presentation pivot, not the storage model.
Assistant OC is not principal OC. Support titles mentioning head coach
are not HC. Broad DB is not automatically CB and S.
"""

from __future__ import annotations

import csv
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Sequence

TAXONOMY_VERSION = "BAS-COACH-ROLE-TAXONOMY-2026-09-14-v1"
PACK_TAXONOMY = Path(
    r"C:\BatteredAggieSyndrome.data\ops\cycle33\COACH_ROLE_TAXONOMY.csv"
)

ROLE_HC = "head_coach"
ROLE_OC = "offensive_coordinator"
ROLE_DC = "defensive_coordinator"

QUALIFIER_CO = "CO"
QUALIFIER_INTERIM = "INTERIM"
QUALIFIER_ACTING = "ACTING"
QUALIFIER_ASSISTANT = "ASSISTANT"
QUALIFIER_ASSOCIATE = "ASSOCIATE"
QUALIFIER_DEPUTY = "DEPUTY"
QUALIFIER_SENIOR = "SENIOR"
QUALIFIER_VOLUNTEER = "VOLUNTEER"
QUALIFIER_GRADUATE = "GRADUATE"
QUALIFIER_STUDENT = "STUDENT"

_ASSISTANT_TO = re.compile(
    r"\b(?:special\s+)?(?:assistant|aide|analyst|executive assistant)\s+"
    r"to(?:\s+the)?\s+",
    re.I,
)
_ASSISTANT_OC = re.compile(
    r"\b(?:assistant|associate|assoc\.|asst\.?)\s+(?:offensive\s+coordinator|\boc\b)",
    re.I,
)
_ASSISTANT_DC = re.compile(
    r"\b(?:assistant|associate|assoc\.|asst\.?)\s+(?:defensive\s+coordinator|\bdc\b)",
    re.I,
)
_CO_OC = re.compile(r"\bco[\s-]*offensive\s+coordinator\b|\bco[\s-]*oc\b", re.I)
_CO_DC = re.compile(r"\bco[\s-]*defensive\s+coordinator\b|\bco[\s-]*dc\b", re.I)
_OC = re.compile(r"\boffensive coordinator\b|\boff\.?\s*coor(?:dinator)?\.?", re.I)
_DC = re.compile(r"\bdefensive coordinator\b|\bdef\.?\s*coor(?:dinator)?\.?", re.I)
_SLASH_OC = re.compile(r"(?:^|[\s/])oc(?:[\s/]|$)", re.I)
_SLASH_DC = re.compile(r"(?:^|[\s/])dc(?:[\s/]|$)", re.I)
_HC = re.compile(
    r"\bhead(?:\s+football)?\s+coach\b|\bendowed football coach\b|"
    r"\bchair in football\s*$|\bdirector of football\s*$",
    re.I,
)
_NOT_HC = re.compile(
    r"""
    \b(?:deputy|associate|assoc\.|assistant|asst\.?).{0,24}
        \bhead(?:\s+football)?\s+coach\b
    |\bhead(?:\s+football)?\s+coach\s+(?:of|for)\s+
        (?:the\s+)?(?:offense|defence|defense|special\s+teams)\b
    |\b(?:director|coordinator|consultant|advisor|adviser|aide)\b.{0,48}
        \bhead(?:\s+football)?\s+coach
    |\b(?:to|for|of)(?:\s+the)?\s+head(?:\s+football)?\s+coach\b
    |\bhead(?:\s+football)?\s+coach\s+(?:analyst|operations|assistant|support)\b
    |\b(?:sports\s+performance|strength(?:\s+and\s+conditioning)?|track\s+and\s+field)\b
    |\bhead\s+strength\b
    |\bhead-coach\s+analyst\b
    """,
    re.I | re.X,
)
_DIRECTOR_OFFENSE = re.compile(
    r"\bdirector of offense\b(?!\s+(?:recruiting|personnel|operations|scouting|quality|player))",
    re.I,
)
_DIRECTOR_DEFENSE = re.compile(
    r"\bdirector of defen[cs]e\b(?!\s+(?:recruiting|personnel|operations|scouting|quality|player))",
    re.I,
)
_ASSISTANT_DIRECTOR = re.compile(
    r"\b(?:assistant|associate|assoc\.|asst\.?|deputy)\s+director of (?:offense|defen[cs]e)\b",
    re.I,
)

POSITION_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (r"\bspecial teams coordinator\b", "special_teams_coordinator", "SPECIAL_TEAMS"),
    (r"\bquarterbacks?\b|(?:^|[/,(])\s*qb(?:\b|/)", "quarterbacks", "OFFENSE"),
    (r"\brunning backs?\b|(?:^|[/,(])\s*rb(?:\b|/)", "running_backs", "OFFENSE"),
    (r"\bhalfbacks?\b|(?:^|[/,(])\s*hb(?:\b|/)", "halfbacks", "OFFENSE"),
    (r"\bfullbacks?\b|(?:^|[/,(])\s*fb(?:\b|/)", "fullbacks", "OFFENSE"),
    (r"\bwide receivers?\b|(?:^|[/,(])\s*wr(?:\b|/)", "wide_receivers", "OFFENSE"),
    (r"\btight ends?\b|(?:^|[/,(])\s*te(?:\b|/)", "tight_ends", "OFFENSE"),
    (r"\boffensive linem(?:an|en)\b|\boffensive line\b", "offensive_line", "OFFENSE"),
    (r"\bdefensive linem(?:an|en)\b|\bdefensive line\b", "defensive_line", "DEFENSE"),
    (r"\bdefensive ends?\b|(?:^|[/,(])\s*de(?:\b|/)", "defensive_ends", "DEFENSE"),
    (
        r"\bdefensive tackles?\b|(?:^|[/,(])\s*dt(?:\b|/)",
        "defensive_tackles",
        "DEFENSE",
    ),
    (r"\bedge\b", "edge", "DEFENSE"),
    (r"\binside linebackers?\b|\bilb\b", "inside_linebackers", "DEFENSE"),
    (r"\boutside linebackers?\b|\bolb\b", "outside_linebackers", "DEFENSE"),
    (r"\blinebackers?\b", "linebackers", "DEFENSE"),
    (r"\bdefensive backs?\b|(?:^|[/,(])\s*db(?:\b|/)", "defensive_backs", "DEFENSE"),
    (r"\bcornerbacks?\b|(?:^|[/,(])\s*cb(?:\b|/)", "cornerbacks", "DEFENSE"),
    (r"\bsafeties\b|\bsafety\b", "safeties", "DEFENSE"),
    (r"\bnickels?\b", "nickels", "DEFENSE"),
    (r"\b(?:kickers?|punters?)\b", "kickers_punters", "SPECIAL_TEAMS"),
    (r"\bstrength\b|\bconditioning\b", "strength_conditioning", "TEAM"),
    (r"\bgeneral manager\b|\b\bgm\b", "general_manager", "TEAM"),
    (r"\bplayer personnel\b|\brecruiting coordinator\b", "player_personnel", "TEAM"),
    (r"\banalyst\b", "analyst", "UNKNOWN"),
    (r"\bquality control\b", "quality_control", "UNKNOWN"),
    (r"\bgraduate assistant\b", "graduate_assistant", "UNKNOWN"),
    (r"\bstudent assistant\b", "student_assistant", "UNKNOWN"),
    (r"\bchief of staff\b", "chief_of_staff", "TEAM"),
    (r"\brun game coordinator\b", "run_game_coordinator", "UNKNOWN"),
    (r"\bpass game coordinator\b", "pass_game_coordinator", "UNKNOWN"),
    (r"\bfootball operations\b", "football_operations", "TEAM"),
    (r"\bathletic director\b|\bdirector of athletics\b", "athletic_director", "TEAM"),
    (
        r"\bathletic trainers?\b|\btraining staff\b|\bsports medicine\b",
        "training_staff",
        "TEAM",
    ),
    (r"\bnutrition\b|\bsports diet", "nutrition_staff", "TEAM"),
    (r"\bequipment\b", "equipment_staff", "TEAM"),
    (r"\bvideo\b|\btechnology coordinator\b", "video_technology_staff", "TEAM"),
    (r"\bsports science\b|\bsports performance\b", "sports_science", "TEAM"),
    (r"\brecruiting\b", "recruiting_staff", "TEAM"),
    (r"\bplayer development\b|\bplayer relations\b", "player_development", "TEAM"),
    (
        r"\bcreative\b|\bcommunications\b|\bmedia relations\b",
        "communications_staff",
        "TEAM",
    ),
    (
        r"\badministrative assistant\b|\bdirector of administration\b",
        "administrative_staff",
        "TEAM",
    ),
    (r"\bintern\b", "intern_or_student_assistant", "UNKNOWN"),
    (r"\bconsultant\b|\badvisor\b|\badviser\b", "consultant", "UNKNOWN"),
    (
        r"\bassistant coach\b|\boffensive assistant\b|\bdefensive assistant\b",
        "assistant_unspecified",
        "UNKNOWN",
    ),
    (r"\bspecial teams\b", "special_teams_staff", "SPECIAL_TEAMS"),
    (r"\bsecondary\b", "secondary", "DEFENSE"),
    (r"\binside receivers?\b|\boutside receivers?\b", "receivers", "OFFENSE"),
    (
        r"\bfootball performance\b|\bathletic performance\b",
        "sports_performance",
        "TEAM",
    ),
    (r"\bstudent manager\b", "student_assistant", "UNKNOWN"),
    (r"\bscouting\b", "player_personnel", "TEAM"),
    (r"\bfaculty liaison\b", "administrative_staff", "TEAM"),
    (
        r"\bdirector of operations\b|\bassistant director of operations\b",
        "football_operations",
        "TEAM",
    ),
    (r"\bassistant football coach\b", "assistant_unspecified", "UNKNOWN"),
    (
        r"\bposition assistant\b|\bcoaching assistant\b",
        "assistant_unspecified",
        "UNKNOWN",
    ),
    (r"\bprogram assistant\b", "football_operations", "TEAM"),
    (
        r"\bfootball technology\b|\bdirector of (?:football )?technology\b",
        "video_technology_staff",
        "TEAM",
    ),
    (r"\bphysician\b|\bsports medicine\b|\bmedical staff\b", "medical_staff", "TEAM"),
    (r"\bnickelbacks?\b", "nickels", "DEFENSE"),
    (r"\bspecialists?\b", "specialists", "SPECIAL_TEAMS"),
    (r"\bcorners?\b", "cornerbacks", "DEFENSE"),
    (r"\bpsycholog", "sports_psychology", "TEAM"),
    (r"\bfootball relations\b|\bhigh school relations\b", "recruiting_staff", "TEAM"),
    (r"\brehabilitation\b|\brehab\b", "training_staff", "TEAM"),
    (r"\bdietitian\b|\bdietician\b", "nutrition_staff", "TEAM"),
    (r"\bstudent coach\b|\bstudent team manager\b", "student_assistant", "UNKNOWN"),
    (r"\bfaculty mentor\b|\bfaculty liaison\b", "administrative_staff", "TEAM"),
    (r"\bacademic\b", "academic_staff", "TEAM"),
    (
        r"\bcoordinator of operations\b|\boperations assistant\b",
        "football_operations",
        "TEAM",
    ),
    (r"\brush ends?\b", "edge", "DEFENSE"),
    (r"\bedges?\b", "edge", "DEFENSE"),
    (r"\breceivers?\b", "receivers", "OFFENSE"),
    (r"\brevenue sharing\b", "football_operations", "TEAM"),
    (r"\bsecretary\b|\bexecutive secretary\b", "administrative_staff", "TEAM"),
    (r"(?:^|[\s|/])te(?:\b|/)", "tight_ends", "OFFENSE"),
    (r"\bgradute assistant\b|\bgraduate assistant\b", "graduate_assistant", "UNKNOWN"),
    (
        r"\bdirector of development\b|\bfootball director of development\b",
        "development_staff",
        "TEAM",
    ),
    (
        r"\badministration coordinator\b|\bfootball administration\b",
        "administrative_staff",
        "TEAM",
    ),
    (r"\bchaplain\b", "chaplain", "TEAM"),
    (r"\bfootball research\b", "analyst", "UNKNOWN"),
    (r"\bsport performance\b|\bsports performance\b", "sports_performance", "TEAM"),
    (r"\bsport science\b|\bsports science\b", "sports_science", "TEAM"),
    (r"\bathletic training\b", "training_staff", "TEAM"),
    (r"\bpersonnel assistant\b", "player_personnel", "TEAM"),
    (r"\banalytic", "analyst", "UNKNOWN"),
    (r"\bsnipers?\b", "nickels", "DEFENSE"),
    (r"\bcompliance\b", "administrative_staff", "TEAM"),
    (r"\bnil\b", "football_operations", "TEAM"),
    (r"\bqc\b|\bquality control\b", "quality_control", "UNKNOWN"),
    (r"\blife coach\b|\bminister of culture\b", "player_development", "TEAM"),
    (r"\bfaculty fellow\b", "administrative_staff", "TEAM"),
    (
        r"\bdefenisve assistant\b|\bassistant-\s*defense\b",
        "assistant_unspecified",
        "DEFENSE",
    ),
    (r"\bpeak performance\b|\bmental performance\b", "sports_performance", "TEAM"),
    (r"\bdigital strategy\b|\bmedia services\b", "communications_staff", "TEAM"),
    (r"\bexecutive assistant\b", "administrative_staff", "TEAM"),
    (r"\bstudent-athlete\b|\bstudent athlete\b", "player_development", "TEAM"),
    (r"\bnicklebacks?\b", "nickels", "DEFENSE"),
    (r"\bdbs?\b", "defensive_backs", "DEFENSE"),
    (
        r"\bpass(?:ing)?\s+game coordinator\b|\bpassing game coordinator\b",
        "pass_game_coordinator",
        "OFFENSE",
    ),
    (r"\b(?:offensive|defensive)\s+ga\b|\bga\b", "graduate_assistant", "UNKNOWN"),
    (r"\bspecial teams? coordinator\b", "special_teams_coordinator", "SPECIAL_TEAMS"),
    (r"\bwide recievers?\b", "wide_receivers", "OFFENSE"),
    (r"\bgeneral manger\b|\bassistant general manger\b", "general_manager", "TEAM"),
    (r"\bplayer personal\b", "player_personnel", "TEAM"),
    (r"\bslot backs?\b", "slot_backs", "OFFENSE"),
    (r"\bstars?\b", "stars", "DEFENSE"),
    (r"\bbandits?\b", "bandits", "DEFENSE"),
    (r"\bsnipes\b", "nickels", "DEFENSE"),
    (r"\bspears\b", "spears", "UNKNOWN"),
    (r"\bassistant backfield\b|\bbackfield\b", "running_backs", "OFFENSE"),
    (r"\bvolunteer coach\b", "volunteer_coach", "UNKNOWN"),
    (r"\bchief medical officer\b|\bsport medicine\b", "medical_staff", "TEAM"),
    (
        r"\bgraphic design\b|\bphotography\b|\bfootball design\b|\bcoordinator of design\b",
        "communications_staff",
        "TEAM",
    ),
    (
        r"\bdigital media\b|\bsocial media\b|\bsports information\b|\bmarketing\b|\bfan engagement\b",
        "communications_staff",
        "TEAM",
    ),
    (
        r"\balumni relations\b|\balumni coordinator\b|\bcommunity relations\b|\bcommunity engagement\b|\bfamily relations\b",
        "player_development",
        "TEAM",
    ),
    (
        r"\bfootball office\b|\bfootball ops\b|\bplayer operations\b|\bgame management\b|\broster and game\b|\bexecutive operations\b",
        "football_operations",
        "TEAM",
    ),
    (
        r"\bfootball strategy\b|\bstrategic initiatives\b|\bstrategic intelligence\b|\bassistant ad for football\b|\bsport administrator\b|\bprimary sport administrator\b",
        "football_operations",
        "TEAM",
    ),
    (
        r"\bfootball development\b|\bprogram development\b|\bplayer administration\b|\boffice administration\b|\boffice associate\b|\badministrative support\b",
        "administrative_staff",
        "TEAM",
    ),
    (
        r"\bspeed development\b|\bhuman performance\b|\bperformance science\b|\bperformance assistant\b|\bsport scientist\b",
        "sports_performance",
        "TEAM",
    ),
    (
        r"\bmental health\b|\bathlete support\b|\bstudent success\b|\bfootball engagement\b|\bfootball academics\b|\bfreshman transition\b",
        "academic_staff",
        "TEAM",
    ),
    (
        r"\bproduction assistant\b|\bmedia\b|\bfinance and administration\b|\bstrategy and finance\b|\bspecial assistant to the ad\b",
        "administrative_staff",
        "TEAM",
    ),
    (
        r"\bpitching\b|\bequestrian\b|\bbarn manager\b|\bjumping seat\b",
        "other_sport_not_football",
        "UNKNOWN",
    ),
    (r"\bacademics?\b", "academic_staff", "TEAM"),
    (
        r"\binternal operations\b|\bfootball administrator\b",
        "football_operations",
        "TEAM",
    ),
    (r"\bassistant director,\s*operations\b", "football_operations", "TEAM"),
)


def _norm(title: str) -> str:
    return re.sub(r"\s+", " ", str(title or "")).strip()


def extract_qualifiers(title: str) -> tuple[str, ...]:
    lowered = _norm(title).casefold()
    found: list[str] = []
    if re.search(r"\bco-", lowered) or re.search(
        r"\bco\s+(?:offensive|defensive)", lowered
    ):
        found.append(QUALIFIER_CO)
    if "interim" in lowered:
        found.append(QUALIFIER_INTERIM)
    if "acting" in lowered:
        found.append(QUALIFIER_ACTING)
    if "deputy" in lowered:
        found.append(QUALIFIER_DEPUTY)
    if re.search(r"\bassociate\b|\bassoc\.", lowered):
        found.append(QUALIFIER_ASSOCIATE)
    if (
        re.search(r"\bassistant\b|\basst\.", lowered)
        and QUALIFIER_ASSOCIATE not in found
    ):
        found.append(QUALIFIER_ASSISTANT)
    if "senior" in lowered:
        found.append(QUALIFIER_SENIOR)
    if "volunteer" in lowered:
        found.append(QUALIFIER_VOLUNTEER)
    if "graduate" in lowered:
        found.append(QUALIFIER_GRADUATE)
    if "student" in lowered:
        found.append(QUALIFIER_STUDENT)
    return tuple(dict.fromkeys(found))


def _principal_oc(title: str) -> bool:
    lowered = _norm(title)
    if _ASSISTANT_TO.search(lowered):
        return False
    if _ASSISTANT_OC.search(lowered) and not _CO_OC.search(lowered):
        return False
    if _ASSISTANT_DIRECTOR.search(lowered) and _DIRECTOR_OFFENSE.search(lowered):
        return False
    return bool(
        _CO_OC.search(lowered)
        or _OC.search(lowered)
        or _DIRECTOR_OFFENSE.search(lowered)
        or _SLASH_OC.search(lowered)
    )


def _principal_dc(title: str) -> bool:
    lowered = _norm(title)
    if _ASSISTANT_TO.search(lowered):
        return False
    if _ASSISTANT_DC.search(lowered) and not _CO_DC.search(lowered):
        return False
    if _ASSISTANT_DIRECTOR.search(lowered) and _DIRECTOR_DEFENSE.search(lowered):
        return False
    return bool(
        _CO_DC.search(lowered)
        or _DC.search(lowered)
        or _DIRECTOR_DEFENSE.search(lowered)
        or _SLASH_DC.search(lowered)
    )


def _principal_hc(title: str) -> bool:
    lowered = _norm(title)
    if not _HC.search(lowered):
        return False
    if _NOT_HC.search(lowered):
        return False
    return True


def assignments_from_title(title: str) -> list[dict[str, Any]]:
    """Lossless assignment list. Raw title is always retained."""

    raw = _norm(title)
    if not raw:
        return []
    lowered = raw.casefold()
    assignments: list[dict[str, Any]] = []
    qualifiers = extract_qualifiers(raw)
    if _principal_hc(raw):
        assignments.append(_assignment(ROLE_HC, "TEAM", qualifiers, raw, "PRINCIPAL"))
    elif _HC.search(lowered) and _NOT_HC.search(lowered):
        code = (
            "assistant_head_coach"
            if "assistant" in lowered or "associate" in lowered
            else "unmapped_title_review_required"
        )
        if "strength" in lowered:
            code = "strength_conditioning"
        assignments.append(
            _assignment(code, "TEAM", qualifiers, raw, "QUALIFIED_NOT_PRINCIPAL")
        )
    if _principal_oc(raw):
        assignments.append(
            _assignment(
                ROLE_OC,
                "OFFENSE",
                qualifiers,
                raw,
                "CO_SHARED" if QUALIFIER_CO in qualifiers else "PRINCIPAL",
            )
        )
    elif _ASSISTANT_TO.search(lowered) and (
        _OC.search(lowered) or _SLASH_OC.search(lowered)
    ):
        assignments.append(
            _assignment(ROLE_OC, "OFFENSE", qualifiers, raw, "QUALIFIED_NOT_PRINCIPAL")
        )
    elif _ASSISTANT_OC.search(lowered) or (
        _OC.search(lowered)
        and QUALIFIER_ASSISTANT in qualifiers
        and QUALIFIER_CO not in qualifiers
    ):
        assignments.append(
            _assignment(ROLE_OC, "OFFENSE", qualifiers, raw, "QUALIFIED_NOT_PRINCIPAL")
        )
    if _principal_dc(raw):
        assignments.append(
            _assignment(
                ROLE_DC,
                "DEFENSE",
                qualifiers,
                raw,
                "CO_SHARED" if QUALIFIER_CO in qualifiers else "PRINCIPAL",
            )
        )
    elif _ASSISTANT_TO.search(lowered) and (
        _DC.search(lowered) or _SLASH_DC.search(lowered)
    ):
        assignments.append(
            _assignment(ROLE_DC, "DEFENSE", qualifiers, raw, "QUALIFIED_NOT_PRINCIPAL")
        )
    elif _ASSISTANT_DC.search(lowered):
        assignments.append(
            _assignment(ROLE_DC, "DEFENSE", qualifiers, raw, "QUALIFIED_NOT_PRINCIPAL")
        )
    for pattern, code, unit in POSITION_PATTERNS:
        if re.search(pattern, lowered, re.I) and not any(
            row["role"] == code for row in assignments
        ):
            # Broad DB stays DB; do not also emit CB/S unless those words appear.
            if (
                code in {"cornerbacks", "safeties"}
                and re.search(r"\bdefensive backs?\b", lowered)
                and not re.search(pattern, lowered, re.I)
            ):
                continue
            assignments.append(_assignment(code, unit, qualifiers, raw, "OBSERVED"))
    if not assignments:
        assignments.append(
            _assignment(
                "unmapped_title_review_required",
                "UNKNOWN",
                qualifiers,
                raw,
                "UNMAPPED",
            )
        )
    return assignments


def _assignment(
    role: str, unit: str, qualifiers: Sequence[str], raw: str, occupancy: str
) -> dict[str, Any]:
    return {
        "role": role,
        "unit": unit,
        "qualifiers": list(qualifiers),
        "source_title": raw,
        "occupancy": occupancy,
        "taxonomy_version": TAXONOMY_VERSION,
        "play_caller_inferred": False,
    }


def principal_role_families(title: str) -> tuple[str, ...]:
    """HC/OC/DC families that may occupy the principal current-staff cell."""

    families: list[str] = []
    if _principal_hc(title):
        families.append(ROLE_HC)
    if _principal_oc(title):
        families.append(ROLE_OC)
    if _principal_dc(title):
        families.append(ROLE_DC)
    return tuple(families)


@lru_cache(maxsize=1)
def load_taxonomy_rows(path: str | None = None) -> tuple[dict[str, str], ...]:
    target = Path(path) if path else PACK_TAXONOMY
    if not target.is_file():
        return ()
    with target.open("r", encoding="utf-8", newline="") as handle:
        return tuple(dict(row) for row in csv.DictReader(handle))
