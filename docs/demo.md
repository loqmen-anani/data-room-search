# Démo de bout en bout

Générée le 2026-09-12 20:01 par `python scripts/demo.py`, data room `exemple_data_room.json`, modèle `huihui_ai/qwen3.5-abliterated:27b` (Ollama).
Pour chaque question : les appels de tools choisis par l'agent, puis sa réponse.

## Quels contrats avec le Groupe Brenalis expirent avant fin 2026 ?

**Appel** `search_data_room` → 2 résultat(s) : ['c04', 'c09'], inconnus : ['c08', 'c17']
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

> Voici les contrats impliquant le Groupe Brenalis qui expirent avant la fin de l'année 2026 :
>
> *   **Lettre de mission d'audit d'acquisition — Cabinet Morand / Groupe Brenalis (c04)**
>     *   **Date de fin :** 30 novembre 2026.
>     *   **Justification :** L'article 2 stipule que la mission s'achève au plus tard le 30 novembre 2026.
>
> *   **Contrat de fourniture d'électricité — Hydrelle Énergie / Groupe Brenalis (c09)**
>     *   **Date de fin :** 30 juin 2026.
>     *   **Justification :** L'article 5 précise que la fourniture prend fin le 30 juin 2026 sans renouvellement tacite.
>
> **Note :** Deux autres contrats (c08 et c17) impliquant le Groupe Brenalis ont été exclus de cette liste car leur date de fin n'est pas déterminée dans les métadonnées disponibles.

_1 appel(s) de tool · 100.5 s_

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
> *   **c05** – *Software License Agreement — Northbeam Analytics / Hydrelle Énergie* : régi par le **droit new-yorkais** (Article 8).
> *   **c16** – *Contrat d'agence commerciale — Atelier Corvel / Heldin SA (Suisse romande)* : régi par le **droit suisse** (Article 9).
> *   **c20** – *Traduction de courtoisie — Contrat de licence de logiciel Northbeam Analytics / Hydrelle Énergie* : régi par le **droit new-yorkais** (Article 8).
>
> **Note :** Le contrat **c10** est exclu de cette liste car sa loi applicable n'a pas pu être déterminée.

_1 appel(s) de tool · 59.3 s_

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
>     *   **c11** : *Convention d'honoraires — Kessler Aubry Avocats / Soravie Santé* (Signé le 2024-04-15, fin le 2027-04-14).
>     *   **c19** : *Convention d'honoraires Kessler Aubry / Soravie* (Signé le 2024-04-15, fin le 2027-04-14).
>     *   **Justification** : Ces deux contrats concernent les mêmes parties (Kessler Aubry Avocats et Soravie Santé), ont la même date de signature, la même date de fin et le même type de contrat. Le nom du fichier de c19 inclut "(1)", suggérant une duplication.
>
> 2.  **Doublon de contrat de licence (Traduction)**
>     *   **c05** : *Software License Agreement — Northbeam Analytics / Hydrelle Énergie* (Signé le 2024-10-01, fin le 2027-09-30).
>     *   **c20** : *Traduction de courtoisie — Contrat de licence de logiciel Northbeam Analytics / Hydrelle Énergie* (Signé le 2024-10-01, fin le 2027-09-30).
>     *   **Justification** : Ces deux contrats impliquent les mêmes parties (Northbeam Analytics et Hydrelle Énergie), avec des dates de signature et de fin identiques. Le titre de c20 indique qu'il s'agit d'une "Traduction de courtoisie" du contrat c05, ce qui constitue un doublon fonctionnel.
>
> 3.  **Doublon potentiel lié à une cession de parts et une garantie**
>     *   **c08** : *Acte de cession de parts sociales — M. Étienne Morand / Groupe Brenalis* (Signé le 2025-01-31).
>     *   **c14** : *Convention de garantie d'actif et de passif — M. Étienne Morand / Groupe Brenalis* (Signé le 2025-01-31).
>     *   **Justification** : Bien que les types de contrats soient différents (cession de parts vs garantie), ils concernent les mêmes parties et la même date de signature. Ils sont probablement liés à la même opération de cession, mais ne constituent pas un doublon strict au sens de la redondance de contenu (comme c11/c19 ou c05/c20).
>
> En résumé, les paires **c11/c19** et **c05/c20** sont des doublons clairs.

_1 appel(s) de tool · 179.9 s_

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
>     *   **Conséquence :** En cas de changement de contrôle, la Banque Orsenne se réserve le droit d'exiger le **remboursement immédiat de l'encours** du prêt.
>     *   **Justification :** L'**Article 8** stipule que la banque peut exercer cette option, sauf si elle y renonce par écrit dans un délai de trente jours suivant le changement de contrôle.

_1 appel(s) de tool · 45.9 s_
