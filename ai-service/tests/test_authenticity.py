import unittest
from app.services.document_authenticity import assess_authenticity, calculate_dynamic_variance, calculate_color_noise
from tests.conftest import create_test_image_bytes

class TestDocumentAuthenticity(unittest.TestCase):
    def test_assess_authenticity_valid(self):
        img_bytes = create_test_image_bytes(800, 600)
        quality = {"quality_score": 90, "blur": False, "lighting": "good"}
        res = assess_authenticity(img_bytes, ocr_confidence=95.0, quality_assessment=quality)
        
        self.assertIn("authenticity_score", res)
        self.assertIn("risk", res)
        self.assertIn("possible_issues", res)
        self.assertIn("manual_review_recommendation", res)
        self.assertIsInstance(res["authenticity_score"], int)
        self.assertTrue(0 <= res["authenticity_score"] <= 100)

    def test_assess_authenticity_blurry(self):
        img_bytes = create_test_image_bytes(800, 600)
        quality = {"quality_score": 40, "blur": True, "lighting": "under_exposed"}
        res = assess_authenticity(img_bytes, ocr_confidence=50.0, quality_assessment=quality)
        
        self.assertTrue(res["authenticity_score"] < 85)
        self.assertTrue(res["manual_review_recommendation"])

    def test_corrupted_image_handling(self):
        res = assess_authenticity(b"corrupted_bytes", ocr_confidence=0.0, quality_assessment={})
        self.assertEqual(res["risk"], "HIGH")
        self.assertIn("Image decode failure", res["possible_issues"])

if __name__ == "__main__":
    unittest.main()
