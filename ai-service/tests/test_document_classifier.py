import unittest
from app.services.document_classifier import classify_document
from app.services.classifier import classify_document_real
from tests.conftest import create_test_image_bytes, create_text_image_bytes

class TestDocumentClassifier(unittest.TestCase):
    def test_classify_by_real_licence_text_content(self):
        img_bytes = create_text_image_bytes([
            "DRIVING LICENCE",
            "1. SMITH",
            "2. JOHN MICHAEL",
            "5. SMITH903155JM9AB",
            "DVLA",
        ])
        res = classify_document(img_bytes)
        self.assertEqual(res["document_type"], "uk_driving_licence")
        self.assertGreater(res["confidence"], 0.0)

    def test_classify_by_real_passport_text_content(self):
        img_bytes = create_text_image_bytes([
            "PASSPORT",
            "Surname: SMITH",
            "P<GBRSMITH<<JOHN<MICHAEL<<<<<<<<<<<<<<<<<<<<",
            "1234567890GBR9003155M3001014<<<<<<<<<<<<<<02",
        ])
        res = classify_document(img_bytes)
        self.assertEqual(res["document_type"], "passport")
        self.assertGreater(res["confidence"], 0.0)

    def test_classify_unknown_when_no_document_evidence(self):
        # Plain noise image with no rendered text at all — no filename hint
        # is passed since classification no longer trusts filenames.
        img_bytes = create_test_image_bytes(600, 400)
        res = classify_document(img_bytes)
        self.assertEqual(res["document_type"], "unknown")
        self.assertEqual(res["confidence"], 0.0)

    def test_classify_document_real_empty_image(self):
        res = classify_document_real(b"")
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["document_type"], "unknown")

if __name__ == "__main__":
    unittest.main()
