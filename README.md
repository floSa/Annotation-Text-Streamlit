# Service d'Annotation de Texte

Application Streamlit simple et efficace pour l'annotation de texte (NER - Named Entity Recognition) à partir de fichiers CSV.

![Démo de l'application](demo.gif)

## Fonctionnalités

*   Chargement de fichiers CSV locaux ou depuis le serveur.
*   Interface d'annotation intuitive avec surlignage coloré.
*   Gestion dynamique des labels.
*   Application globale des annotations (annoter une fois, appliquer partout).
*   Sauvegarde automatique des annotations dans le fichier source.
*   Export CSV.

## Prérequis

*   [Docker](https://www.docker.com/) et [Docker Compose](https://docs.docker.com/compose/)
*   Ou Python 3.9+ pour une exécution locale

## Installation et Lancement

### Via Docker (Recommandé)

1.  Cloner ce dépôt.
2.  Lancer le service :
    ```bash
    docker-compose up --build
    ```
3.  Accéder à l'application dans le navigateur : [http://localhost:8501](http://localhost:8501)

### En local (Sans Docker)

1.  Installer les dépendances :
    ```bash
    pip install -r requirements.txt
    ```
2.  Lancer l'application :
    ```bash
    streamlit run app.py
    ```

## Utilisation

1.  **Charger un fichier** : Utiliser le panneau de droite pour téléverser un CSV ou en choisir un dans le dossier `data/`.
2.  **Créer des labels** : Dans le panneau de gauche, ajouter des labels (ex: "ORG", "PERS", "LOC").
3.  **Annoter** :
    *   Sélectionner du texte dans la zone de saisie.
    *   Choisir un label.
    *   Cliquer sur "Valider annotation".
    *   L'annotation sera appliquée à toutes les occurrences de ce texte dans le document si possible.
4.  **Naviguer** : Utiliser les boutons "Précédent" et "Suivant" pour changer de ligne.
5.  **Sauvegarde** : Les annotations sont sauvegardées automatiquement dans le fichier CSV chargé (colonne `annotations`).

## Structure du Projet

*   `app.py` : Code principal de l'application Streamlit.
*   `data/` : Dossier contenant les fichiers CSV à annoter.
*   `docker-compose.yml` : Configuration Docker.
