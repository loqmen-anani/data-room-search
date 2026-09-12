# data-room-search — tool de recherche dans une data room

## Contexte

- Un tool qu'un agent LLM appelle pour interroger en langage naturel une data room de contrats (M&A, audit, contentieux).
- **`private/` n'est jamais versionné** : données réelles, énoncé d'origine et notes locales (voir `private/enonce.md` s'il existe). Ne jamais committer de données réelles ni de contenu qui en dérive (extraits, noms, valeurs, résultats) : les exemples, tests et démos versionnés utilisent le jeu fictif.
- Préférer des plans clairs et concis, centrés sur les grandes étapes ; ne pas partir dans le détail avant qu'on le demande.
- Tout en français (échanges, docstrings, messages du tool).

## Architecture retenue (4 étapes)

1. **Réception de la demande** : l'agent reformule la question et appelle un tool unique, `search_data_room`, validé par Pydantic : `query` (texte libre, optionnel), `filters` (`entity_ids`, `contract_types`, `governing_law` in/not_in, plages `signature_date` / `end_date`) et `top_k`. Les valeurs possibles (entités, types, lois) sont tirées de la data room chargée, injectées dans le schéma (`_inject_enums` dans `tools.py`) et vérifiées à la recherche : une valeur inconnue lève une erreur qui liste les valeurs possibles. Dates absolues uniquement : l'agent convertit « fin 2026 » en `2026-12-31`.
2. **Indexation** : un chunk par article (regex `ARTICLE n — TITRE`), le texte avant le premier article devient « PRÉAMBULE ». Titre, parties et type du contrat sont indexés avec chaque article. BM25 maison (sans dépendance), tokenisation FR (accents, mots vides, pluriels). Index en mémoire, reconstruit au démarrage (quelques ms).
3. **Recherche** : pré-filtrage sur les métadonnées, puis :
   - sans `query` → **tous** les candidats (réponse exhaustive, pas de top-k) ;
   - avec `query` → BM25 sur les articles des candidats, score du contrat = son meilleur article, `top_k` premiers.
4. **Sortie** : par contrat, `matched_filters` et jusqu'à 3 `relevant_articles` (heading + extrait + score). L'article qui justifie un filtre (DURÉE, LOI APPLICABLE) remonte aussi sans query. Un contrat dont le champ filtré est vide va dans `excluded_unknown` : **jamais écarté en silence**. Le tool `get_contract` renvoie le texte par article pour vérifier.

Positionnement : c'est un **RAG agentique hybride**. Le chemin `query` est du RAG (retrieval BM25) ; le chemin `filters` est une requête structurée construite par le LLM (self-query), pas du RAG. Le RAG classique (top-k) échoue sur ce type de questions : exhaustivité, filtres, comparaison entre documents.

## Décisions prises

- Tout le code est dans le package `dataroom/` (structure plate, sans `src/`, pour rester simple à lancer) ; données dans `data/`, scripts dans `scripts/`, un fichier de test par module.
- Configuration centralisée dans `dataroom/config.py`, surchargeable par variables d'environnement : `DATAROOM_DATA`, `DATAROOM_MODEL`, `OLLAMA_URL`, `DATAROOM_MCP_TOKEN`.
- **Données** :
  - `data/exemple_data_room.json` : jeu fictif, publiable, écrit à la main indépendamment des données de l'exercice (aucun nom, texte, date ni montant repris ; pièges placés à d'autres numéros). 20 contrats d'une due diligence sur le « Groupe Brenalis », SIREN invalides au sens de Luhn. C'est la data room par défaut.
  - Données réelles : dans `private/`, chargées avec `DATAROOM_DATA=private/<fichier>.json`.
  - Tests sur le jeu fictif (`tests/conftest.py` fixe `DATAROOM_DATA` avant tout import). Un test local sur données réelles peut vivre dans `tests/test_enonce.py`, exclu de git et ignoré si les données sont absentes.
  - `scripts/demo.py` écrit dans `private/`, et non dans `docs/`, dès que la data room n'est pas le jeu fictif.
