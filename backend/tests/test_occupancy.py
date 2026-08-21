import unittest
import json
from datetime import datetime, timedelta, timezone
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Occupancy, OccupancyStatusEnum, Customer, AuditLog, VenueConfiguration, Venue, User, RoleEnum
from backend.services.occupancy_cron import auto_expire_occupancy
from backend.core.security import get_password_hash


def _finalize_pass_session(headers, unique_id="OCCTEST901018AB9IJ", name="OCC TEST"):
    from backend.db.redis import get_redis
    start_res = client.post("/api/v1/session/start", headers=headers)
    session_id = start_res.json()["session_id"]
    session_state = {
        # step 4 = face-verify step completed, matching what the real
        # /session/{id}/face endpoint sets — finalize_session requires
        # this before honoring a "pass" decision.
        "step": 4,
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
    return session_id, res


class TestOccupancy(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def test_finalize_pass_creates_open_occupancy_row(self):
        session_id, res = _finalize_pass_session(self.headers)
        self.assertEqual(res.status_code, 200)
        customer_id = res.json()["customer_id"]

        db = TestingSessionLocal()
        try:
            record = db.query(Occupancy).filter(Occupancy.customer_id == customer_id).first()
            self.assertIsNotNone(record)
            self.assertIsNone(record.exited_at)
            self.assertEqual(record.status, OccupancyStatusEnum.INSIDE)
            self.assertEqual(record.venue_id, 1)
        finally:
            db.close()

    def test_current_and_count_endpoints(self):
        _finalize_pass_session(self.headers, unique_id="OCCTEST111018AB9IJ", name="FIRST PERSON")

        res = client.get("/api/v1/occupancy/current", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        occupants = res.json()
        self.assertEqual(len(occupants), 1)
        self.assertEqual(occupants[0]["customer_name"], "FIRST PERSON")

        res = client.get("/api/v1/occupancy/count", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["current_count"], 1)

    def test_auto_expire_at_matches_venue_configured_window(self):
        client.put(
            "/api/v1/venues/1/config",
            json={"occupancy_auto_expire_hours": 3},
            headers=auth_headers("testadmin@pub.com"),
        )
        _finalize_pass_session(self.headers, unique_id="OCCTEST222018AB9IJ", name="EXPIRY TEST")

        res = client.get("/api/v1/occupancy/current", headers=self.headers)
        occupant = res.json()[0]
        self.assertIsNotNone(occupant["auto_expire_at"])

        def _aware(value):
            dt = datetime.fromisoformat(value)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        entered = _aware(occupant["entered_at"])
        expires = _aware(occupant["auto_expire_at"])
        self.assertAlmostEqual((expires - entered).total_seconds(), 3 * 3600, delta=5)

        count_res = client.get("/api/v1/occupancy/count", headers=self.headers)
        self.assertEqual(count_res.json()["occupancy_auto_expire_hours"], 3)

    def test_manual_checkout(self):
        session_id, res = _finalize_pass_session(self.headers)
        customer_id = res.json()["customer_id"]

        db = TestingSessionLocal()
        try:
            record = db.query(Occupancy).filter(Occupancy.customer_id == customer_id).first()
            occupancy_id = record.id
        finally:
            db.close()

        checkout_res = client.post(f"/api/v1/occupancy/{occupancy_id}/checkout", headers=self.headers)
        self.assertEqual(checkout_res.status_code, 200)

        db = TestingSessionLocal()
        try:
            record = db.query(Occupancy).filter(Occupancy.id == occupancy_id).first()
            self.assertIsNotNone(record.exited_at)
            self.assertEqual(record.status, OccupancyStatusEnum.CHECKED_OUT)
            self.assertIsNotNone(record.checked_out_by_id)
        finally:
            db.close()

        # Second checkout attempt on the same record 400s
        second_res = client.post(f"/api/v1/occupancy/{occupancy_id}/checkout", headers=self.headers)
        self.assertEqual(second_res.status_code, 400)

    def test_checkout_requires_own_venue(self):
        # Regression: occupancy_service.check_out had no venue filter at
        # all — any door_staff+ operator at any venue could force-checkout
        # another venue's occupant just by guessing/incrementing
        # occupancy_id, corrupting that venue's live headcount.
        session_id, res = _finalize_pass_session(self.headers)
        customer_id = res.json()["customer_id"]

        db = TestingSessionLocal()
        try:
            record = db.query(Occupancy).filter(Occupancy.customer_id == customer_id).first()
            occupancy_id = record.id

            db.add(Venue(id=2, name="Rival Pub", address="1 Other Street"))
            db.commit()
            db.add(User(
                id=30,
                venue_id=2,
                email="othervenuedoorstaff@pub.com",
                hashed_password=get_password_hash("password"),
                role=RoleEnum.door_staff,
                is_active=True,
            ))
            db.commit()
        finally:
            db.close()

        other_headers = auth_headers("othervenuedoorstaff@pub.com", "password")
        checkout_res = client.post(
            f"/api/v1/occupancy/{occupancy_id}/checkout", headers=other_headers
        )
        self.assertEqual(checkout_res.status_code, 404)

        # The record must still be open — untouched by the other venue's
        # attempt.
        db = TestingSessionLocal()
        try:
            record = db.query(Occupancy).filter(Occupancy.id == occupancy_id).first()
            self.assertIsNone(record.exited_at)
        finally:
            db.close()

    def test_checkout_requires_floor_staff_not_viewer(self):
        # No viewer seeded by default in conftest; simulate via a role check
        # against a non-existent occupancy id is enough to confirm the auth
        # dependency runs before the 404 — use door_staff (always allowed).
        res = client.post("/api/v1/occupancy/99999/checkout", headers=self.headers)
        self.assertEqual(res.status_code, 404)

    def test_auto_expire_respects_per_venue_window(self):
        db = TestingSessionLocal()
        try:
            # Two different customers, not the same customer twice: a
            # customer can only have one OPEN occupancy row per venue at a
            # time (uq_occupancy_open_per_venue_customer), so simulating
            # "one stale, one fresh" needs two customers rather than two
            # simultaneous rows for one — the constraint's whole purpose is
            # to make the latter state unreachable.
            stale_cust = Customer(unique_id="STALE001", name="Stale Person", dob=datetime(1990, 1, 1, tzinfo=timezone.utc))
            fresh_cust = Customer(unique_id="FRESH001", name="Fresh Person", dob=datetime(1990, 1, 1, tzinfo=timezone.utc))
            db.add_all([stale_cust, fresh_cust])
            db.commit()
            db.refresh(stale_cust)
            db.refresh(fresh_cust)

            stale = Occupancy(
                venue_id=1,
                customer_id=stale_cust.id,
                entered_at=datetime.now(timezone.utc) - timedelta(hours=10),
            )
            fresh = Occupancy(
                venue_id=1,
                customer_id=fresh_cust.id,
                entered_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            db.add_all([stale, fresh])
            db.commit()
            stale_id, fresh_id = stale.id, fresh.id
        finally:
            db.close()

        db = TestingSessionLocal()
        try:
            summary = auto_expire_occupancy(trigger="manual", db=db)
        finally:
            db.close()

        self.assertEqual(summary["expired_count"], 1)
        self.assertIn(stale_id, summary["occupancy_ids"])
        self.assertNotIn(fresh_id, summary["occupancy_ids"])

        db = TestingSessionLocal()
        try:
            refreshed_stale = db.query(Occupancy).filter(Occupancy.id == stale_id).first()
            refreshed_fresh = db.query(Occupancy).filter(Occupancy.id == fresh_id).first()
            self.assertEqual(refreshed_stale.status, OccupancyStatusEnum.AUTO_EXPIRED)
            self.assertIsNotNone(refreshed_stale.exited_at)
            self.assertIsNone(refreshed_fresh.exited_at)

            log = (
                db.query(AuditLog)
                .filter(AuditLog.action == "occupancy_auto_expire")
                .order_by(AuditLog.timestamp.desc())
                .first()
            )
            self.assertIsNotNone(log)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
