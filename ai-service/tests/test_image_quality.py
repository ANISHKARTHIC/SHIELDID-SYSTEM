import unittest
from app.services.image_quality import assess_image_quality
from tests.conftest import create_test_image_bytes

class TestImageQuality(unittest.TestCase):
    def test_assess_valid_image(self):
        img_bytes = create_test_image_bytes(800, 600)
        res = assess_image_quality(img_bytes)
        self.assertIn("quality_score", res)
        self.assertIn("blur", res)
        self.assertIn("lighting", res)
        self.assertIn("cropped", res)
        self.assertIn("rotation", res)
        self.assertTrue(0 <= res["quality_score"] <= 100)

    def test_assess_low_resolution_image(self):
        img_bytes = create_test_image_bytes(200, 100)
        res = assess_image_quality(img_bytes)
        # Should flag low resolution penalty
        self.assertTrue(res["quality_score"] < 100)

    def test_invalid_bytes_raises_error(self):
        with self.assertRaises(ValueError):
            assess_image_quality(b"not an image")

if __name__ == "__main__":
    unittest.main()
