import unittest
import json
from unittest.mock import patch, MagicMock
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import VerificationSession, SessionStateEnum, Blacklist, Customer, Document

class TestSessionEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def test_start_session(self):
        response = client.post("/api/v1/session/start", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("session_id", data)
        self.assertTrue(len(data["session_id"]) > 10)

    def test_face_before_ocr_returns_400_not_500(self):
        # Regression: /session/{id}/face used to read session_data["ocr"]
        # unconditionally, which raised a raw KeyError (surfaced as an
        # opaque 500) if called before /session/{id}/scan (classify+OCR
        # combined) ever ran. Every other step-order violation in this
        # flow already returns a clean 400 — /face should too.
        from backend.db.redis import get_redis
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]
        session_state = {"step": 1, "status": "started", "session_id": session_id}
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))

        response = client.post(
            f"/api/v1/session/{session_id}/face",
            files={"file": ("face.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("OCR", response.json()["detail"])

    def test_scan_combines_classify_and_ocr_in_one_call(self):
        # Regression: /classify and /ocr used to be two separate endpoints
        # requiring two separate client uploads of the same photo. /scan
        # combines them server-side into a single call — this verifies the
        # merged endpoint calls ai-service's /classify then /ocr in that
        # order (routing OCR's document_type from classify's own result),
        # and lands the session on step 3 (matching the old /ocr
        # endpoint's final step), same as before the merge.
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        classify_payload = {
            "is_valid": True,
            "document_type": "uk_driving_licence",
            "type_confidence": 0.95,
        }
        ocr_payload = {
            "extracted_data": {
                "document_number": "SMITH901018AB9IJ",
                "name": "JOHN SMITH",
                "dob": "1990-01-01",
                "confidence": 92.0,
            },
            "validation": {"is_valid": True, "errors": []},
        }

        calls = []

        async def fake_post(self, url, **kwargs):
            calls.append(url)
            response = MagicMock()
            response.status_code = 200
            if url.endswith("/classify"):
                response.json = lambda: classify_payload
            elif url.endswith("/ocr"):
                response.json = lambda: ocr_payload
            return response

        with patch("httpx.AsyncClient.post", new=fake_post):
            res = client.post(
                f"/api/v1/session/{session_id}/scan",
                files={"file": ("id.jpg", b"fake-image-bytes", "image/jpeg")},
                headers=self.headers,
            )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["extracted_data"]["document_number"], "SMITH901018AB9IJ")
        # classify must be called before ocr — ocr's document_type routing
        # depends on classify's result being available first.
        self.assertTrue(calls[0].endswith("/classify"))
        self.assertTrue(calls[1].endswith("/ocr"))

        from backend.db.redis import get_redis
        session_data = json.loads(next(get_redis()).get(f"session:{session_id}"))
        self.assertEqual(session_data["step"], 3)
        self.assertEqual(session_data["classification"]["document_type"], "uk_driving_licence")

    def test_scan_rejects_document_without_classifying(self):
        # A document that fails classification (no face detected, etc.)
        # must short-circuit before OCR ever runs — same behavior as the
        # old two-endpoint flow's /classify rejection.
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        calls = []

        async def fake_post(self, url, **kwargs):
            calls.append(url)
            response = MagicMock()
            response.status_code = 200
            response.json = lambda: {
                "is_valid": False,
                "reason": "No face detected on the document.",
            }
            return response

        with patch("httpx.AsyncClient.post", new=fake_post):
            res = client.post(
                f"/api/v1/session/{session_id}/scan",
                files={"file": ("id.jpg", b"fake-image-bytes", "image/jpeg")},
                headers=self.headers,
            )

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["message"], "No face detected on the document.")
        # OCR must never be called for a rejected document.
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith("/classify"))

    def test_operator_stats(self):
        # Start a session
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        response = client.get("/api/v1/operator/stats", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["operator_name"], "testoperator")
        # Regression: the mobile dashboard shows the operator's venue name
        # (Profile > seeded as "Test Pub" in conftest.init_test_db) rather
        # than a static "Door team verification" subtitle — this field
        # must be present and correctly scoped to the caller's own venue.
        self.assertEqual(data["venue_name"], "Test Pub")
        self.assertIn("verified", data)
        self.assertIn("pending", data)
        self.assertIn("flagged", data)

    def test_finalize_session_pass(self):
        # 1. Start session
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        # Populate session data via the same redis client the app uses
        # (a real local Redis if available, else the in-memory fallback)
        from backend.db.redis import get_redis
        session_state = {
            # step 4 = face-verify step completed, matching what the real
            # /session/{id}/face endpoint sets — finalize_session requires
            # this before honoring a "pass" decision.
            "step": 4,
            "status": "ready",
            "session_id": session_id,
            "ocr": {
                "document_number": "SMITH901018AB9IJ",
                "name": "JOHN SMITH",
                "dob": "1990-01-01",
                "document_type": "uk_driving_licence",
                "expiry_date": "2030-01-01",
                "issue_date": "2020-01-01"
            },
            "classification": {"document_type": "uk_driving_licence"},
            "embedding": [0.1] * 512,
            "validation": {"is_valid": True}
        }
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))

        # 2. Finalize
        finalize_payload = {
            "staff_decision": "PASS",
            "notes": "Verified visually against photo"
        }
        res = client.post(f"/api/v1/session/{session_id}/finalize", json=finalize_payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("customer_id", data)

        # Check DB
        db = TestingSessionLocal()
        try:
            sess = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
            self.assertIsNotNone(sess)
            self.assertEqual(sess.state, SessionStateEnum.APPROVED)
            self.assertEqual(sess.final_decision, "pass")
            self.assertTrue(sess.is_locked)

            doc = db.query(Document).filter(Document.customer_id == sess.customer_id).first()
            self.assertIsNotNone(doc)
            self.assertEqual(doc.doc_type, "uk_driving_licence")
            self.assertEqual(doc.doc_number, "SMITH901018AB9IJ")
            self.assertIsNotNone(doc.expiry_date)
            self.assertIsNotNone(doc.issue_date)
        finally:
            db.close()

    def test_finalize_session_block_creates_blacklist(self):
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        from backend.db.redis import get_redis
        session_state = {
            "step": 3,
            "status": "ready",
            "session_id": session_id,
            "ocr": {
                "document_number": "JONES850505CD8KL",
                "name": "ALICE JONES",
                "dob": "1985-05-05"
            },
            "embedding": [0.2] * 512,
            "validation": {"is_valid": True}
        }
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))

        finalize_payload = {
            "staff_decision": "BLOCK",
            "notes": "Aggressive behavior at entrance"
        }
        res = client.post(f"/api/v1/session/{session_id}/finalize", json=finalize_payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)

        db = TestingSessionLocal()
        try:
            sess = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
            self.assertEqual(sess.state, SessionStateEnum.DENIED)
            self.assertEqual(sess.final_decision, "block")

            customer = db.query(Customer).filter(Customer.unique_id == "JONES850505CD8KL").first()
            self.assertIsNotNone(customer)

            ban = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).first()
            self.assertIsNotNone(ban)
            self.assertEqual(ban.reason, "Aggressive behavior at entrance")
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