- **Aucune data room codée en dur** : identifiant d'entité = nom normalisé (formes sociales et civilités retirées, `entity_id()` dans `loader.py`), sans rapprochement approximatif ; pas de table d'alias ni de `Literal`. Sur le jeu fictif, « Groupe Brenalis » a pour identifiant `groupe_brenalis`.
- **BM25 seul pour l'instant** : les embeddings se brancheront dans `search.py` (fusion RRF) sans changer les formats d'entrée et de sortie.
- **Qualité des données hors périmètre pour l'instant** : normalisation minimale (dates multi-formats, SIREN, noms d'entités) dans `dataroom/loader.py`.
- Pas de SQL libre pour l'agent : peu de tools, typés.
- Schéma des tools aplati (`_simplify` dans `tools.py`) : pas de `$ref` ni d'`anyOf`, moins de tokens, plus fiable pour un petit modèle.
- **LLM de l'agent : local, via Ollama** (`huihui_ai/qwen3.5-abliterated:27b` par défaut, surchargeable via `DATAROOM_MODEL` ou `--model`). Appels HTTP directs avec `httpx`, sans SDK. Une erreur de tool est renvoyée au modèle (et non levée) pour qu'il corrige son appel.
- **Serveur MCP** (`dataroom/mcp_server.py`, SDK `mcp` 2.x) : serveur bas niveau `Server(on_list_tools=…, on_call_tool=…)` branché sur `tool_definitions()` / `run_tool()`. Un seul contrat de tool pour l'API REST, l'agent Ollama et MCP.
  - Transports : stdio par défaut ; `--http` = Streamable HTTP sans état, en JSON, sur `/mcp` (port 8002).
  - Sécurité : local par défaut (protection DNS rebinding du SDK) ; hors localhost, jeton Bearer `DATAROOM_MCP_TOKEN` obligatoire (`token_verifier` du SDK), sinon le serveur refuse de démarrer. Derrière un tunnel : `--allow-host <domaine>` et `--path /mcp/<secret>` (le chemin secret sert de clé).
  - Erreurs : une erreur du tool (dont une valeur de filtre inconnue) revient avec `is_error` ; un tool inconnu est une erreur de protocole `-32602`.
  - Attention : dans `mcp` 2.x, `FastMCP` est devenu `MCPServer` et l'API bas niveau a changé (handlers passés au constructeur, types en snake_case, `resource_server_url` obligatoire dans `AuthSettings`). Vérifier dans le paquet installé plutôt que de se fier à la v1.

## Structure

```
├── README.md               présentation pour un lecteur humain
├── CLAUDE.md
├── pyproject.toml          dépendances + config pytest
├── .github/workflows/pytest.yml    CI : pytest sur Python 3.10 et 3.14
├── data/
│   └── exemple_data_room.json      jeu fictif, publiable
├── dataroom/
│   ├── config.py           chemins et modèle (variables d'environnement)
│   ├── models.py           entrée/sortie du tool (valeurs des filtres : tirées de la data room)
│   ├── loader.py           chargement du JSON + normalisation (identifiants d'entités, dates, SIREN)
│   ├── indexer.py          découpage par article, tokenisation, BM25, DataRoomIndex (entités, types, lois)
│   ├── search.py           filtres (match / exclu / inconnu), valeurs inconnues rejetées, classement, articles
│   ├── tools.py            get_contract, tool_definitions() (format API Claude, schéma aplati, valeurs injectées), run_tool()
│   ├── agent.py            boucle tool-use avec Ollama + CLI
│   ├── api.py              FastAPI : GET /tools, POST /tools/search_data_room, /tools/get_contract, /ask
│   └── mcp_server.py       serveur MCP : stdio, ou Streamable HTTP sur /mcp (jeton Bearer hors localhost)
├── scripts/
│   ├── run_query.sh        recherche seule (sans LLM), sortie JSON
│   ├── demo.py             agent sur des questions types → docs/demo.md (jeu fictif) ou private/demo.md
│   └── mcp_tunnel.sh       URL HTTPS publique pour le connecteur personnalisé de Claude
├── docs/demo.md            trace générée de la démo sur le jeu fictif (ne pas éditer à la main)
├── tests/                  conftest.py (jeu fictif) + un fichier par module ; test_agent.py : faux LLM
└── private/                non versionné : données réelles, énoncé, notes, ancien historique, ébauche v2
```

Identifiants : contrats `c01`…`c20` (ordre du JSON, à partir de 1), articles `c03-3`.

## Commandes

