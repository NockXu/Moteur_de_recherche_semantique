# Accueil

## Sommaire

- [Accueil](#accueil)
  - [Sommaire](#sommaire)
  - [Description du projet](#description-du-projet)
  - [Installation](#installation)
    - [Prérequis](#prérequis)
    - [Exemple d'environement avec conda](#exemple-denvironement-avec-conda)
    - [Récupérer le dépot github](#récupérer-le-dépot-github)
    - [Etape d'installation](#etape-dinstallation)
  - [Documentation](#documentation)
  - [Lancer les tests](#lancer-les-tests)
  - [Lancer le programme](#lancer-le-programme)

## Description du projet

Ce projet consiste à développer un moteur de recherche sémantique d'images basé sur des embeddings et une architecture hybride combinant une base de données relationnelle et un index vectoriel.

L'application permet d'importer des collections d'images, d'en extraire automatiquement des descriptions, des mots-clés et des représentations vectorielles, puis d'effectuer des recherches en langage naturel afin de retrouver des images à partir de leur contenu sémantique plutôt qu'à partir d'une simple correspondance de mots-clés.

Le moteur propose également un système de recherche permettant de combiner plusieurs requêtes à l'aide d'un arbre de recherche pondéré afin d'affiner les résultats obtenus.

Enfin, une fonctionnalité de segmentation d'images basée sur le modèle [SAM3](https://ai.meta.com/research/sam3/) permet d'identifier des éléments précis au sein d'une image à partir de prompts textuels et de zones d'intérêt définies par l'utilisateur.

## Installation

Avant toute chose, je vous recommande d'utiliser un environnement Python dédié. En effet, les versions des bibliothèques utilisées dans ce projet ne correspondent pas nécessairement aux dernières versions disponibles. Utiliser un environnement virtuel permet donc d'éviter d'avoir à modifier régulièrement les versions de vos dépendances installées. Cela garantit une meilleure compatibilité lors de l'installation et de l'exécution du projet.

### Prérequis

- Python 3.12 ou version supérieure (les développements et les tests ont été réalisés avec Python 3.12.13).
- Une carte graphique compatible CUDA (pour l'utilisation de GPU)
- Windows (certaines dépendances sont spécifiques à Windows, mais il devrait exister des équivalents sous Linux).

### Exemple d'environement avec conda

Si vous voulez utiliser conda, voici les commandes pour mettre en place un environement

```powershell

conda create -n MoteurRechercheSementique python=3.12.13

conda activate MoteurRechercheSementique

```

[Lien vers l'installation de miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install/overview)

### Récupérer le dépot github

```powershell
git clone https://github.com/NockXu/Moteur_de_recherche_semantique.git
```

### Etape d'installation

1. Installer les dépandances pip

```bash
pip install -r requirements.txt
```

1. Installer PyTorch qui prend en charge CUDA

```bash
pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
```

1. Cloner le dépôt git de sam3 et installer les dépendances

```bash
cd vision
git clone https://github.com/facebookresearch/sam3.git
cd sam3
pip install -e .
cd ../..
```

1. Installer les dépendances manquantes de SAM3

```bash
pip install -r requirementsv2.txt
```

> Ce deuxième `requirements` existe parce que le premier est créé automatiquement à partir d'un fichier `requirements.in`, et certaines versions des bibliothèques ne sont pas écrasées lors de la génération du fichier `requirements`.

1. Accès au model hugging face

> **Attention** : il est important de noter que si votre carte graphique ne supporte pas CUDA, vous ne pourrez probablement pas utiliser les fonctionnalités SAM3.

Allez sur la page du [dépot](https://huggingface.co/facebook/sam3) du model pour vous y inscrire est avoir l'accès

Ensuite vous devez vous connecter à hugging face sur votre machine:

- Acceder à vous tokens:
![Comment acceder au tokens](./documentation/huggingface1.png)

- Créer un nouveau token:
![Page liste de token](./documentation/token_list_page.png)

- Créer un token de type "read":
![page de création du token](./documentation/token_creation.png)

Enfin connecter vous à hugging face sur votre machine via le code que le token à créer:

```bash
hf auth login

    _|    _|  _|    _|    _|_|_|    _|_|_|  _|_|_|  _|      _|    _|_|_|      _|_|_|_|    _|_|      _|_|_|  _|_|_|_|
    _|    _|  _|    _|  _|        _|          _|    _|_|    _|  _|            _|        _|    _|  _|        _|
    _|_|_|_|  _|    _|  _|  _|_|  _|  _|_|    _|    _|  _|  _|  _|  _|_|      _|_|_|    _|_|_|_|  _|        _|_|_|
    _|    _|  _|    _|  _|    _|  _|    _|    _|    _|    _|_|  _|    _|      _|        _|    _|  _|        _|
    _|    _|    _|_|      _|_|_|    _|_|_|  _|_|_|  _|      _|    _|_|_|      _|        _|    _|    _|_|_|  _|_|_|_|

    A token is already saved on your machine. Run `hf auth whoami` to get more information or `hf auth logout` if you want to log out.
    Setting a new token will erase the existing one.
    To log in, `huggingface_hub` requires a token generated from https://huggingface.co/settings/tokens .
Token can be pasted using 'Right-Click'.
Enter your token (input will not be visible):
```

[Voir plus sur l'authentication sur hugging face](https://huggingface.co/docs/huggingface_hub/en/quick-start#authentication)

[Voir plus sur l'installation de sam3](https://github.com/facebookresearch/sam3)

## Documentation

[Lien vers la documentation](./documentation/index.md)

[Lien vers le site](https://nockxu.github.io/Moteur_de_recherche_semantique/)

## Lancer les tests

Voici les commandes pour lancer les tests:

```powershell
coverage erase
coverage run -m unittest discover
coverage report
coverage html
```

> commande à réaliser à la racine du projet

## Lancer le programme

Voici la commande pour lancer le programme principale:

```powershell
python main.py
```

> commande à réaliser à la racine du projet
