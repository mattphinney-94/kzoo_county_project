"""No database required. Run: python -m pytest tests/search -v"""

import pytest
from api.search_matching import name_match_score, rank_fuzzy_candidates, tokenize


@pytest.mark.parametrize("query", [
    "William Graham", "William D Graham", "Graham William D",
    "Will Graham", "Bill Graham", "Will Grahm", "Graham, William D",
])
def test_william_graham_can_be_found_with_name_variations(query):
    assert name_match_score(query, "GRAHAM, WILLIAM D") is not None


def test_different_people_are_not_merged():
    originals = [
        {
            "entity_id": ident,
            "canonical_name": "GRAHAM, WILLIAM D",
            "entity_type": "Person",
            "canonical_address": address,
            "organization_type": None,
            "organization_classification_confidence": None,
            "occurrence_count": 1,
            "source_entity_name": None,
        }
        for ident, address in [(1710, "Portland"), (1711, "Galesburg"),
                               (1719, "PO Box")]
    ]
    result = rank_fuzzy_candidates("Will Grahm", originals)
    assert {row["entity_id"] for row in result} == {1710, 1711, 1719}
    assert len(result) == 3


def test_search_tokens_are_order_independent():
    assert name_match_score("William D Graham", "GRAHAM WILLIAM D") == (0, 0)


def test_middle_initial_is_optional_only_when_not_queried():
    assert name_match_score("William Graham", "GRAHAM, WILLIAM D") is not None
    assert name_match_score("William D Graham", "GRAHAM WILLIAM") is None


def test_nonsensical_or_unrelated_names_not_matched():
    assert name_match_score("Will Grahm", "SUSAN GRAHAM") is None
    assert name_match_score("Will Graham", "WILL SMITH") is None
    assert name_match_score("%_!", "GRAHAM WILLIAM D") is None


def test_source_name_variant_is_supported():
    row = {
        "entity_id": 4342,
        "canonical_name": "THE COPPER CREEK TRUST",
        "entity_type": "Organization",
        "canonical_address": None,
        "organization_type": "Trust",
        "organization_classification_confidence": "Medium",
        "occurrence_count": 4,
        "source_entity_name": "COPPERCREEK TRUST",
    }
    assert [x["entity_id"] for x in rank_fuzzy_candidates("Coppercreek", [row])] == [4342]


def test_literal_source_variants_are_deduplicated():
    row = {
        "entity_id": 4342,
        "canonical_name": "THE COPPER CREEK TRUST",
        "entity_type": "Organization",
        "canonical_address": None,
        "organization_type": "Trust",
        "organization_classification_confidence": "Medium",
        "occurrence_count": 4,
        "source_entity_name": "COPPERCREEK TRUST",
    }
    assert len(rank_fuzzy_candidates("Copper Creek", [row, row])) == 1


def test_search_token_normalization():
    assert tokenize("  GrAhAm,   WILLIAM D. ") == ("graham", "william", "d")
