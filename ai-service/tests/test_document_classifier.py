import unittest
from app.services.document_classifier import classify_document
from app.services.classifier import classify_document_real
from tests.conftest import create_test_image_bytes

class TestDocumentClassifier(unittest.TestCase):
    def test_classify_by_filename_passport(self):
        img_bytes = create_test_image_bytes(600, 400)
        res = classify_document(img_bytes, filename="user_passport.jpg")
        self.assertEqual(res["document_type"], "passport")
        self.assertGreater(res["confidence"], 0.8)

    def test_classify_by_filename_driving_licence(self):
        img_bytes = create_test_image_bytes(600, 400)
        res = classify_document(img_bytes, filename="uk_driving_licence_scan.jpg")
        self.assertEqual(res["document_type"], "uk_driving_licence")

    def test_classify_aspect_ratio_portrait_fallback(self):
        # Portrait orientation image with generic name
        img_bytes = create_test_image_bytes(400, 700)
        res = classify_document(img_bytes, filename="scan001.png")
        self.assertEqual(res["document_type"], "passport")

    def test_classify_document_real_empty_image(self):
        res = classify_document_real(b"")
        self.assertFalse(res["is_valid"])
        self.assertEqual(res["document_type"], "unknown")

if __name__ == "__main__":
    unittest.main()
