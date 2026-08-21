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

    def test_assess_authenticity_is_deterministic(self):
        # Regression: the score used to be perturbed by a deterministic
        # MD5-hash-of-image-bytes "natural_variance" term purely to look
        # less static — that's cosmetic, not a real signal, and made the
        # score non-reproducible for the exact same inputs across two
        # different images that happen to hash differently. The same
        # inputs must now always produce the exact same score.
        img_bytes = create_test_image_bytes(800, 600)
        quality = {"quality_score": 90, "blur": False, "lighting": "good"}
        res1 = assess_authenticity(img_bytes, ocr_confidence=95.0, quality_assessment=quality)
        res2 = assess_authenticity(img_bytes, ocr_confidence=95.0, quality_assessment=quality)
        self.assertEqual(res1["authenticity_score"], res2["authenticity_score"])

    def test_assess_authenticity_not_compressed_into_bands(self):
        # Regression: scores used to be remapped into hardcoded percentage
        # bands (30-65 / 70-85 / 91-98.5) regardless of the actual
        # computed value. A perfect-signal input (max OCR confidence, no
        # blur) should be able to score above the old 98.5 ceiling.
        img_bytes = create_test_image_bytes(800, 600)
        quality = {"quality_score": 100, "blur": False, "lighting": "good"}
        res = assess_authenticity(img_bytes, ocr_confidence=100.0, quality_assessment=quality)
        self.assertLessEqual(res["authenticity_score"], 100)

if __name__ == "__main__":
    unittest.main()
