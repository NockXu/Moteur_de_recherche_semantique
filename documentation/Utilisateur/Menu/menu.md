# Menus de l'application

Les menus de l'application est composé de quatre parties :

![Fichier, Outils, Styles, Langue](menu_global.png)

## Fichier

Ce menu regroupe les fonctionnalités d'importation et d'exportation des données du jeu de données.

![Menu Fichier](menu_file.png)

### Importer/Exporter

L'importation peut être effectuée de deux manières :

- importation d'un fichier contenant des jeux de données définis.
- importation d'un fichier sans jeux de données.

![Menu Fichier Importer](import1.png)

#### Format JSON

Schéma sans jeu de données (simple)
```json

{
  <nom de l'image>: {
    "id": <nom de l'image>,
    "path": <chemin de l'image>,
    "description": <description>,
    "keywords": [
      <mot clé 1>,
      <mot clé 2>,
      ...,
      <mot clé n>
    ],
    "embedding": [ ... ]
  }
}

```

Schéma avec jeu de données (intégral)

```json

{
  <nom de l'image>: {
    "id": <nom de l'image>,
    "path": <chemin de l'image>,
    "description": <description>,
    "keywords": [
      <mot clé 1>,
      <mot clé 2>,
      ...,
      <mot clé n>
    ],
    "dataset": <nom jeu de données>,
    "embedding": [ ... ]
  }
}
```

#### Importation sans datasets

Il existe deux mode d'importation sans dataset:

la fusion de toute les images en 1 dataset

![Dataset_fusion](Dataset_fusion.png)

un dataset par dossier d'images

![Dataset mult](Dataset_mutl.png)

#### Importation avec datasets

![Dataset_present](Dataset_present.png)

### Exporter

De la même manière l'export fonctionne de deux manières:
- Avec datasets
- Sans datasets

![alt text](export.png)

## Outils

La partie outils est simple, il y a une option qui permet d'afficher/caché l'outil d'import d'image

![Image outil](outils.png)

## Style

La partie de style permet de changer le thème actuelle de l'application

![Image style](style.png)

Double cliquez sur un thème et il s'applique et s'enregistre

![alt text](selection_theme.png)

## Langue

L'option permet de changer la langue parmit toute les langues disponibles

![alt text](langue1.png)

![alt text](langue2.png)