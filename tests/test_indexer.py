from datetime import date

from dataroom.indexer import DURATION_HEADING, DataRoomIndex, chunk_contract, plain, tokenize
from dataroom.loader import load_contracts


def test_chunk_by_article(index):
    chunks = chunk_contract(index.contracts["c03"])
    assert [c.heading for c in chunks] == [
        "PRÉAMBULE", "ARTICLE 1 — OBJET", "ARTICLE 2 — OBJECTIFS", "ARTICLE 4 — EXCLUSIVITÉ", "ARTICLE 6 — DURÉE",
        "ARTICLE 10 — LOI APPLICABLE",
    ]
    assert chunks[3].text.startswith("Pendant toute la durée du contrat, Ribault Logistique bénéficie")


def test_tokenize_accents_stopwords_plural():
    assert tokenize("Les Contrats d'exclusivité") == ["contrat", "exclusivite"]


def test_values_come_from_the_data_room(index):
    assert {"groupe_brenalis", "brenalys_advisory"} <= index.entities
    assert index.laws == {"droit français", "droit suisse", "droit new-yorkais"}
    assert "contrat de franchise" not in index.contract_types  # c13 est mal typé : seul son texte le révèle


def test_amendment_is_linked_and_postpones_term(index):
    c09, c18 = index.contracts["c09"], index.contracts["c18"]
    assert c18.amends == ["c09"] and c09.amended_by == ["c18"]
    assert (c09.initial_end_date.isoformat(), c09.end_date.isoformat()) == ("2026-06-30", "2028-06-30")
    assert c09.warnings == ["terme modifié par l'avenant c18 : 2026-06-30 → 2028-06-30"]


def test_duration_heading_matches_whole_words_only():
    for heading in ("ARTICLE 5 — DURÉE", "ARTICLE 2 — REPORT DU TERME", "ARTICLE 2 — TERM AND TERMINATION", "PROROGATION"):
        assert DURATION_HEADING.search(plain(heading)), heading
    for heading in ("ARTICLE 3 — DÉTERMINATION DU PRIX", "ARTICLE 9 — TERMINATION", "ARTICLE 4 — INTERMÉDIAIRES"):
        assert not DURATION_HEADING.search(plain(heading)), heading


def test_amendment_term_vs_metadata_mismatch_is_flagged():
    contracts = load_contracts()
    c18 = next(c for c in contracts if c.contract_id == "c18")
    c18.end_date = c18.initial_end_date = date(2029, 1, 1)  # métadonnée fausse : le texte dit 30 juin 2028
    index = DataRoomIndex(contracts)
    assert index.contracts["c09"].end_date == date(2028, 6, 30)  # le texte de l'avenant fait foi
    assert index.contracts["c18"].warnings == ["terme cité dans l'avenant (2028-06-30) différent de sa date de fin (2029-01-01)"]


def test_amendment_without_duration_article_leaves_term_unchanged():
    contracts = load_contracts()
    c18 = next(c for c in contracts if c.contract_id == "c18")
    c18.content = c18.content.replace("ARTICLE 2 — REPORT DU TERME", "ARTICLE 2 — INDEXATION")  # avenant de prix seulement
    index = DataRoomIndex(contracts)
    assert index.contracts["c18"].amends == ["c09"]
    assert index.contracts["c09"].end_date == date(2026, 6, 30) and index.contracts["c09"].warnings == []


def test_amendment_without_identified_contract_stays_alone():
    contracts = {c.contract_id: c for c in load_contracts()}
    # Un second contrat possible (mêmes parties), et l'avenant ne cite plus la date de signature : pas de rattachement.
    twin = contracts["c09"].model_copy(update={"contract_id": "c21", "signature_date": date(2024, 1, 1)}, deep=True)
    contracts["c18"].content = contracts["c18"].content.replace("le 19 juin 2023", "")
    index = DataRoomIndex([*contracts.values(), twin])
    assert index.contracts["c18"].amends == [] and index.contracts["c09"].end_date.isoformat() == "2026-06-30"
    assert index.contracts["c18"].warnings == ["avenant non rattaché : contrat modifié non identifié"]
