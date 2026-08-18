import unittest
from datetime import datetime, timezone, timedelta
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, Blacklist, AuditLog
from backend.services.retention_cron import delete_expired_records


class TestRetention(unittest.TestCase):
    def setUp(self):
        init_test_db()

    def test_delete_expired_records_anonymizes_expired_customer(self):
        db = TestingSessionLocal()
        try:
            cust = Customer(
                unique_id="EXPIRED001",
                name="John Expired",
                dob=datetime(1990, 1, 1, tzinfo=timezone.utc),
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                is_anonymized=False,
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)
            cust_id = cust.id
        finally:
            db.close()

        db = TestingSessionLocal()
        try:
            summary = delete_expired_records(trigger="manual", db=db)
        finally:
            db.close()
        self.assertEqual(summary["anonymized_count"], 1)
        self.assertIn(cust_id, summary["customer_ids"])

        db = TestingSessionLocal()
        try:
            refreshed = db.query(Customer).filter(Customer.id == cust_id).first()
            self.assertEqual(refreshed.name, "Anonymized")
            self.assertIsNone(refreshed.dob)
            self.assertTrue(refreshed.is_anonymized)

            log = (
                db.query(AuditLog)
                .filter(AuditLog.action == "retention_cleanup")
                .order_by(AuditLog.timestamp.desc())
                .first()
            )
            self.assertIsNotNone(log)
            self.assertEqual(log.details["anonymized_count"], 1)
        finally:
            db.close()

    def test_delete_expired_records_spares_blacklisted_customer(self):
        db = TestingSessionLocal()
        try:
            cust = Customer(
                unique_id="BANNED001",
                name="Jane Banned",
                dob=datetime(1985, 5, 5, tzinfo=timezone.utc),
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                is_anonymized=False,
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)

            ban = Blacklist(
                customer_id=cust.id,
                reason="Violence",
                banned_by_id=1,
                expiry_date=None,  # permanent ban
            )
            db.add(ban)
            db.commit()
            cust_id = cust.id
        finally:
            db.close()

        db = TestingSessionLocal()
        try:
            summary = delete_expired_records(trigger="manual", db=db)
        finally:
            db.close()
        self.assertEqual(summary["skipped_blacklisted_count"], 1)
        self.assertNotIn(cust_id, summary["customer_ids"])

        db = TestingSessionLocal()
        try:
            refreshed = db.query(Customer).filter(Customer.id == cust_id).first()
            self.assertEqual(refreshed.name, "Jane Banned")
            self.assertFalse(refreshed.is_anonymized)
        finally:
            db.close()

    def test_manual_retention_trigger_requires_super_admin(self):
        res = client.post("/api/v1/admin/retention/run", headers=auth_headers())
        self.assertEqual(res.status_code, 403)

        res = client.post("/api/v1/admin/retention/run", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

    def test_retention_logs_endpoint(self):
        db = TestingSessionLocal()
        try:
            delete_expired_records(trigger="scheduled", db=db)
        finally:
            db.close()
        res = client.get("/api/v1/admin/retention/logs", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(res.status_code, 200)
        logs = res.json()
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[0]["details"]["trigger"], "scheduled")


if __name__ == "__main__":
    unittest.main()
