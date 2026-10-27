"""Conservative, order-independent, typo-tolerant *search* helpers.

This module never merges entities or changes database records. Returned matches
are suggestions; each distinct entity retains its original ID and address.
"""

import re
import unicodedata
from functools import lru_cache

from rapidfuzz.distance import Levenshtein


# Explicit, deliberately small alias groups. These help discovery but DO NOT
# prove identity. Add synonyms only after reviewing representative search cases.
_NICKNAME_TO_ROOT = {
    alias: root
    for root, aliases in (
        ("william", {"william", "will", "bill", "billy", "willie"}),
        ("robert", {"robert", "rob", "bob", "bobby"}),
        ("james", {"james", "jim", "jimmy"}),
        ("elizabeth", {"elizabeth", "liz", "beth", "betty"}),
        ("richard", {"richard", "rick", "rich", "dick"}),
    )
    for alias in aliases
}



@lru_cache(maxsize=65536)
def tokenize(value: str) -> tuple[str, ...]:
    """Fold case/accents and break punctuation-separated words into tokens."""
    folded = unicodedata.normalize("NFKD", value.casefold())
    ascii_name = "".join(c for c in folded if not unicodedata.combining(c))
    return tuple(dict.fromkeys(re.findall(r"[^\W_]+", ascii_name)))


def _token_cost(query_token: str, candidate_token: str) -> int | None:
    if query_token == candidate_token:
        return 0

    # Nicknames are only considered as alternatives for otherwise supported
    # candidates, not as grounds for merging records.
    if (_NICKNAME_TO_ROOT.get(query_token, query_token)
            == _NICKNAME_TO_ROOT.get(candidate_token, candidate_token)):
        return 1

    # Guard against loose matching on initials and short tokens such as 'D'.
    shortest = min(len(query_token), len(candidate_token))
    if shortest < 5:
        return None

    max_edits = 2 if shortest >= 9 else 1
    distance = Levenshtein.distance(
        query_token, candidate_token, score_cutoff=max_edits
    )
    if distance <= max_edits:
        return 2 + (distance - 1)
    return None


def name_match_score(query: str, candidate: str) -> tuple[int, int] | None:
    """Find all search words in one candidate name, without assuming order.

    Returns (match_penalty, extra_candidate_tokens) or None. Each query word
    must map to a DISTINCT candidate word; candidate middle initials are okay.
    """
    sought = tokenize(query)
    available = tokenize(candidate)

    # Keep the search bounded and conservative for long or punctuation-only
    # inputs. The original SQL substring search remains available for those.
    if not sought or len(sought) > 6 or len(sought) > len(available):
        return None

    match_options = []
    for word in sought:
        options = []
        for i, name_word in enumerate(available):
            penalty = _token_cost(word, name_word)
            if penalty is not None:
                options.append((i, penalty))
        if not options:
            return None
        match_options.append(options)

    order = sorted(range(len(sought)), key=lambda k: len(match_options[k]))
    memo = {}

    def best_cost(position: int, used: int) -> int | None:
        state = (position, used)
        if state in memo:
            return memo[state]
        if position == len(order):
            return 0
        scores = []
        for word_index, cost in match_options[order[position]]:
            mask = 1 << word_index
            if used & mask:
                continue
            remaining = best_cost(position + 1, used | mask)
            if remaining is not None:
                scores.append(cost + remaining)
        answer = min(scores) if scores else None
        memo[state] = answer
        return answer

    total_penalty = best_cost(0, 0)
    if total_penalty is None:
        return None
    return total_penalty, len(available) - len(sought)


def rank_fuzzy_candidates(query, candidates, exclude_ids=(), limit=25):
    """Return unique entity rows ranked by strongest matching name variant.

    candidates: database rows with normal API result fields plus
    `source_entity_name` (nullable). Source variants are evaluated individually.
    """
    blocked = set(exclude_ids)
    ranked = {}
    for row in candidates:
        entity_id = row["entity_id"]
        if entity_id in blocked:
            continue
        names = ((row["canonical_name"], 0),
                 (row.get("source_entity_name"), 1))
        scores = []
        for name, source_penalty in names:
            if name:
                score = name_match_score(query, name)
                if score is not None:
                    scores.append((score[0], score[1], source_penalty))
        if not scores:
            continue
        score = min(scores)
        api_result = {
            k: row[k]
            for k in (
                "entity_id", "canonical_name", "entity_type",
                "canonical_address", "organization_type",
                "organization_classification_confidence", "occurrence_count"
            )
        }
        previous = ranked.get(entity_id)
        if previous is None or score < previous[0]:
            ranked[entity_id] = (score, api_result)

    ordered = sorted(
        ranked.values(),
        key=lambda v: (*v[0], v[1]["canonical_name"], v[1]["entity_id"])
    )
    return [row for _, row in ordered[:limit]]
