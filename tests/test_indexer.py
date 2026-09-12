from datetime import date

from dataroom.indexer import DataRoomIndex, chunk_contract, tokenize
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


def test_amendment_without_identified_contract_stays_alone():
    contracts = {c.contract_id: c for c in load_contracts()}
    # Un second contrat possible (mêmes parties), et l'avenant ne cite plus la date de signature : pas de rattachement.
    twin = contracts["c09"].model_copy(update={"contract_id": "c21", "signature_date": date(2024, 1, 1)}, deep=True)
    contracts["c18"].content = contracts["c18"].content.replace("le 19 juin 2023", "")
    index = DataRoomIndex([*contracts.values(), twin])
    assert index.contracts["c18"].amends == [] and index.contracts["c09"].end_date.isoformat() == "2026-06-30"
    assert index.contracts["c18"].warnings == ["avenant non rattaché : contrat modifié non identifié"]
