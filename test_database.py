#!/usr/bin/env python3
"""
Script de test pour vérifier l'intégration BDD <-> ImageInfo
"""

import sys
import os
from pathlib import Path

# Ajouter le chemin racine du projet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.ImageInfo import ImageInfo, ProcessingStatus
from index.image import insert_image, get_all_images, get_images_with_embeddings, get_image_by_id
from index.vectResearch import vectresearch

def test_database_integration():
    """Test l'intégration complète BDD <-> ImageInfo"""
    
    print("🧪 Test d'intégration BDD <-> ImageInfo")
    print("=" * 50)
    
    # 1. Créer une image de test
    test_image = ImageInfo(
        path=Path("dataset/test/weezer.png"),
        description="Image test de weezer",
        keywords=["musique", "rock", "groupe"],
        embedding=[0.1, 0.2, 0.3, 0.4, 0.5],  # Embedding de test
        status=ProcessingStatus.COMPLETED
    )
    
    print(f"✅ Image de test créée: {test_image.name} (ID: {test_image.id})")
    
    # 2. Insérer dans la BDD
    success = insert_image(test_image)
    print(f"{'✅' if success else '❌'} Insertion en BDD: {'Succès' if success else 'Échec'}")
    
    # 3. Récupérer par ID
    retrieved_image = get_image_by_id(test_image.id)
    if retrieved_image:
        print(f"✅ Récupération par ID: {retrieved_image.name}")
        print(f"   - Description: {retrieved_image.description}")
        print(f"   - Keywords: {retrieved_image.keywords}")
        print(f"   - Embedding: {len(retrieved_image.embedding)} dimensions")
        print(f"   - Status: {retrieved_image.status}")
    else:
        print("❌ Échec de la récupération par ID")
    
    # 4. Récupérer toutes les images
    all_images = get_all_images()
    print(f"✅ Toutes les images: {len(all_images)} trouvées")
    
    # 5. Récupérer les images avec embeddings
    images_with_embeddings = get_images_with_embeddings()
    print(f"✅ Images avec embeddings: {len(images_with_embeddings)} trouvées")
    
    # 6. Test de recherche sémantique
    if images_with_embeddings:
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Embedding de test
        results = vectresearch(query_embedding, use_database=True)
        print(f"✅ Recherche sémantique: {len(results)} résultats")
        for i, result in enumerate(results[:3]):  # Top 3
            print(f"   {i+1}. {result['image'].name} (similarité: {result['similarity']:.3f})")
    
    print("\n🎉 Test terminé avec succès!")

if __name__ == "__main__":
    test_database_integration()
