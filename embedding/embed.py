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
    try:
        result = wrapper.embed(
            model="nomic-embed-text:v1.5",
            text=input
        )
        return result
    except Exception as e:
        return None