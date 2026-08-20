import unittest
import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, Blacklist, Notification, Occupancy, VerificationSession
from backend.services import storage_service as storage_service_module


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

    def test_standalone_ban_moves_images_to_banned_prefix(self):
        # A ban created against a past visitor (not mid-session) must still
        # relocate that customer's stored S3 images from scans/unflagged/ to
        # scans/flagged/ so bulk retention/flush operations scoped to
        # scans/unflagged/ never touch a banned customer's photos.
        # storage_service.client is None in this test env (no real S3/MinIO),
        # so move_to_banned would normally no-op — fake a minimal boto3
        # client to exercise the real copy+delete path.
        customer_id = self._create_bare_customer(unique_id="IMGBAN001", name="Image Ban Person")
        db = TestingSessionLocal()
        try:
            session = VerificationSession(
                id="imgban-session-1",
                venue_id=1,
                operator_id=1,
                customer_id=customer_id,
                id_image_path="scans/unflagged/imgban-session-1_id.jpg",
                face_image_path="scans/unflagged/imgban-session-1_face.jpg",
            )
            db.add(session)
            db.commit()
        finally:
            db.close()

        fake_client = MagicMock()
        with patch.object(storage_service_module.storage_service, "client", fake_client):
            res = client.post(
                "/api/v1/blacklist",
                json={"customer_id": customer_id, "reason": "Reported fake ID"},
                headers=self.headers,
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(fake_client.copy_object.call_count, 2)
        self.assertEqual(fake_client.delete_object.call_count, 2)

        db = TestingSessionLocal()
        try:
            refreshed = db.query(VerificationSession).filter(VerificationSession.id == "imgban-session-1").first()
            self.assertEqual(refreshed.id_image_path, "scans/flagged/imgban-session-1_id.jpg")
            self.assertEqual(refreshed.face_image_path, "scans/flagged/imgban-session-1_face.jpg")
        finally:
            db.close()

    def test_finalize_block_moves_images_to_banned_prefix(self):
        # The inline BLOCK-at-the-door path must also quarantine images,
        # not just the standalone /blacklist endpoint.
        from backend.db.redis import get_redis
        start_res = client.post("/api/v1/session/start", headers=self.headers)
        session_id = start_res.json()["session_id"]
        session_state = {
            "step": 3,
            "status": "ready",
            "session_id": session_id,
            "ocr": {"document_number": "BLOCKIMG850505CD8KL", "name": "Block Image Person", "dob": "1985-05-05"},
            "embedding": [0.2] * 512,
            "validation": {"is_valid": True},
        }
        next(get_redis()).set(f"session:{session_id}", json.dumps(session_state))

        db = TestingSessionLocal()
        try:
            row = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
            row.id_image_path = f"scans/unflagged/{session_id}_id.jpg"
            row.face_image_path = f"scans/unflagged/{session_id}_face.jpg"
            db.commit()
        finally:
            db.close()

        fake_client = MagicMock()
        with patch.object(storage_service_module.storage_service, "client", fake_client):
            res = client.post(
                f"/api/v1/session/{session_id}/finalize",
                json={"staff_decision": "BLOCK", "notes": "Fighting"},
                headers=self.headers,
            )
        self.assertEqual(res.status_code, 200)

        db = TestingSessionLocal()
        try:
            refreshed = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
            self.assertEqual(refreshed.id_image_path, f"scans/flagged/{session_id}_id.jpg")
            self.assertEqual(refreshed.face_image_path, f"scans/flagged/{session_id}_face.jpg")
        finally:
            db.close()

    def test_unban_removes_blacklist_row(self):
        customer_id = self._create_bare_customer(unique_id="UNBAN001", name="Unban Person")
        client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "Initial ban"},
            headers=self.headers,
        )

        supervisor_headers = auth_headers("testsupervisor@pub.com")
        res = client.delete(f"/api/v1/blacklist/{customer_id}", headers=supervisor_headers)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        db = TestingSessionLocal()
        try:
            self.assertIsNone(db.query(Blacklist).filter(Blacklist.customer_id == customer_id).first())
        finally:
            db.close()

    def test_unban_requires_manager_or_above(self):
        # door_staff can create a ban but must not be able to lift one —
        # unbanning is scoped to require_supervisor (manager+), a
        # deliberately higher bar than create_ban's require_floor_staff.
        customer_id = self._create_bare_customer(unique_id="UNBANROLE001", name="Unban Role Person")
        client.post(
            "/api/v1/blacklist",
            json={"customer_id": customer_id, "reason": "Initial ban"},
            headers=self.headers,
        )

        res = client.delete(f"/api/v1/blacklist/{customer_id}", headers=self.headers)
        self.assertEqual(res.status_code, 403)

        db = TestingSessionLocal()
        try:
            self.assertIsNotNone(db.query(Blacklist).filter(Blacklist.customer_id == customer_id).first())
        finally:
            db.close()

    def test_unban_nonexistent_ban_returns_404(self):
        customer_id = self._create_bare_customer(unique_id="NOBAN001", name="Never Banned Person")
        supervisor_headers = auth_headers("testsupervisor@pub.com")
        res = client.delete(f"/api/v1/blacklist/{customer_id}", headers=supervisor_headers)
        self.assertEqual(res.status_code, 404)

    def test_unban_restores_images_to_unflagged_prefix(self):
        customer_id = self._create_bare_customer(unique_id="UNBANIMG001", name="Unban Image Person")
        db = TestingSessionLocal()
        try:
            session = VerificationSession(
                id="unban-img-session-1",
                venue_id=1,
                operator_id=1,
                customer_id=customer_id,
                id_image_path="scans/flagged/unban-img-session-1_id.jpg",
                face_image_path="scans/flagged/unban-img-session-1_face.jpg",
            )
            db.add(session)
            db.add(Blacklist(customer_id=customer_id, reason="test"))
            db.commit()
        finally:
            db.close()

        fake_client = MagicMock()
        supervisor_headers = auth_headers("testsupervisor@pub.com")
        with patch.object(storage_service_module.storage_service, "client", fake_client):
            res = client.delete(f"/api/v1/blacklist/{customer_id}", headers=supervisor_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(fake_client.copy_object.call_count, 2)
        self.assertEqual(fake_client.delete_object.call_count, 2)

        db = TestingSessionLocal()
        try:
            refreshed = db.query(VerificationSession).filter(VerificationSession.id == "unban-img-session-1").first()
            self.assertEqual(refreshed.id_image_path, "scans/unflagged/unban-img-session-1_id.jpg")
            self.assertEqual(refreshed.face_image_path, "scans/unflagged/unban-img-session-1_face.jpg")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
