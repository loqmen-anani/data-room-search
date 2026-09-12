import json
from datetime import date

from dataroom.loader import dates_in_text, entity_id, load_contracts, parse_date


def test_entity_id_merges_variants_but_not_lookalikes():
    assert entity_id("QUORVIA SAS") == entity_id("Quorvia") == entity_id("Société Quorvia") == "quorvia"
    assert entity_id("M. Étienne Morand") == "etienne_morand" != entity_id("Cabinet Morand")
    assert entity_id("Groupe Brenalis") != entity_id("Brénalys Advisory")


def test_parse_date_formats():
    for raw in ("15 mars 2021", "15/03/2021", "2021-03-15", "2021/03/15", "15-03-2021", "2021-03-15T00:00:00Z"):
        assert parse_date(raw).isoformat() == "2021-03-15"
    assert parse_date("15 foo 2021") is None
    assert parse_date(None) is None


def test_dates_in_text():
    text = "Signé le 1er juillet 2023, terme reporté au 30/06/2028 (le 31/02/2026 n'existe pas)."
    assert dates_in_text(text) == [date(2023, 7, 1), date(2028, 6, 30)]
    assert dates_in_text("Fait le 3 Fevrier 2024, pour 12 mois 2024, en 2023 juin 2024, ref 130/06/2028") == [date(2024, 2, 3)]


def test_example_data_room_warnings():
    contracts = load_contracts()  # jeu fictif, fixé par conftest.py
    assert {c.contract_id: c.warnings for c in contracts if c.warnings} == {"c13": ["siren_invalide: 'en cours'"]}


def test_load_tolerates_missing_or_inconsistent_metadata(tmp_path):
    path = tmp_path / "data_room.json"
    path.write_text(json.dumps([
        {"filename": "a.pdf", "parties": ["Alpha SAS", "Beta"], "siren_parties": ["123456789"], "content": "x"},
        {"title": "Sans rien", "parties": [], "content": None},
    ]), encoding="utf-8")
    a, b = load_contracts(path)
    assert a.title == "a.pdf" and a.contract_type == "non renseigné" and a.governing_law is None
    assert [p.siren for p in a.parties] == ["123456789", None]
    assert a.warnings == ["siren_parties: 1 valeur(s) pour 2 partie(s)"]
    assert b.contract_id == "c02" and b.parties == [] and b.content == "" and b.end_date is None
