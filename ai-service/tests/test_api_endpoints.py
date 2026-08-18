import unittest
import asyncio
import json
from fastapi.responses import JSONResponse
from app.main import (
    read_root,
    classify_document_endpoint,
    face_match_endpoint,
)
from app.api.v1_router import (
    analyze_document_quality,
    analyze_document_authenticity,
    evaluate_risk
)
from app.schemas.ai_schemas import RiskRequest
from app.core.model_registry import model_registry
from tests.conftest import create_test_image_bytes, create_upload_file

class TestAIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Real InsightFace/EasyOCR models loaded once for the whole suite,
        # matching the app's own startup lifespan hook.
        model_registry.initialize_models()

    def test_root_endpoint(self):
        res = read_root()
        self.assertIn("running", res["message"])

    def test_classify_endpoint(self):
        img_bytes = create_test_image_bytes()
        upload_file = create_upload_file("license.jpg", img_bytes)
        res = asyncio.run(classify_document_endpoint(upload_file))
        self.assertIn("is_valid", res)
        self.assertIn("document_type", res)

    def test_face_match_endpoint_no_face_rejected(self):
        # A featureless noise image has no detectable face, so the real
        # InsightFace pipeline should reject it rather than fabricate an
        # embedding the way the old color-histogram stub used to.
        img_bytes = create_test_image_bytes()
        upload_file = create_upload_file("face.jpg", img_bytes)
        res = asyncio.run(face_match_endpoint(upload_file))
        self.assertIsInstance(res, JSONResponse)
        self.assertEqual(res.status_code, 422)

    def test_risk_endpoint(self):
        payload = RiskRequest(
            ocr_confidence=95.0,
            quality_score=90.0,
            authenticity_score=92.0,
            is_over_18=True,
            venue_status={"blacklisted": False, "incidents": 0}
        )
        res = asyncio.run(evaluate_risk(payload))
        self.assertEqual(res["recommendation"], "PASS")

    def test_document_quality_endpoint(self):
        img_bytes = create_test_image_bytes(800, 600)
        upload_file = create_upload_file("doc.jpg", img_bytes)
        res = asyncio.run(analyze_document_quality(upload_file))
        self.assertIn("quality_score", res)

    def test_document_authenticity_endpoint(self):
        img_bytes = create_test_image_bytes(800, 600)
        upload_file = create_upload_file("doc.jpg", img_bytes)
        quality_json = json.dumps({"quality_score": 90, "blur": False, "lighting": "good"})
        res = asyncio.run(analyze_document_authenticity(
            file=upload_file,
            ocr_confidence=95.0,
            quality_assessment=quality_json
        ))
        self.assertIn("authenticity_score", res)
        self.assertIn("risk", res)

if __name__ == "__main__":
    unittest.main()
