from abc import ABC, abstractmethod
from typing import Dict, Any, List
import numpy as np

class BaseOCR(ABC):
    @abstractmethod
    def load_model(self) -> None:
        """Load the OCR model into memory."""
        pass

    @abstractmethod
    def extract_text(self, image_path: str, regions: Dict[str, dict] = None) -> Dict[str, Any]:
        """
        Extract text from an image.
        Optionally restricted to specific bounding box regions from a document template.
        Must return:
        {
            "field_name": {
                "text": "Extracted String",
                "confidence": 0.95,
                "bounding_box": [x1, y1, x2, y2]
            }
        }
        """
        pass

class BaseFaceRecognition(ABC):
    @abstractmethod
    def load_model(self) -> None:
        """Load the Face Recognition and Detection models into memory."""
        pass

    @abstractmethod
    def extract_embedding(self, image_path: str) -> np.ndarray:
        """
        Detect a face and extract its embedding.
        """
        pass
        
    @abstractmethod
    def compare(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compare two embeddings and return a similarity score (0.0 to 1.0).
        """
        pass

class BaseClassifier(ABC):
    @abstractmethod
    def load_model(self) -> None:
        """Load the classification model into memory."""
        pass

    @abstractmethod
    def classify(self, image_path: str) -> Dict[str, Any]:
        """
        Classify the type of document.
        Must return:
        {
            "is_valid": bool,
            "doc_type": str, # e.g., 'uk_driving_licence'
            "confidence": float,
            "reason": str
        }
        """
        pass
