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

    def test_operator_stats(self):
        # Start a session
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        response = client.get("/api/v1/operator/stats", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["operator_name"], "testoperator")
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
            "step": 3,
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
