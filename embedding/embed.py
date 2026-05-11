import sys
import os

# Ajouter la racine du projet au sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from vision.ollama_wrapper import OllamaWrapper
from common.Image_Classes.Image import Image

from typing import List
import numpy as np
import time

def TextToEmbedding(wrapper: OllamaWrapper, image: Image) -> None:
    try:
        result = wrapper.embed(
            model="nomic-embed-text:v1.5",
            text=f"{image.name}\n{image.description}\n{image.keywords}"
        )
        image.embedding = result
    except Exception as e:
        return None

def inputToEmbedding(wrapper: OllamaWrapper, input: str) -> List[float]:
    print(f"[DEBUG] inputToEmbedding appelé avec: '{input}'")
    print(f"[DEBUG] wrapper: {wrapper}")
    try:
        print(f"[DEBUG] Appel à wrapper.embed()...")
        result = wrapper.embed(
            model="nomic-embed-text:v1.5",
            text=input
        )
        print(f"[DEBUG] Résultat de wrapper.embed(): {type(result)}")
        if result:
            print(f"[DEBUG] Dimensions de l'embedding: {len(result)}")
        else:
            print("[DEBUG] wrapper.embed() a retourné None")
        return result
    except Exception as e:
        print(f"[DEBUG] Exception dans inputToEmbedding: {e}")
        print(f"[DEBUG] Type d'exception: {type(e)}")
        return None