from abc import ABC, abstractmethod

class BaseOCR(ABC):
    @abstractmethod
    def extract_text(self, image_bytes: bytes, document_type: str) -> dict:
        """
        Extract structured text from the document image.
        Returns a dictionary containing:
        - name
        - dob
        - address
        - document_number
        - expiry_date
        - issue_date
        - confidence
        """
        pass
