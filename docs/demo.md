# Démo de bout en bout

Générée le 2026-09-12 22:15 par `python scripts/demo.py`, data room `exemple_data_room.json`, modèle `huihui_ai/qwen3.5-abliterated:27b` (Ollama).
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
> **Notes sur les autres contrats :**
> *   **c08** et **c17** : Leur situation ne peut pas être déterminée (données inconnues).
> *   **c09** : Initialement prévu pour expirer le 30 juin 2026, son terme a été reporté au 30 juin 2028 par l'avenant c18.

_1 appel(s) de tool · 79.5 s_

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

> Les contrats régis par un droit étranger sont les suivants :
>
> *   **c05** – *Software License Agreement — Northbeam Analytics / Hydrelle Énergie* : régi par le **droit new-yorkais** (Article 8).
> *   **c16** – *Contrat d'agence commerciale — Atelier Corvel / Heldin SA (Suisse romande)* : régi par le **droit suisse** (Article 9).
> *   **c20** – *Traduction de courtoisie — Contrat de licence de logiciel Northbeam Analytics / Hydrelle Énergie* : régi par le **droit new-yorkais** (Article 8).
>
> **Note :** Le contrat **c10** est exclu de cette liste car sa situation ne peut pas être déterminée (données manquantes sur la loi applicable).

_1 appel(s) de tool · 54.5 s_

## Y a-t-il des doublons ?

**Appel** `search_data_room` → 20 résultat(s) : ['c01', 'c02', 'c03', 'c04', 'c05', 'c06', 'c07', 'c08', 'c09', 'c10', 'c11', 'c12', 'c13', 'c14', 'c15', 'c16', 'c17', 'c18', 'c19', 'c20'], inconnus : []
```json
{
  "filters": {}
}
```

**Réponse de l'agent**

> Oui, il y a des doublons dans la data room. Voici les contrats identifiés comme tels :
>
> 1.  **Doublon de contrat de prestation de services (Convention d'honoraires)**
>     *   **c11** : *Convention d'honoraires — Kessler Aubry Avocats / Soravie Santé*
>     *   **c19** : *Convention d'honoraires Kessler Aubry / Soravie*
>     *   **Justification** : Ces deux contrats concernent les mêmes parties (Kessler Aubry Avocats et Soravie Santé), le même type de contrat (prestation de services), et partagent la même date de signature (2024-04-15) et la même date de fin (2027-04-14). Le nom du fichier de c19 inclut "(1)", suggérant une duplication.
>
> 2.  **Doublon de contrat de licence (Traduction)**
>     *   **c05** : *Software License Agreement — Northbeam Analytics / Hydrelle Énergie*
>     *   **c20** : *Traduction de courtoisie — Contrat de licence de logiciel Northbeam Analytics / Hydrelle Énergie*
>     *   **Justification** : Ces deux contrats impliquent les mêmes parties (Northbeam Analytics et Hydrelle Énergie), sont du même type (contrat de licence), et ont les mêmes dates de signature (2024-10-01) et de fin (2027-09-30). Le titre de c20 indique qu'il s'agit d'une "Traduction de courtoisie" du contrat c05.
>
> Aucun autre doublon n'a été identifié parmi les 20 contrats répertoriés.

_1 appel(s) de tool · 122.9 s_

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
> Aucun autre contrat n'a été identifié comme contenant une clause spécifique sur le changement de contrôle pour le Groupe Brenalis dans cette recherche.

_1 appel(s) de tool · 43.7 s_
