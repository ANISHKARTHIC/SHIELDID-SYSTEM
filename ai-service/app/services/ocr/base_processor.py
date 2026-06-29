class BaseDocumentProcessor:
    """
    Base class for document-specific OCR extraction and validation processors.
    """
    def process(self, ocr_results: list) -> dict:
        """
        Takes list of OCR results: (bounding_box, text, confidence)
        and returns structured, validated JSON.
        """
        raise NotImplementedError
