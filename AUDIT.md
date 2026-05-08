# Audit & Stratégie d'amélioration — Annotation-Text-Streamlit

**Date :** 2026-05-08
**Périmètre :** [app.py](app.py), [utils.py](utils.py), [dockerfile](dockerfile), [docker-compose.yml](docker-compose.yml), [requirements.txt](requirements.txt), [README.md](README.md), [QUICKSTART.md](QUICKSTART.md), `.env`, [data/annotations.csv](data/annotations.csv)
**Verdict global :** prototype fonctionnel cohérent avec une bonne UX de base. **Pas prêt pour la production** : `.env` versionné avec credentials, aucun test, aucune CI, plusieurs bugs algorithmiques (BIO/BILOU), `except` nus qui masquent des erreurs, et UX qui force le copier-coller pour sélectionner. Effort estimé pour atteindre un MVP « propre » : **~3-4 semaines / 1 dev**.

---

## 1. Synthèse — Forces & faiblesses

### Forces
- Périmètre fonctionnel clair : NER sur CSV, export multi-format (Span JSON / IOB / BILOU).
- Séparation embryonnaire entre UI ([app.py](app.py)) et logique ([utils.py](utils.py)).
- Docker + docker-compose fournis dès le départ.
- Application globale d'une annotation à toutes les occurrences = bonne intuition produit.
- Démo gif présente, README + QUICKSTART = onboarding correct.

### Faiblesses majeures
- **Sécurité** : `.env` committé avec creds par défaut, aucun `.gitignore`, `unsafe_allow_html` injecté avec des labels saisis par l'utilisateur (XSS si déploiement multi-user).
- **Qualité** : 5 `try/except` nus, aucune type hint, aucune docstring rigoureuse, code mort (`convert_to_iob` est une identité).
- **Algo** : conversion BIO bug sur les annotations qui chevauchent partiellement un token, BILOU se base sur `endswith(label)` (faux si deux labels partagent un suffixe), suppression d'annotation par index `i` qui peut viser la mauvaise entrée.
- **UX** : sélection texte = champ texte à remplir manuellement (gros frein), pas de raccourcis clavier, pas d'indicateur de progression, typo « Extrat » dans la sidebar, pas de filtre lignes vides/annotées.
- **Robustesse** : sauvegarde CSV synchrone à chaque navigation (I/O lourd), `iloc[0]` partout en utils mais `'text'` recherchée en app → incohérence.
- **Process** : zéro test, zéro CI, pas de linter, pas de pre-commit, pas de lockfile, Python 3.9 (EOL octobre 2025).

---

## 2. Findings détaillés (par priorité)

### 🔴 P0 — Critique (à traiter avant tout autre commit)

