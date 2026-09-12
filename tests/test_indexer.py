from dataroom.indexer import chunk_contract, tokenize


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
