import unittest
import json
from datetime import datetime, timezone
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Venue, User, RoleEnum, VenueConfiguration, PolicySchema, Customer, Blacklist
from backend.core.security import get_password_hash


def _seed_second_venue():
    db = TestingSessionLocal()
    try:
        venue = Venue(id=2, name="Rival Pub", address="1 Other Street")
        db.add(venue)
        db.commit()

        db.add(VenueConfiguration(venue_id=2, verification_mode="manual"))
        db.add(PolicySchema(venue_id=2, minimum_age=18))
        db.commit()

        other_operator = User(
            id=10,
            venue_id=2,
            email="otherventoperator@pub.com",
            hashed_password=get_password_hash("password"),
            role=RoleEnum.door_staff,
            is_active=True,
        )
        db.add(other_operator)
        db.commit()
    finally:
        db.close()


class TestSessionVenueIsolation(unittest.TestCase):
    def setUp(self):
        init_test_db()
        _seed_second_venue()
        self.headers = auth_headers()  # venue 1
        self.other_headers = auth_headers("otherventoperator@pub.com", "password")  # venue 2

    def test_cross_venue_finalize_returns_404(self):
        # Session belongs to venue 1's operator; venue 2's operator must
        # not be able to act on it at all — not even to see it exists.
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        res = client.post(
            f"/api/v1/session/{session_id}/finalize",
            json={"staff_decision": "PASS", "notes": "hijacked"},
            headers=self.other_headers,
        )
        self.assertEqual(res.status_code, 404)

    def test_cross_venue_face_returns_404(self):
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        res = client.post(
            f"/api/v1/session/{session_id}/face",
            files={"file": ("face.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=self.other_headers,
        )
        self.assertEqual(res.status_code, 404)

    def test_cross_venue_ocr_returns_404(self):
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        res = client.post(
            f"/api/v1/session/{session_id}/ocr",
            files={"file": ("id.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=self.other_headers,
        )
        self.assertEqual(res.status_code, 404)

    def test_own_venue_session_still_accessible(self):
        # Sanity check: the venue guard doesn't break the normal same-venue
        # path — a step-order 400 (not a venue-check 404) is expected here
        # since no /classify has run yet.
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]

        res = client.post(
            f"/api/v1/session/{session_id}/ocr",
            files={"file": ("id.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("classified", res.json()["detail"])


class TestFinalizeRequiresFaceStep(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def _start_and_seed(self, step: int, unique_id="STEPTEST901018AB9IJ"):
        from backend.db.redis import get_redis
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]
        session_state = {
            "step": step,
            "status": "ready",
            "session_id": session_id,
            "ocr": {
                "document_number": unique_id,
                "name": "STEP TEST",
                "dob": "1990-01-01",
                "document_type": "uk_driving_licence",
            },
            "classification": {"document_type": "uk_driving_licence"},
            "validation": {"is_valid": True},
        }
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))
        return session_id

    def test_pass_without_face_step_is_rejected(self):
        session_id = self._start_and_seed(step=3)
        res = client.post(
            f"/api/v1/session/{session_id}/finalize",
            json={"staff_decision": "PASS", "notes": "skip face"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Face verification", res.json()["detail"])

    def test_deny_without_face_step_is_allowed(self):
        # Restrictive outcomes don't need the face step — only PASS does.
        session_id = self._start_and_seed(step=3)
        res = client.post(
            f"/api/v1/session/{session_id}/finalize",
            json={"staff_decision": "DENY", "notes": "no face captured"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)

    def test_pass_with_face_step_completed_is_allowed(self):
        session_id = self._start_and_seed(step=4)
        res = client.post(
            f"/api/v1/session/{session_id}/finalize",
            json={"staff_decision": "PASS", "notes": "verified"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 200)


class TestFinalizeBlacklistSafetyNet(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def test_pass_for_blacklisted_customer_is_blocked_even_if_face_step_ran(self):
        # Simulates a stale/tampered session_data blob claiming venue_check
        # was clear, but the customer has since (or already) been banned —
        # finalize must re-check the DB directly rather than trusting the
        # client-controlled decision alone.
        db = TestingSessionLocal()
        try:
            customer = Customer(
                unique_id="BANNED901018AB9IJ",
                name="Banned Person",
                dob=datetime(1990, 1, 1, tzinfo=timezone.utc),
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            db.add(Blacklist(customer_id=customer.id, reason="Prior incident"))
            db.commit()
        finally:
            db.close()

        from backend.db.redis import get_redis
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]
        session_state = {
            "step": 4,
            "status": "ready",
            "session_id": session_id,
            "ocr": {
                "document_number": "BANNED901018AB9IJ",
                "name": "Banned Person",
                "dob": "1990-01-01",
                "document_type": "uk_driving_licence",
            },
            "classification": {"document_type": "uk_driving_licence"},
            "validation": {"is_valid": True},
        }
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))

        res = client.post(
            f"/api/v1/session/{session_id}/finalize",
            json={"staff_decision": "PASS", "notes": "attempted override"},
            headers=self.headers,
        )
        self.assertEqual(res.status_code, 409)


if __name__ == "__main__":
    unittest.main()
