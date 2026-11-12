"""Evidence & Freshness Intelligence Engine (Feature 10).

Principle: Claude *proposes* statements and cites sources; this module *decides*
how much evidence backs each statement, using deterministic rules that Claude
cannot talk its way around.

Labels
  verified              >=2 independent domains, strong text match, at least one recent source
  partially_supported   some support (1 source, undated/older sources, or weaker match)
  needs_verification    no valid source, or the cited text doesn't support the statement
  potentially_outdated  every cited source is older than its freshness window

AI interpretations (is_inference=True) can never be "verified".
"""
import re
from dataclasses import dataclass
from datetime import date

from app.models import Claim, EvidenceLabel, Freshness, SourceCategory
from app.utils.date_utils import age_in_days, today_utc
from app.utils.helpers import domain_of

NEWS_WINDOW_DAYS = 30
OTHER_WINDOW_DAYS = 365

VERIFIED_MIN_SCORE = 0.45
UNSUPPORTED_BELOW = 0.20

_STOP = {
    "that", "this", "with", "from", "have", "has", "been", "were", "was", "will", "their", "they",
    "than", "then", "also", "into", "over", "such", "which", "while", "about", "after", "before",
    "more", "most", "other", "some", "these", "those", "there", "where", "when", "what", "would",
    "could", "should", "being", "its", "for", "and", "the", "are", "but", "not", "can", "may",
    "company", "organisation", "organization",
}


def classify_freshness(published: date | None, category: str, today: date | None = None) -> str:
    """recent / potentially_outdated / unknown. Undated sources are 'unknown', never guessed."""
    age = age_in_days(published, today)
    if age is None or age < 0:
        return Freshness.UNKNOWN.value
    window = NEWS_WINDOW_DAYS if category == SourceCategory.NEWS.value else OTHER_WINDOW_DAYS
    return Freshness.RECENT.value if age <= window else Freshness.POTENTIALLY_OUTDATED.value


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9][a-z0-9\-']+", text.lower()) if len(w) >= 4 and w not in _STOP}


def support_score(claim: str, source_texts: list[str]) -> float:
    """Share of the claim's content words that appear in the cited source text (0..1)."""
    toks = _tokens(claim)
    if not toks:
        return 0.0
    hay = " ".join(source_texts).lower()
    return sum(1 for t in toks if t in hay) / len(toks)


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "").rstrip(".") for n in re.findall(r"\d[\d,]*\.?\d*", text)}


@dataclass
class Verdict:
    label: str
    valid_ids: list[int]
    note: str
    score: float


def evaluate_claim(text: str, source_ids: list[int], sources_by_id: dict, is_inference: bool = False) -> Verdict:
    ids = list(dict.fromkeys(source_ids))  # de-duplicate, keep order
    valid = [i for i in ids if i in sources_by_id]
    dropped = len(ids) - len(valid)

    if not valid:
        note = "No supporting source was cited."
        if dropped:
            note = "The cited source ids do not exist, so they were discarded."
        return Verdict(EvidenceLabel.NEEDS_VERIFICATION.value, [], note, 0.0)

    srcs = [sources_by_id[i] for i in valid]
    texts = [(s.content or s.snippet or s.title or "") for s in srcs]
    score = support_score(text, texts)
    notes: list[str] = []
    if dropped:
        notes.append(f"{dropped} cited source id(s) did not exist and were discarded.")

    if score < UNSUPPORTED_BELOW:
        notes.append(f"Cited sources do not appear to support this statement (text match {score:.0%}).")
        return Verdict(EvidenceLabel.NEEDS_VERIFICATION.value, valid, " ".join(notes), score)

    fresh = [s.freshness for s in srcs]
    domains = {domain_of(s.url) for s in srcs}

    if all(f == Freshness.POTENTIALLY_OUTDATED.value for f in fresh):
        label = EvidenceLabel.POTENTIALLY_OUTDATED.value
        notes.append("All supporting sources are older than their freshness window.")
    elif len(domains) >= 2 and score >= VERIFIED_MIN_SCORE and Freshness.RECENT.value in fresh:
        label = EvidenceLabel.VERIFIED.value
        notes.append(f"Supported by {len(domains)} independent domains, including a recent source.")
    else:
        label = EvidenceLabel.PARTIALLY_SUPPORTED.value
        notes.append(f"Supported by {len(domains)} domain(s); not enough for full verification.")

    hay = " ".join(texts).replace(",", "")
    missing = [n for n in _numbers(text) if n not in hay]
    if missing and label == EvidenceLabel.VERIFIED.value:
        label = EvidenceLabel.PARTIALLY_SUPPORTED.value
        notes.append(f"Figure(s) {', '.join(sorted(missing))} not found in the cited text.")

    if is_inference and label == EvidenceLabel.VERIFIED.value:
        label = EvidenceLabel.PARTIALLY_SUPPORTED.value
        notes.append("AI interpretation: cannot be marked verified.")
    if is_inference:
        notes.append("This is an AI interpretation, not a quoted fact.")

    return Verdict(label, valid, " ".join(notes), score)


# ---------------------------------------------------------------- helpers for raw Claude output

def as_list(value) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def int_list(value) -> list[int]:
    out: list[int] = []
    for v in as_list(value):
        try:
            out.append(int(str(v).strip().lstrip("S").lstrip("s")))
        except (TypeError, ValueError):
            continue
    return out


def clean_text(value) -> str:
    return re.sub(r"\s+", " ", value).strip() if isinstance(value, str) else ""


def verify_statements(
    db,
    meeting_id: int,
    raw_items,
    section: str,
    sources_by_id: dict,
    ref_map: dict[int, int],
    default_inference: bool = False,
) -> list[dict]:
    """Turn Claude's proposed statements into persisted, labelled Claim rows."""
    out: list[dict] = []
    for item in as_list(raw_items):
        if isinstance(item, str):
            item = {"text": item}
        if not isinstance(item, dict):
            continue
        text = clean_text(item.get("text"))
        if not text:
            continue
        is_inf = bool(item.get("is_inference", default_inference))
        verdict = evaluate_claim(text, int_list(item.get("source_ids")), sources_by_id, is_inf)
        claim = Claim(
            meeting_id=meeting_id,
            section=section,
            text=text,
            evidence_label=verdict.label,
            source_ids=verdict.valid_ids,
            is_inference=is_inf,
            note=verdict.note,
        )
        db.add(claim)
        db.flush()
        out.append(
            {
                "text": text,
                "source_ids": verdict.valid_ids,
                "refs": [ref_map[i] for i in verdict.valid_ids],
                "evidence_label": verdict.label,
                "is_inference": is_inf,
                "note": verdict.note,
                "claim_id": claim.id,
            }
        )
    return out


def summarize_evidence(sources: list, claims: list) -> dict:
    def count(label: str) -> int:
        return sum(1 for c in claims if c.evidence_label == label)

    return {
        "total_sources": len(sources),
        "recent_sources": sum(1 for s in sources if s.freshness == Freshness.RECENT.value),
        "outdated_sources": sum(1 for s in sources if s.freshness == Freshness.POTENTIALLY_OUTDATED.value),
        "undated_sources": sum(1 for s in sources if s.freshness == Freshness.UNKNOWN.value),
        "total_claims": len(claims),
        "verified": count(EvidenceLabel.VERIFIED.value),
        "partially_supported": count(EvidenceLabel.PARTIALLY_SUPPORTED.value),
        "needs_verification": count(EvidenceLabel.NEEDS_VERIFICATION.value),
        "potentially_outdated": count(EvidenceLabel.POTENTIALLY_OUTDATED.value),
    }
