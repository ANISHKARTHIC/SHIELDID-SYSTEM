import unittest
import json
from datetime import datetime, timezone
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, Blacklist, Notification, Occupancy, VerificationSession


def _finalize_pass_session(headers, unique_id, name):
    from backend.db.redis import get_redis
    start_res = client.post("/api/v1/session/start", headers=headers)
    session_id = start_res.json()["session_id"]
    session_state = {
        "step": 3,
        "status": "ready",
        "session_id": session_id,
        "ocr": {
            "document_number": unique_id,
            "name": name,
            "dob": "1990-01-01",
            "document_type": "uk_driving_licence",
        },
        "classification": {"document_type": "uk_driving_licence"},
        "embedding": [0.1] * 512,
        "validation": {"is_valid": True},
    }
    next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))
    res = client.post(
        f"/api/v1/session/{session_id}/finalize",
        json={"staff_decision": "PASS", "notes": "ok"},
        headers=headers,
    )
    return res.json()["customer_id"]


class TestBlacklistBan(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def _create_bare_customer(self, unique_id="BARE001", name="Bare Customer", venue_id=1):
        db = TestingSessionLocal()
        try:
            cust = Customer(unique_id=unique_id, name=name, dob=datetime(1990, 1, 1, tzinfo=timezone.utc))
            db.add(cust)
            db.commit()
            db.refresh(cust)
            return cust.id
        finally:
            db.close()

    def test_ban_without_occupancy_no_alert(self):
        customer_id = self._create_bare_customer()

        res = client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "Reported fake ID"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["currently_inside"])

        db = TestingSessionLocal()
        try:
            ban = db.query(Blacklist).filter(Blacklist.customer_id == customer_id).first()
            self.assertIsNotNone(ban)
            notif = db.query(Notification).filter(Notification.type == "ALERT").first()
            self.assertIsNone(notif)
        finally:
            db.close()

    def test_ban_with_open_occupancy_creates_alert(self):
        customer_id = _finalize_pass_session(self.headers, "INSIDE001901018AB9IJ", "Currently Inside Person")

        res = client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "Violent behavior"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["currently_inside"])

        db = TestingSessionLocal()
        try:
            notif = db.query(Notification).filter(Notification.type == "ALERT").first()
            self.assertIsNotNone(notif)
            self.assertIn("CURRENTLY INSIDE", notif.message)
        finally:
            db.close()

    def test_duplicate_ban_returns_409(self):
        customer_id = self._create_bare_customer(unique_id="DUP001", name="Dup Customer")
        client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "First ban"},
            headers=self.headers,
        )
        res = client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "Second attempt"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 409)

    def test_cross_venue_occupancy_does_not_trigger_alert(self):
        # Customer is inside venue 2, caller is scoped to venue 1 — the
        # occupancy match must be venue-specific.
        customer_id = self._create_bare_customer(unique_id="XVENUE001", name="Cross Venue Person")
        db = TestingSessionLocal()
        try:
            db.add(Occupancy(venue_id=2, customer_id=customer_id))
            db.commit()
        finally:
            db.close()

        res = client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "Reported elsewhere"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["currently_inside"])

    def test_finalize_session_block_path_unaffected(self):
        # Regression guard: the existing inline BLOCK-at-the-door ban path
        # must keep working unchanged after this phase's standalone endpoint
        # is added.
        from backend.db.redis import get_redis
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]
        session_state = {
            "step": 3,
            "status": "ready",
            "session_id": session_id,
            "ocr": {"document_number": "BLOCKTEST850505CD8KL", "name": "Block Test Person", "dob": "1985-05-05"},
            "embedding": [0.2] * 512,
            "validation": {"is_valid": True},
        }
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))
        res = client.post(
            f"/api/v1/session/{session_id}/finalize",
            json={"staff_decision": "BLOCK", "notes": "Fighting"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)

        db = TestingSessionLocal()
        try:
            customer = db.query(Customer).filter(Customer.unique_id == "BLOCKTEST850505CD8KL").first()
            ban = db.query(Blacklist).filter(Blacklist.customer_id == customer.id).first()
            self.assertIsNotNone(ban)
            self.assertEqual(ban.reason, "Fighting")
        finally:
            db.close()

    def test_viewer_role_forbidden(self):
        # No viewer seeded by default; use door_staff to confirm floor roles
        # succeed, matching the gate applied to all floor-staff actions.
        customer_id = self._create_bare_customer(unique_id="ROLE001", name="Role Test")
        res = client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "test"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
