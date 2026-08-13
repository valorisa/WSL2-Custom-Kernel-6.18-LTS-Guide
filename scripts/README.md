# Scripts de maintenance du dépôt

Ce dossier contient des utilitaires destinés à maintenir la qualité de la documentation Markdown d’un dépôt GitHub.

## `fix_markdownlint.py`

### Objectif

Lors de l’ajout ou de la modification de fichiers Markdown, certaines erreurs de formatage peuvent faire échouer les contrôles de qualité ou le pipeline d’intégration continue utilisant `markdownlint-cli2`.

L’option `--fix` de markdownlint ne corrige qu’une partie des règles. Ce script Python automatise notamment la correction des problèmes suivants :

- MD026 : suppression de la ponctuation finale dans les titres, par exemple `# Titre.` devient `# Titre`.
- MD032 : ajout des lignes vides nécessaires autour des listes.
- MD034 : encapsulation des URL nues entre chevrons, par exemple `https://example.com` devient `<https://example.com>`.

Ces règles correspondent aux contrôles documentés par markdownlint pour la ponctuation des titres, l’espacement autour des listes et les URL nues [web:1][web:2].

### Prérequis

- Python 3.6 ou version ultérieure.
- Aucune dépendance externe.
- La bibliothèque standard Python suffit.

### Utilisation

Les commandes suivantes doivent être exécutées depuis la racine du dépôt.

Pour corriger un dossier entier :

    python3 scripts/fix_markdownlint.py docs/

Pour corriger un fichier unique :

    python3 scripts/fix_markdownlint.py README.md

Pour corriger tous les fichiers Markdown du dépôt :

    python3 scripts/fix_markdownlint.py .

### Workflow recommandé

1. Ajouter ou modifier les fichiers Markdown du dépôt.
2. Exécuter le script sur les fichiers concernés ou sur l’ensemble du dépôt :

       python3 scripts/fix_markdownlint.py .

3. Vérifier les fichiers Markdown avec markdownlint :

       npx -y markdownlint-cli2 "**/*.md"

4. Examiner les modifications produites.
5. Commiter les changements.
6. Pousser la branche vers le dépôt distant.

Le contrôle final avec markdownlint reste nécessaire, car le script ne corrige qu’un sous-ensemble des règles de formatage.
