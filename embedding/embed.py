from vision.ollama_wrapper import OllamaWrapper
from common.ImageInfo import ImageInfo

from typing import List
import numpy as np
import time

def TextToEmbedding(wrapper: OllamaWrapper, image: ImageInfo) -> None:
    try:
        result = wrapper.embed(
            model="nomic-embed-text:v1.5",
            text=f"{image.name}\n{image.description}\n{image.keywords}"
        )
        image.embedding = result
    except Exception as e:
        return None

def inputToEmbedding(wrapper: OllamaWrapper, input: str) -> list:
    try:
        result = wrapper.embed(
            model="nomic-embed-text:v1.5",
            text=input
        )
        return result
    except Exception as e:
        return None