```bash
.venv/bin/pip install -e ".[dev]"                     # installation (projet + pytest)
.venv/bin/pytest -q                                   # tests (sans Ollama)
.venv/bin/python -m dataroom.indexer                  # stats de l'index (jeu fictif)
DATAROOM_DATA=private/<fichier>.json .venv/bin/python -m dataroom.indexer   # sur des données réelles (locales)
.venv/bin/uvicorn dataroom.api:app --port 8001 --reload   # API (le port 8000 est souvent occupé)
bash scripts/run_query.sh "exclusivité territoriale"  # recherche seule, sortie JSON (PORT=8002 pour changer)
.venv/bin/python -m dataroom.agent "Lesquels sont régis par un droit étranger ?"   # agent de bout en bout
.venv/bin/python scripts/demo.py                      # régénère docs/demo.md (~5 min avec le 27B)
.venv/bin/dataroom-mcp                                # serveur MCP en stdio (= python -m dataroom.mcp_server)
.venv/bin/dataroom-mcp --http                         # serveur MCP HTTP : http://127.0.0.1:8002/mcp
# Clients stdio : donner la commande dataroom-mcp sans argument (le CLI de l'Inspector MCP avale « -m »).
bash scripts/mcp_tunnel.sh                            # URL HTTPS publique (cloudflared) pour le connecteur personnalisé de Claude
curl -s -X POST localhost:8001/ask -H 'Content-Type: application/json' -d '{"question": "..."}'
```

Environnement : Python 3.14 (`.venv`), projet installé en éditable. Ollama 0.33 sur `localhost:11434` ; modèle recommandé : Qwen 3.5 27B (35 à 90 s par question sur M1 Pro 32 Go).

## Résultats de référence (jeu fictif)

| Question | Résultat | Signalés à part |
|---|---|---|
| Brenalis (`groupe_brenalis`), fin avant fin 2026 | c04, c09 | `excluded_unknown` : c08, c17 ; c12 (Brénalys) exclu |
| Droit étranger | c05 (new-yorkais), c16 (suisse), c20 (traduction de c05) | c10 (loi non renseignée) |
| « exclusivité territoriale » / « franchise » | c03 (ARTICLE 4) / c13 (typé « licence ») | — |

## Pièges connus du jeu fictif (non traités pour l'instant)

- c09 : terme reporté par l'avenant c18 (faux positif pour « fin avant fin 2026 ») ; doublons {c11, c19} (même convention téléversée deux fois) et {c05, c20} (contrat en anglais et sa traduction de courtoisie).
- c15 : fin 2027-03-31 dans les métadonnées, 30/09/2026 dans le texte ; c13 est une franchise typée « contrat de licence ».
- c10 sans loi applicable ; SIREN « en cours » (c13) ; c08 (cession) et c14 (garantie) signés le même jour par les mêmes parties, sans être des doublons ; entités distinctes à noms proches : Groupe Brenalis / Brénalys Advisory, Cabinet Morand / M. Étienne Morand, Foncière Verdane / Comptoir Verdane.

## Publication

- Repo public depuis le 2026-09-12. Il ne contient aucune donnée réelle : le jeu d'exemple a été réécrit indépendamment des données de l'exercice, et l'historique a été recréé pour ne garder aucune version antérieure (l'ancien n'existe qu'en local dans `private/`).
- Avant tout commit qui touche aux données ou aux exemples : vérifier qu'aucun nom, texte, date ni montant n'est repris des fichiers de `private/`.

## Limites et prochaines étapes

- Pas de tool pour « Y a-t-il des doublons ? » : sur 20 contrats, l'agent peut trouver les paires en demandant la liste complète (filtres vides), ce qui ne passe pas à l'échelle. Pas de lien avenant → contrat.
- Bruit sur les requêtes texte : le préfixe titre/type fait matcher des contrats dont seul le titre correspond ; pas de seuil de pertinence (piste : couper sous ~40 % du meilleur score).
- Recherche lexicale seulement : une reformulation sans les mots du contrat ne trouve rien → embeddings + RRF.
- Identifiants d'entités = nom normalisé : pas de rapprochement des sigles ou fautes de frappe (voulu) ; à grande échelle, un tool `resolve_parties`.
- Évaluation sur un jeu de questions annoté par des juristes.
