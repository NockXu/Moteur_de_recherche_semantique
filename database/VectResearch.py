import json
from pathlib import Path
from common.ImageInfo import ImageInfo
from typing import List, Dict, Optional
import numpy as np

# Import FAISS pour la recherche vectorielle
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    print("⚠️ FAISS non disponible, utilisation de la recherche manuelle")
    FAISS_AVAILABLE = False

def cosine_similarity(vect1: List[float], vect2: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs (fallback si FAISS non disponible).
    
    Args:
        vect1: Premier vecteur
        vect2: Second vecteur
        
    Returns:
        Score de similarité cosinus (entre 0 et 1)
    """
    vect1_np = np.array(vect1)
    vect2_np = np.array(vect2)
    
    norm1 = np.linalg.norm(vect1_np)
    norm2 = np.linalg.norm(vect2_np)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return np.dot(vect1_np, vect2_np) / (norm1 * norm2)

def VectResearch(vect_input: list[float], images_data: list[ImageInfo]) -> list[ImageInfo]:
    """
    Fonction qui recherche les images les plus similaires à un vecteur d'entrée.
    Utilise FAISS si disponible, sinon recherche manuelle.
    
    Args:
        vect_input: Vecteur d'entrée pour la recherche
        images_data: Liste des ImageInfo à comparer
        
    Returns:
        Liste des images les plus similaires avec leurs scores
    """
    if not FAISS_AVAILABLE or not images_data:
        # Fallback : recherche manuelle
        return _vect_research_manual(vect_input, images_data)
    
    # Utiliser FAISS pour la recherche
    return _vect_research_faiss(vect_input, images_data)

def _vect_research_manual(vect_input: list[float], images_data: list[ImageInfo]) -> list[ImageInfo]:
    """
    Recherche manuelle (fallback si FAISS non disponible)
    """
    results: list[ImageInfo] = []
    
    # Calculer les similarités avec le vecteur d'entrée pour chaque image
    for image_data in images_data:
        if image_data.embedding and len(image_data.embedding) > 0:
            try:
                similarity = cosine_similarity(vect_input, image_data.embedding)
                image_data.score = similarity
                results.append(image_data)
            except Exception as e:
                print(f"Erreur de similarité pour {image_data.name}: {e}")
    
    # Trier par similarité décroissante
    results.sort(key=lambda x: x.score, reverse=True)
    
    print(f"Recherche manuelle terminée: {len(results)} résultats trouvés")
    return results

def _vect_research_faiss(vect_input: list[float], images_data: list[ImageInfo]) -> list[ImageInfo]:
    """
    Recherche avec FAISS (méthode rapide)
    """
    try:
        # Créer l'index FAISS
        dimension = len(vect_input)
        index = faiss.IndexFlatIP(dimension)
        
        # Préparer les embeddings et les IDs
        embeddings = []
        image_ids = []
        
        for image in images_data:
            if image.embedding and len(image.embedding) == dimension:
                embeddings.append(image.embedding)
                image_ids.append(image.id)
        
        if not embeddings:
            print("Aucun embedding valide trouvé pour la recherche FAISS")
            return []
        
        # Convertir en numpy array et normaliser
        embeddings_array = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(embeddings_array)
        
        # Ajouter à l'index
        index.add(embeddings_array)
        
        # Normaliser la requête
        query_array = np.array([vect_input], dtype=np.float32)
        faiss.normalize_L2(query_array)
        
        # Rechercher
        k = min(len(embeddings), 10)  # Limiter à 10 résultats max
        distances, indices = index.search(query_array, k)
        
        # Construire les résultats
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= 0 and idx < len(image_ids):
                image_id = image_ids[idx]
                # Trouver l'image correspondante
                for image in images_data:
                    if image.id == image_id:
                        image.score = float(dist)
                        results.append(image)
                        break
        
        # Trier par score décroissant
        results.sort(key=lambda x: x.score, reverse=True)
        
        print(f"Recherche FAISS terminée: {len(results)} résultats trouvés")
        return results
        
    except Exception as e:
        print(f"Erreur lors de la recherche FAISS: {e}")
        # Fallback vers la recherche manuelle
        return _vect_research_manual(vect_input, images_data)