| # | Finding | Fichier | Impact |
|---|---|---|---|
| P0-1 | `.env` committé avec `ADMIN_PASSWORD=admin` | `.env` + git history | Fuite de credentials publique. Le fichier est sur GitHub. |
| P0-2 | Aucun `.gitignore` | racine | Risque répété : `__pycache__`, `.venv`, `*.csv` privés, secrets futurs. |
| P0-3 | XSS potentielle via labels | [app.py:175-180](app.py#L175-L180) | Un label `<img src=x onerror=...>` est rendu via `unsafe_allow_html=True`. Bénin en local, critique en multi-user. |
| P0-4 | `except:` nus qui avalent toute exception | [app.py:71](app.py#L71), [app.py:214](app.py#L214), [utils.py:132](utils.py#L132), [utils.py:158](utils.py#L158) | Bugs silencieux, debug très difficile. |

**Action immédiate P0-1** : révoquer/changer toute donnée sensible que `.env` aurait pu contenir, retirer `.env` du tracking, ré-écrire l'historique git (`git filter-repo --path .env --invert-paths`) puis force-push (le faire en accord avec le user puisque c'est destructif).

### 🟠 P1 — Haute priorité

| # | Finding | Fichier | Impact |
|---|---|---|---|
| P1-1 | Bug BILOU : `next_tag.endswith(label)` matche faussement deux labels qui partagent un suffixe (ex `LOC` et `PERS_LOC`) | [utils.py:109](utils.py#L109), [utils.py:114](utils.py#L114) | Exports corrompus. |
| P1-2 | Bug suppression annotation : `pop(i)` après que la liste a été triée par `start` ailleurs | [app.py:272](app.py#L272) | Supprime potentiellement la mauvaise annotation. |
| P1-3 | Annotation appliquée globalement sans confirmation ni preview | [app.py:230-249](app.py#L230-L249) | Action destructive irréversible (pas d'undo). |
| P1-4 | `save_current_state()` réécrit tout le CSV à chaque navigation | [app.py:35-49](app.py#L35-L49), [app.py:197](app.py#L197), [app.py:205](app.py#L205) | I/O lourd, lent sur > 1000 lignes. |
| P1-5 | Aucun test (unitaire, intégration, UI) | — | Toute refonte = risque régressions invisibles. |
| P1-6 | Python 3.9 dans Dockerfile (EOL atteint) | [dockerfile:1](dockerfile#L1) | Pas de patchs sécurité, libs récentes pas garanties. |
| P1-7 | Pas d'auth alors que `.env` la suggère | — | Fonctionnalité orpheline ; à implémenter ou supprimer du `.env`. |

### 🟡 P2 — Moyenne priorité

| # | Finding | Fichier | Impact |
|---|---|---|---|
| P2-1 | UX de sélection : copier-coller manuel | [app.py:225](app.py#L225) | Friction majeure. Solution : composant custom JS, `streamlit-text-annotation`, ou intégration `st-annotated-text` interactive. |
| P2-2 | Incohérence colonne texte : `iloc[0]` en utils vs `'text'` en app | [utils.py:126](utils.py#L126), [utils.py:154](utils.py#L154), [app.py:212](app.py#L212) | Comportement imprévisible si la 1ʳᵉ colonne n'est pas le texte. |
| P2-3 | `convert_to_iob` est l'identité (code mort) | [utils.py:84-86](utils.py#L84-L86) | À supprimer. |
| P2-4 | `align_tokens_with_annotations` en O(n×m) | [utils.py:65-80](utils.py#L65-L80) | Lent sur longs textes. Solution : sweep linéaire avec pointeur. |
| P2-5 | Tokenizer regex naïf : ignore tirets, apostrophes complexes, unicode | [utils.py:38](utils.py#L38), [utils.py:57](utils.py#L57) | Tokens incorrects sur français/multilingue. |
| P2-6 | Aucun feedback de modification non sauvegardée | UI globale | L'utilisateur peut quitter en pensant que c'est sauvegardé. |
| P2-7 | Typo « Extrat » dans la sidebar | [app.py:147](app.py#L147) | Petit, mais visible. |
| P2-8 | `version: '3.8'` dans docker-compose.yml = déprécié | [docker-compose.yml:1](docker-compose.yml#L1) | À retirer. |
| P2-9 | Image Docker = root par défaut | [dockerfile](dockerfile) | Bonne pratique : `USER appuser`. |
| P2-10 | Pas de HEALTHCHECK | [dockerfile](dockerfile) | Compose ne sait pas si l'app est vivante. |

### 🟢 P3 — Basse priorité (nice-to-have)

- Pas de `pyproject.toml` (PEP 621), pas de lockfile (`uv.lock` / `requirements.lock`).
- Pas de `LICENSE` à la racine (le repo GitHub en mentionne une, mais le fichier devrait être présent).
- Pas de CONTRIBUTING.md ni de CHANGELOG.md.
- Pas de structure `src/annotation_tool/` — tout en racine.
- `from io import StringIO` dans [app.py:6](app.py#L6) jamais utilisé.
- `import streamlit as st` etc. → pas de séparation imports stdlib / tiers / locaux.
- Pas de stats du dataset (% lignes annotées, distribution labels).
- Pas de raccourcis clavier (← / → / 1-9 pour labels).
- Pas de filtre « lignes non annotées ».
- Schéma de labels non typé : juste un nom + couleur. Pas de description, pas de hiérarchie.

---

## 3. Stratégie de développement — Roadmap en 4 phases

L'ordre des phases est volontaire : **on stabilise avant d'enrichir**. Chaque phase a un livrable testable.

### Phase 0 — Sécurité & assainissement (1-2 jours)
**Objectif** : ne plus avoir de honte à pointer le repo en public.

1. Créer un `.gitignore` standard Python (gitignore.io → Python + VSCode + macOS).
2. `git rm --cached .env`, ajouter `.env` au `.gitignore`, créer un `.env.example` documenté.
3. Réécrire l'historique pour purger `.env` : `git filter-repo --path .env --invert-paths` + force-push (à valider avec toi).
4. Renommer `dockerfile` → `Dockerfile` (convention), ajouter user non-root et HEALTHCHECK, passer à Python 3.12-slim.
5. Échapper les labels rendus en HTML : `html.escape(label)` ou retirer `unsafe_allow_html` via CSS classes propres.
6. Remplacer chaque `except:` nu par `except SpecificError as e:` avec log.
7. Ajouter un `LICENSE` (MIT/Apache-2.0 selon ta préférence).

**Livrable** : repo propre, pas de secret, pas d'`except` nu.

### Phase 1 — Fondations qualité (3-5 jours)
**Objectif** : empêcher toute régression future.

1. Migrer vers `pyproject.toml` + `uv` (rapide, moderne, lockfile natif).
2. Restructurer en package : `src/annotation_tool/{app,core,io,export}.py` + `tests/`.
3. Outils dev : `ruff` (lint + format), `mypy` (typage progressif), `pre-commit`.
4. Type hints partout dans `core` et `export` (UI peut rester sans).
5. Tests unitaires (`pytest`) sur les fonctions pures :
   - `tokenize`, `align_tokens_with_annotations`, `convert_to_bilou`, `export_json_span`, `export_to_conll`.
   - Cas limites : annotations qui chevauchent, labels avec tirets, texte vide, CSV malformé.
6. CI GitHub Actions : `ruff check`, `mypy`, `pytest --cov`, build Docker.
7. Test Streamlit end-to-end avec [`streamlit.testing.v1.AppTest`](https://docs.streamlit.io/library/api-reference/app-testing) (charger CSV, ajouter label, valider annotation, exporter).

**Livrable** : badge CI verte, couverture > 70 % sur `core`/`export`.

### Phase 2 — Corrections fonctionnelles & UX (1 semaine)
**Objectif** : l'outil fait ce qu'il prétend faire, sans surprise.

1. **Fix BILOU** (P1-1) : remplacer `endswith(label)` par split rigoureux du tag.
2. **Fix suppression annotation** (P1-2) : supprimer par identifiant (uuid attribué à la création) plutôt que par index de liste.
3. **Save asynchrone / debounce** (P1-4) : sauvegarder uniquement à la sortie ou bouton « Sauvegarder » + indicateur « modifications non sauvées ».
4. **Choix de la colonne texte** (P2-2) : selectbox au chargement « Quelle colonne contient le texte ? ».
5. **Confirmation + preview** sur l'application globale (P1-3) : afficher « Cette annotation sera appliquée à N lignes. Confirmer ? ».
6. **Undo** (au moins 1 niveau) sur ajout/suppression d'annotation.
7. **Tokenizer** : remplacer la regex par `spacy` (modèle FR + multilingue) ou au moins gérer apostrophes, tirets, unicode propre.
8. Petits fix : typo « Extrat », imports inutilisés, `convert_to_iob` mort.

**Livrable** : v1.0 utilisable en interne sans accompagnement.

### Phase 3 — Confort & productivité (1 semaine, optionnel)
**Objectif** : transformer l'outil en plaisir d'usage.

1. **Sélection souris native** : intégrer un composant custom (ex : [`st-annotation-tool`](https://github.com/JohnSnowLabs) ou écrire un composant Streamlit minimal en JS) pour cliquer-glisser sur le texte au lieu du copier-coller.
2. **Raccourcis clavier** : `←`/`→` navigation, `1-9` labels rapides, `Cmd+Z` undo (via `streamlit-keyboard-events` ou composant maison).
3. **Stats dataset** : panneau « Vue d'ensemble » avec % annoté, distribution des labels, lignes non annotées.
4. **Filtres** : « afficher uniquement les lignes non annotées », recherche texte, jump-to-line.
5. **Templates de labels** : sauvegarder/charger un schéma (JSON) avec label, couleur, description, hot-key.
6. **Auth simple** (si toujours pertinent) : `streamlit-authenticator` ou reverse-proxy avec basic auth — décider à ce moment si le multi-user est dans le scope.
7. **Imports/exports supplémentaires** : JSONL, CoNLL en entrée, mapping de colonnes flexible.

**Livrable** : v1.1, retours utilisateurs collectés.

---

## 4. Quick wins (à faire dans la journée, < 2h chacun)

Si tu veux commencer petit avant la Phase 0 complète :

1. ✏️ Corriger « Extrat » → « Export » dans [app.py:147](app.py#L147).
2. 🗑️ Supprimer `from io import StringIO` (inutilisé) en [app.py:6](app.py#L6).
3. 🗑️ Supprimer `convert_to_iob` (identité) dans [utils.py:84-86](utils.py#L84-L86).
4. 🐍 Passer Python 3.9 → 3.12 dans [dockerfile:1](dockerfile#L1).
5. 📦 Retirer `version: '3.8'` de [docker-compose.yml:1](docker-compose.yml#L1).
6. 🚫 Créer un `.gitignore` minimal et y mettre `.env`, `__pycache__/`, `.venv/`, `*.pyc`.

Note : **ces quick wins ne remplacent PAS la Phase 0** — il faut quand même purger `.env` de l'historique git.

---

## 5. Décisions à prendre avec toi

Avant d'attaquer, je veux ton arbitrage sur :

- **Réécriture d'historique git** : OK pour `git filter-repo` + force-push (destructif mais nécessaire pour purger `.env`) ?
- **Multi-user / auth** : on garde l'idée (et on l'implémente Phase 3) ou on supprime `.env` et on positionne l'app comme « single-user local » ?
- **Outillage Python** : `uv` (recommandé, rapide, moderne) ou tu préfères `poetry` / `pip-tools` ?
- **Composant de sélection texte** : OSS existant (rapide, mais moins de contrôle) ou composant Streamlit maison (effort +++ mais sur mesure) ?
- **Ambition cible** : outil interne (single-user local, exports propres) ou produit (multi-user, déploiement, collab) ? Cela change la profondeur des Phases 2-3.

---

## 6. Effort estimé (1 dev solo)

| Phase | Effort | Cumul |
|---|---|---|
| Phase 0 — Sécurité | 1-2 j | 1-2 j |
| Phase 1 — Fondations qualité | 3-5 j | 4-7 j |
| Phase 2 — Corrections fonctionnelles | ~5 j | 9-12 j |
| Phase 3 — Confort (optionnel) | ~5 j | 14-17 j |

**MVP propre = fin Phase 2.** Phase 3 selon ambition produit.
