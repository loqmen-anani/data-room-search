"""Chargement de la data room JSON et normalisation des métadonnées (entités, dates, SIREN)."""

import json
import re
import unicodedata
from datetime import date, datetime
from pathlib import Path

from dataroom.config import DATA_PATH
from dataroom.models import Contract, Party

# Mots ignorés pour identifier une entité : formes sociales et civilités. « QUORVIA SAS », « Quorvia » et
# « Société Quorvia » donnent le même identifiant ; des noms proches mais différents (« Groupe Brenalis » /
# « Brénalys Advisory ») restent distincts : aucun rapprochement approximatif.
IGNORED_WORDS = {
    "sa", "sas", "sasu", "sarl", "eurl", "sci", "snc", "societe", "ltd", "inc", "gmbh", "llc",
    "m", "mme", "mlle", "monsieur", "madame",
}

MOIS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
    "août": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12,
}

# Date citée dans un texte : « 1er juillet 2023 » ou « 30/06/2026 »
DATE_IN_TEXT = re.compile(rf"(\d{{1,2}})(?:er)?\s+({'|'.join(MOIS)})\s+(\d{{4}})|(\d{{2}})/(\d{{2}})/(\d{{4}})", re.IGNORECASE)


def normalize_name(raw: str) -> str:
    s = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode().lower()
    words = re.sub(r"[^a-z0-9 ]", " ", s).split()
    return " ".join(w for w in words if w not in IGNORED_WORDS)


def entity_id(raw: str) -> str:
    """Identifiant d'une entité, tiré de son nom normalisé : « Société Quorvia » -> "quorvia"."""
    return normalize_name(raw).replace(" ", "_")


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    raw = raw.strip()
    if m := re.fullmatch(r"(\d{1,2}) (\w+) (\d{4})", raw):  # "15 mars 2021"
        month = MOIS.get(m[2].lower())
        return date(int(m[3]), month, int(m[1])) if month else None
    if re.match(r"\d{4}-\d{2}-\d{2}T", raw):  # ISO avec heure
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def dates_in_text(text: str) -> list[date]:
    """Dates citées dans un texte, dans l'ordre d'apparition."""
    dates = []
    for m in DATE_IN_TEXT.finditer(text):
        try:
            dates.append(date(int(m[3]), MOIS[m[2].lower()], int(m[1])) if m[1] else date(int(m[6]), int(m[5]), int(m[4])))
        except ValueError:  # date impossible (31/02)
            pass
    return dates


def normalize_siren(raw: str | None) -> str | None:
    if raw is None:
        return None
    digits = raw.replace(" ", "")
    return digits if re.fullmatch(r"\d{9}", digits) else None


def load_contracts(path: Path = DATA_PATH) -> list[Contract]:
    contracts = []
    for i, c in enumerate(json.loads(path.read_text(encoding="utf-8")), start=1):
        warnings = []
        parties = []
        for raw_name, raw_siren in zip(c["parties"], c["siren_parties"]):
            siren = normalize_siren(raw_siren)
            if raw_siren is not None and siren is None:
                warnings.append(f"siren_invalide: {raw_siren!r}")
            parties.append(Party(entity_id=entity_id(raw_name), raw=raw_name, siren=siren))

        signature_date = parse_date(c["signature_date"])
        if c["signature_date"] and signature_date is None:
            warnings.append(f"date_signature_illisible: {c['signature_date']!r}")
        end_date = parse_date(c["end_date"])
        if c["end_date"] and end_date is None:
            warnings.append(f"date_fin_illisible: {c['end_date']!r}")

        contracts.append(Contract(
            contract_id=f"c{i:02d}",
            filename=c["filename"],
            title=c["title"],
            parties=parties,
            contract_type=c["contract_type"],
            signature_date=signature_date,
            end_date=end_date,
            initial_end_date=end_date,
            governing_law=c["governing_law"],
            content=c["content"] or "",
            warnings=warnings,
        ))
    return contracts
