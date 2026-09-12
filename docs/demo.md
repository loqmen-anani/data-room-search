# Démo de bout en bout

Générée le 2026-09-12 22:54 par `python scripts/demo.py`, data room `exemple_data_room.json`, modèle `huihui_ai/qwen3.5-abliterated:27b` (Ollama).
Pour chaque question : les appels de tools choisis par l'agent, puis sa réponse.

## Quels contrats avec le Groupe Brenalis expirent avant fin 2026 ?

**Appel** `search_data_room` → 1 résultat(s) : ['c04'], inconnus : ['c08', 'c17'], écartés par un avenant : ['c09']
```json
{
  "filters": {
    "end_date": {
      "before": "2026-12-31"
    },
    "entity_ids": [
      "groupe_brenalis"
    ]
  }
}
```

**Réponse de l'agent**

> Un seul contrat avec le Groupe Brenalis expire avant la fin 2026 :
>
> *   **Lettre de mission d'audit d'acquisition — Cabinet Morand / Groupe Brenalis (c04)**
>     *   **Date de fin :** 2026-11-30
>     *   **Justification :** L'article 2 stipule que la mission s'achève au plus tard le 30 novembre 2026.
>
> **Notes sur les contrats exclus :**
> *   **c08** et **c17** : Leur situation ne peut pas être déterminée (excluded_unknown).
> *   **c09** : Initialement prévu pour fin 2026, son terme a été reporté au 30 juin 2028 par l'avenant c18.

_1 appel(s) de tool · 58.1 s_

## Lesquels sont régis par un droit étranger ?

**Appel** `search_data_room` → 3 résultat(s) : ['c05', 'c16', 'c20'], inconnus : ['c10']
```json
{
  "filters": {
    "governing_law": {
      "not_in": [
        "droit français"
      ]
    }
  }
}
```

**Réponse de l'agent**

> Voici les contrats régis par un droit étranger :
>
> 1.  **Software License Agreement — Northbeam Analytics / Hydrelle Énergie** (c05)
>     *   **Droit applicable :** Droit new-yorkais.
>     *   **Justification :** Article 8 stipulant que l'accord est régi par les lois de l'État de New York.
>
> 2.  **Contrat d'agence commerciale — Atelier Corvel / Heldin SA (Suisse romande)** (c16)
>     *   **Droit applicable :** Droit suisse.
>     *   **Justification :** Article 9 précisant que le contrat est soumis au droit suisse, notamment aux articles 418a et suivants du Code des obligations.
>
> 3.  **Traduction de courtoisie — Contrat de licence de logiciel Northbeam Analytics / Hydrelle Énergie** (c20)
>     *   **Droit applicable :** Droit new-yorkais.
>     *   **Justification :** Article 8 indiquant que le contrat est régi par le droit de l'État de New York.
>
> *Note : Le contrat c10 est exclu de cette liste car sa situation ne peut pas être déterminée (excluded_unknown).*

_1 appel(s) de tool · 66.1 s_

## Y a-t-il des doublons ?

**Appel** `find_duplicates` → 2 paire(s) de doublons : [['c11', 'c19'], ['c05', 'c20']]
```json
{}
```

**Réponse de l'agent**

> Oui, deux paires de contrats en doublon ont été identifiées :
>
> 1. **Paire 1 (Doublon certain)**
>    - **Contrats** :
>      - `c11` : *Convention d'honoraires — Kessler Aubry Avocats / Soravie Santé*
>      - `c19` : *Convention d'honoraires Kessler Aubry / Soravie*
>    - **Raisons** : Mêmes parties, même type de contrat (prestation de services), mêmes dates de signature (2024-04-15) et de fin (2027-04-14).
>    - **Similarité** : Le texte est identique à 100 %. Il s'agit très probablement d'une duplication de fichier.
>
> 2. **Paire 2 (Doublon probable - Traduction)**
>    - **Contrats** :
>      - `c05` : *Software License Agreement — Northbeam Analytics / Hydrelle Énergie*
>      - `c20` : *Traduction de courtoisie — Contrat de licence de logiciel Northbeam Analytics / Hydrelle Énergie*
>    - **Raisons** : Mêmes parties, même type de contrat (contrat de licence), mêmes dates de signature (2024-10-01) et de fin (2027-09-30).
>    - **Similarité** : La similarité textuelle est de 15 %, ce qui suggère qu'il s'agit d'une version originale et de sa traduction (comme indiqué dans le titre de c20).

_1 appel(s) de tool · 71.2 s_

## Un changement de contrôle du Groupe Brenalis aurait-il des conséquences sur ses contrats ?

**Appel** `search_data_room` → 1 résultat(s) : ['c01'], inconnus : []
```json
{
  "query": "changement de contrôle",
  "filters": {
    "entity_ids": [
      "groupe_brenalis"
    ]
  }
}
```

**Réponse de l'agent**

> Oui, un changement de contrôle du Groupe Brenalis aurait des conséquences sur au moins un de ses contrats :
>
> *   **Contrat de crédit — Banque Orsenne / Groupe Brenalis (c01)**
>     *   **Article 8 — Changement de contrôle** : Si un actionnaire (ou plusieurs agissant de concert) prend le contrôle du Groupe Brenalis, la Banque Orsenne pourra exiger le **remboursement immédiat de l'encours**, sauf si elle y renonce par écrit dans les trente jours.
>
> Ce contrat est régi par le droit français et est en vigueur jusqu'au 2031-01-20.

_1 appel(s) de tool · 46.4 s_
