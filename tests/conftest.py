"""Les tests tournent sur le jeu de données fictif publiable, quelle que soit la data room par défaut."""

import os
from pathlib import Path

# Avant tout import de dataroom : la configuration lit DATAROOM_DATA au chargement.
os.environ["DATAROOM_DATA"] = str(Path(__file__).parent.parent / "data" / "exemple_data_room.json")

import pytest  # noqa: E402

from dataroom.indexer import DataRoomIndex  # noqa: E402


@pytest.fixture(scope="session")
def index():
    return DataRoomIndex.from_json()
