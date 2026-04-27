# Sujet 1 — Moteur de recherche sémantique d’images avec Ollama

---

**auteur: Rémi Cozot — date: Avril 2026**

---

## Contexte

Les moteurs de recherche classiques sur des collections d’images reposent souvent sur les noms de fichiers, les dossiers, ou des métadonnées saisies manuellement. Cette approche devient vite limitée dès que l’on souhaite retrouver des images à partir de leur **contenu sémantique** : par exemple *“une rue de nuit sous la pluie”*, *“un bureau avec ordinateur et tasse”* ou *“des images montrant un animal”*.

L’objectif de ce projet est de développer un **moteur de recherche sémantique d’images** en s’appuyant sur des modèles exécutés localement avec **Ollama**. L’idée générale est de transformer chaque image en une représentation textuelle exploitable, puis d’indexer ces descriptions dans un espace vectoriel afin de permettre une recherche par similarité.

Le projet permet d’aborder plusieurs notions importantes en IA appliquée :

* modèles de vision-langage,
* embeddings,
* recherche vectorielle,
* structuration d’un pipeline IA complet,
* évaluation d’un système de recherche.

---

## Objectif général

Développer une application capable :

* d’indexer un corpus local d’images ;
* de produire automatiquement une description textuelle de chaque image avec un modèle **vision-language** ;
* de calculer des embeddings sur ces descriptions ;
* de retrouver les images les plus pertinentes à partir d’une requête textuelle ;
* d’afficher les résultats de manière claire et exploitable.

---

## Contraintes techniques

Le projet devra s’appuyer sur les outils suivants :

* **Ollama**
* un modèle **vision-language** de type **Qwen2.5-VL** ou **Qwen3.5-VL**
* un modèle d’embeddings **nomic-embed-text**

Le projet devra fonctionner **en local**, sans dépendance à une API cloud externe.

---

## Principe général du pipeline

Le pipeline attendu est le suivant :

### 1. Constitution du corpus

L’utilisateur choisit un dossier contenant des images :

* `.jpg`
* `.png`
* `.jpeg`
* éventuellement `.webp`

Le programme parcourt ce dossier et construit la liste des images à indexer.

### 2. Analyse visuelle par modèle vision-language

Pour chaque image, le système interroge un modèle de type **Qwen-VL** afin de produire une ou plusieurs sorties textuelles, par exemple :

* une description générale ;
* quelques mots-clés ;
* éventuellement une catégorie probable.

Exemples de consignes possibles au modèle :

* décrire l’image en une ou deux phrases ;
* produire 5 à 10 mots-clés utiles pour la recherche ;
* indiquer les objets ou éléments principaux visibles.

### 3. Construction d’une représentation textuelle

Les sorties du modèle sont ensuite structurées dans une fiche associée à l’image, par exemple :

* chemin du fichier ;
* description courte ;
* mots-clés ;
* date d’indexation ;
* éventuellement score ou informations complémentaires.

Cette étape est importante : le projet ne repose pas sur un embedding visuel natif, mais sur une **représentation textuelle du contenu visuel**.

### 4. Calcul des embeddings

La description textuelle de chaque image est transformée en vecteur via **nomic-embed-text**.

Ces vecteurs seront stockés afin d’éviter de recalculer toute l’indexation à chaque lancement.

### 5. Recherche sémantique

Quand l’utilisateur saisit une requête textuelle :

* la requête est encodée avec le même modèle d’embedding ;
* une similarité est calculée entre le vecteur de la requête et les vecteurs des images ;
* les images sont triées par proximité.

Une mesure simple comme la **similarité cosinus** est suffisante.

### 6. Restitution des résultats

Le système affiche :

* les top-k images les plus proches ;
* leur score de similarité ;
* leur description générée.

---

## Fonctionnalités minimales attendues

Le projet devra au minimum proposer les fonctionnalités suivantes :

### A. Indexation d’un dossier d’images

* sélection d’un dossier ;
* détection des fichiers image ;
* création d’une base locale d’index.

### B. Génération automatique d’une description

* appel au modèle vision-language ;
* stockage de la description produite.

### C. Calcul et stockage des embeddings

* encodage des descriptions ;
* sauvegarde des vecteurs ou d’une structure réutilisable.

### D. Recherche textuelle sémantique

* saisie d’une requête utilisateur ;
* calcul de similarité ;
* affichage des images les plus pertinentes.

### E. Interface de consultation

* affichage sous forme de galerie ou de liste ;
* visualisation des miniatures ;
* affichage de la description associée à chaque résultat.

---

## Fonctionnalités complémentaires possibles

Il es possible d'ajouter une ou plusieurs extensions :

### 1. Re-ranking des résultats

Après une première recherche vectorielle, utiliser à nouveau **Qwen-VL** pour réévaluer les meilleurs résultats en comparant plus finement la requête et chaque image.

### 2. Recherche par image exemple

Permettre à l’utilisateur de choisir une image du corpus ou hors corpus et de demander :

* *“trouve les images les plus proches de celle-ci”*

Dans ce cas, une stratégie simple consiste à :

* décrire l’image exemple avec Qwen-VL ;
* utiliser cette description comme requête.

### 3. Enrichissement multi-champs

Créer plusieurs champs textuels :

* description générale,
* mots-clés,
* objets détectés,
* ambiance ou scène probable.

Puis tester différentes façons de fusionner ces informations.

### 4. Mise à jour incrémentale de l’index

Ne traiter que les nouvelles images ou celles qui ont été modifiées.

### 5. Filtrage et tri

Ajouter des filtres :

* nom de fichier,
* extension,
* présence d’un mot-clé,
* date d’indexation.

### 6. Export des résultats

Exporter une recherche dans un fichier :

* JSON,
* CSV,
* ou HTML simple.

---

## Architecture logicielle conseillée

Une structuration modulaire est attendue. Par exemple :

* `dataset/`

  * chargement des images
* `vision/`

  * interrogation de Qwen-VL
* `embedding/`

  * calcul des vecteurs
* `index/`

  * stockage et recherche par similarité
* `ui/`

  * interface utilisateur
* `storage/`

  * JSON, SQLite ou autre persistance

Une séparation claire entre :

* ingestion,
* analyse,
* indexation,
* recherche,
* affichage

sera valorisée.

---

## Données manipulées

Chaque image pourra être représentée par une structure du type :

```json
{
  "id": "img_0001",
  "path": "dataset/photo_01.jpg",
  "description": "A rainy street at night with reflections on the ground.",
  "keywords": ["street", "night", "rain", "lights"],
  "embedding": "...",
  "indexed_at": "2026-04-17T10:30:00"
}
```

Le format exact est libre, mais il doit être cohérent et documenté.

---

## Interface attendue

L’interface peut être :

* une application Python desktop ;
* ou une interface web locale simple.

Elle devra permettre au minimum :

* de charger ou indexer un corpus ;
* de lancer une recherche ;
* d’afficher les résultats avec miniatures ;
* de consulter la description générée.

Une interface simple mais propre et robuste est préférable à une interface très ambitieuse mais instable.

---

## Livrables attendus

* code source du projet ;
* notice d’installation et d’utilisation ;
* corpus d’images de test ;
* rapport technique ;
* démonstration fonctionnelle.

---

## Compétences mobilisées

* programmation Python ;
* structuration logicielle ;
* appels à des modèles IA locaux ;
* embeddings et similarité ;
* gestion de données ;
* interface utilisateur ;
* expérimentation et analyse critique.

---





