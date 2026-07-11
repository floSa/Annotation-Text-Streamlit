# Cadrage — Annotation-Text-Streamlit

> Le **POURQUOI** du projet. Le **COMMENT** (composants, flux, décisions techniques) est
> dans [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Pitch

Outil web léger pour **annoter du texte en NER** à partir d'un simple fichier CSV, sans
infrastructure lourde ni base de données. Trois capacités :

1. **Charger** un corpus CSV (local ou upload) et reprendre des annotations existantes.
2. **Annoter** interactivement en surlignant des fragments par label, avec application
   automatique à toutes les occurrences du corpus.
3. **Exporter** vers les formats standards de la chaîne NLP : **Span JSON**, **IOB** et
   **BILOU** (CoNLL).

Cas d'usage « golden » : constituer rapidement un jeu de données annoté (ex. corpus de
recettes → labels `action` / `ingrédient`, cf. [data/annotations.csv](../data/annotations.csv))
pour entraîner ou évaluer un modèle NER.

---

## 2. Objectifs & périmètre

**Dans le périmètre (actuel)** :
- Annotation NER sur CSV mono-colonne texte.
- Gestion dynamique des labels (ajout, couleur automatique).
- Persistance automatique dans le CSV source.
- Exports Span JSON / IOB / BILOU.
- Déploiement local (Docker ou `uv`).

**Hors périmètre (état actuel du code)** :
- **Multi-utilisateur / authentification** — l'app est pensée single-user local.
- **Sélection souris native** — l'annotation passe par un champ de saisie de fragment.
- **Undo / historique** — pas de retour arrière sur une annotation.
- **Formats d'entrée autres que CSV `;`** (pas de JSONL, pas de CoNLL en entrée).

---

## 3. Contraintes (fermes)

| Contrainte | Détail |
|---|---|
| Licences | Open-source uniquement (dépendances MIT / Apache-2.0 / BSD) |
| Déploiement | Local / on-prem, un seul conteneur, port `8501` |
| Runtime | Python `>=3.12` |
| Format d'échange | CSV séparé par `;`, colonne `annotations` en JSON |

---

## 4. Hypothèses

<!-- Hypothèses non lisibles directement dans le code. -->
- **Corpus répétitif** : l'application globale d'une annotation à toutes les occurrences
  suppose qu'annoter partout le même fragment est souhaitable. Vrai sur un corpus
  homogène (recettes) ; **à remettre en cause** sur un corpus où un même mot change de
  sens selon le contexte. `<à confirmer>` selon le public visé.
- **Fichiers de taille modérée** : la réécriture complète du CSV à chaque action suppose
  des corpus de quelques centaines à ~1000 lignes. `<à confirmer>`.
- **Usage local de confiance** : l'échappement HTML atténue l'XSS, mais l'absence d'auth
  suppose un environnement non hostile.
- **Public visé** : `<à confirmer>` (auto-usage / recruteur / collègue). Le niveau de la
  doc est tenu factuel par défaut.

---

## 5. Stack technique

| Brique | Choix | Licence |
|---|---|---|
| Interface web | Streamlit | Apache-2.0 |
| Données | pandas | BSD-3-Clause |
| Rendu annotations | st-annotated-text | Apache-2.0 (`<à confirmer>` — voir README §Licences) |
| Runtime | Python 3.12 | PSF |
| Dépendances | uv + `uv.lock` | Apache-2.0 / MIT |
| Conteneur | Docker (`python:3.12-slim`) | — |

---

## 6. Décisions

**Figées ✅**
- **Deux fichiers, logique isolée** : `utils.py` (pur, testé) + `app.py` (UI) plutôt
  qu'un monolithe, pour la testabilité.
- **CSV comme format pivot** : lisible, versionnable, sans base de données.
- **uv** comme gestionnaire de dépendances plutôt que pip/poetry, pour la reproductibilité
  (lockfile natif) et la vitesse.
- **Python 3.12** (l'audit signalait 3.9 EOL, désormais corrigé).

**À trancher 🔲**
- **Ambition cible** : outil interne single-user ou produit multi-user collaboratif ?
  Détermine l'ajout d'auth et le déplacement de la persistance vers une base. Reco par
  défaut : rester single-user local. `<à confirmer>`.
- **Sélection texte** : garder le copier-coller ou investir dans un composant souris
  custom ? Reco par défaut : composant custom si l'usage se généralise.

---

## 7. Roadmap

L'historique et le détail priorisé vivent dans [AUDIT.md](../AUDIT.md) (Phases 0 à 3).
Synthèse :

0. **Sécurité & assainissement** — `.gitignore`, retrait `.env`, Dockerfile durci, `LICENSE`. ✅
1. **Fondations qualité** — `pyproject.toml` + uv, ruff/mypy/pytest, CI. ✅ *(branche `chore/phase1-foundations`)*
2. **Corrections fonctionnelles & UX** — fix BILOU, suppression par identifiant, save débounce, choix de colonne, confirmation + undo, tokenizer. 🔲
3. **Confort & productivité** — sélection souris, raccourcis clavier, stats dataset, filtres. 🔲

---

## 8. Stratégie de tests

- **Unitaire** sur la logique pure (`utils.py`) : chaque fonction d'export et
  d'alignement, avec cas limites (JSON invalide, unicode, labels à suffixe partagé).
- **Smoke test** de l'app Streamlit (`AppTest`) : démarrage sans exception + landing page.
- Couverture mesurée sur `utils` (`app.py` exclu). Détail : [ARCHITECTURE.md §7](ARCHITECTURE.md#7-tests--ci).

Non couvert (à faire, Phase 2) : tests d'interaction bout-en-bout (charger un fichier,
valider une annotation, exporter) qui nécessitent de mocker `file_uploader` et le
filesystem.

---

## 9. Références

- [AUDIT.md](../AUDIT.md) — audit qualité daté et roadmap détaillée (source de la Phase 1).
- [ARCHITECTURE.md](ARCHITECTURE.md) — le COMMENT technique.
- Dépôt : `https://github.com/floSa/Annotation-Text-Streamlit`.
- Standards de sortie : formats **IOB** / **BILOU** (CoNLL), format **span** JSON.
