import unittest
import cv2
import numpy as np
from app.services.image_utils import resize_image_for_ai
from tests.conftest import create_test_image_bytes


class TestResizeImageForAI(unittest.TestCase):
    def test_downscales_large_image_to_max_dim(self):
        # A modern phone photo (e.g. 4000x3000) must be capped on its
        # longest side — this is the fix for OCR/face-match taking far
        # longer than necessary on CPU-only inference when full-resolution
        # images were sent straight to EasyOCR/InsightFace.
        img_bytes = create_test_image_bytes(4000, 3000)
        resized_bytes = resize_image_for_ai(img_bytes, max_dim=1600)

        arr = np.frombuffer(resized_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        self.assertLessEqual(max(h, w), 1600)
        # Aspect ratio preserved (4000x3000 = 4:3)
        self.assertAlmostEqual(w / h, 4000 / 3000, places=2)

    def test_leaves_small_image_untouched(self):
        img_bytes = create_test_image_bytes(800, 600)
        resized_bytes = resize_image_for_ai(img_bytes, max_dim=1600)

        arr = np.frombuffer(resized_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        h, w = img.shape[:2]
        self.assertEqual((w, h), (800, 600))

    def test_invalid_bytes_returns_original_unchanged(self):
        garbage = b"not an image"
        self.assertEqual(resize_image_for_ai(garbage), garbage)

    def test_empty_bytes_returns_original_unchanged(self):
        self.assertEqual(resize_image_for_ai(b""), b"")

    def test_crops_bordered_document_from_background(self):
        from app.services.image_utils import crop_and_deskew_document
        from tests.conftest import create_bordered_document_image_bytes

        # 1000x750 with 150px border on all sides -> document is 700x450 in center
        img_bytes = create_bordered_document_image_bytes(width=1000, height=750, inset=150)
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        cropped = crop_and_deskew_document(img)
        h, w = cropped.shape[:2]

        # The cropped document should be smaller than original frame and closer to 700x450
        self.assertLess(w, 1000)
        self.assertLess(h, 750)
        self.assertGreaterEqual(w, 650)
        self.assertGreaterEqual(h, 400)

    def test_leaves_already_tightly_framed_document_intact(self):
        from app.services.image_utils import crop_and_deskew_document
        from tests.conftest import create_bordered_document_image_bytes

        # Inset of 5 means document covers >95% of the frame
        img_bytes = create_bordered_document_image_bytes(width=856, height=540, inset=5)
        arr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        cropped = crop_and_deskew_document(img)
        self.assertEqual(cropped.shape, img.shape)


if __name__ == "__main__":
    unittest.main()
