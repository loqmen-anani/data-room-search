import pytest

from dataroom.duplicates import find_duplicates, text_similarity
from dataroom.models import FindDuplicates


def pairs(resp):
    return sorted(tuple(p.contract_ids) for p in resp.pairs)


def test_finds_reupload_and_translation(index):
    resp = find_duplicates(index, FindDuplicates())
    assert pairs(resp) == [("c05", "c20"), ("c11", "c19")]
    assert resp.contracts_compared == 20
    by = {tuple(p.contract_ids): p for p in resp.pairs}
    reupload, translation = by[("c11", "c19")], by[("c05", "c20")]
    assert reupload.text_similarity == 1.0 and "texte identique à 100 %" in reupload.reasons
    assert translation.text_similarity < 0.5  # traduction : le texte diffère, les métadonnées la trahissent
    assert translation.reasons == [
        "mêmes parties", "même type (contrat de licence)", "même date de signature (2024-10-01)",
        "même date de fin (2027-09-30)",
    ]


def test_same_day_different_acts_are_not_duplicates(index):
    flagged = {cid for p in find_duplicates(index, FindDuplicates()).pairs for cid in p.contract_ids}
    assert not {"c08", "c14"} & flagged  # cession et garantie signées le même jour par les mêmes parties
    assert not {"c09", "c18"} & flagged  # un contrat et son avenant


def test_restricted_to_entities(index):
    resp = find_duplicates(index, FindDuplicates(entity_ids=["hydrelle_energie"]))
    assert pairs(resp) == [("c05", "c20")] and resp.contracts_compared < 20
    with pytest.raises(ValueError, match="inconnu"):
        find_duplicates(index, FindDuplicates(entity_ids=["nobody"]))


def test_text_similarity():
    assert text_similarity({"a", "b"}, {"a", "b"}) == 1.0
    assert text_similarity({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)
    assert text_similarity(set(), set()) == 0.0
