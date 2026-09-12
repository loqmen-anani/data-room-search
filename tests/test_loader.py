from dataroom.loader import entity_id, load_contracts, parse_date


def test_entity_id_merges_variants_but_not_lookalikes():
    assert entity_id("QUORVIA SAS") == entity_id("Quorvia") == entity_id("Société Quorvia") == "quorvia"
    assert entity_id("M. Étienne Morand") == "etienne_morand" != entity_id("Cabinet Morand")
    assert entity_id("Groupe Brenalis") != entity_id("Brénalys Advisory")


def test_parse_date_formats():
    for raw in ("15 mars 2021", "15/03/2021", "2021-03-15", "2021/03/15", "15-03-2021", "2021-03-15T00:00:00Z"):
        assert parse_date(raw).isoformat() == "2021-03-15"
    assert parse_date("15 foo 2021") is None
    assert parse_date(None) is None


def test_example_data_room_warnings():
    contracts = load_contracts()  # jeu fictif, fixé par conftest.py
    assert {c.contract_id: c.warnings for c in contracts if c.warnings} == {"c13": ["siren_invalide: 'en cours'"]}
