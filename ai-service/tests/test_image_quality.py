import unittest
from app.services.image_quality import assess_image_quality
from tests.conftest import create_test_image_bytes, create_bordered_document_image_bytes

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

    def test_cropped_document_flush_to_frame_is_detected(self):
        # Regression: cropping/rotation detection used to be a stub that
        # always returned cropped=False/rotation=0 regardless of input
        # (its own comment said "Mocked for now") — a document rectangle
        # with zero inset (flush against every edge of the frame, as a
        # crop that clips the document itself would produce) must now
        # actually be flagged.
        img_bytes = create_bordered_document_image_bytes(inset=0)
        res = assess_image_quality(img_bytes)
        self.assertTrue(res["cropped"])

    def test_well_framed_document_is_not_flagged_as_cropped(self):
        # A document photographed with a comfortable background border on
        # every side (not touching the frame edges) should not be flagged.
        img_bytes = create_bordered_document_image_bytes(inset=60)
        res = assess_image_quality(img_bytes)
        self.assertFalse(res["cropped"])

if __name__ == "__main__":
    unittest.main()
