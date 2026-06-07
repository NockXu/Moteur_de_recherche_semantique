# Accueil

## Description du projet

Ce projet est un moteur de recherche sémantique d’images basé sur des embeddings et une architecture hybride combinant base de données relationnelle et index vectoriel.

Il permet d’indexer, analyser et retrouver des images en fonction de leur contenu sémantique plutôt que de simples correspondances de mots-clés.

## Prérequis

- Python 3.12 minimum
- une carte graphique compatible CUDA (pour l'utilisation de GPU)

## Installation

1. Installer les dépandances pip
```bash
pip install -r requirements.txt
```

2. Installer PyTorch qui prend en charge CUDA
```bash
pip install torch==2.10.0 torchvision --index-url https://download.pytorch.org/whl/cu128
```

3. Cloner le dépôt git de sam3 et installer les dépendances
```bash
cd vision
git clone https://github.com/facebookresearch/sam3.git
cd sam3
pip install -e .
cd ../..
```

4. Installer les dépendances manquantes
```bash
pip install -r requirementsv2.txt
```

[Voir plus sur l'installation de sam3](https://github.com/facebookresearch/sam3)

## Sommaire

### Vision

- [Image Processor](vision/ImageProcessor.md)
- [Ollama Wrapper](vision/ollama_wrapper.md)

### Database

- [DB Service](database/DbService.md)
- [SQLite Manager](database/sqlite.md)
- [FAISS Manager](database/faiss.md)

### Common

#### Classes des Images

- [Image](common/image/image.md)
- [Image Repository](common/image/image_repository.md)
- [Image Scan Service](common/image/image_scan_service.md)

#### Classes des Datasets

- [Dataset](common/dataset/dataset.md)
- [Dataset Repository](common/dataset/dataset_repository.md)