import unittest
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, VerificationSession, SessionStateEnum, User, Venue, RoleEnum
from backend.core.security import get_password_hash

class TestAnalyticsAndSearchEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def _seed_other_venue_and_session(self, session_id="venue2-session", email="othervenueuser@pub.com"):
        db = TestingSessionLocal()
        try:
            db.add(Venue(id=2, name="Rival Pub", address="1 Other Street"))
            db.commit()
            db.add(User(
                id=40,
                venue_id=2,
                email=email,
                hashed_password=get_password_hash("password"),
                role=RoleEnum.door_staff,
                is_active=True,
            ))
            db.add(VerificationSession(
                id=session_id, venue_id=2, operator_id=40,
                state=SessionStateEnum.APPROVED,
            ))
            db.commit()
        finally:
            db.close()
        return auth_headers(email, "password")

    def test_global_search(self):
        db = TestingSessionLocal()
        try:
            cust = Customer(unique_id="SEARCH999", name="ARTHUR DENT")
            db.add(cust)
            sess = VerificationSession(id="sess-search-456", venue_id=1, operator_id=1, state=SessionStateEnum.APPROVED)
            db.add(sess)
            db.commit()
        finally:
            db.close()

        # Search for ARTHUR
        res = client.get("/api/v1/search/?q=ARTHUR", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["customers"]), 1)
        self.assertEqual(data["customers"][0]["name"], "ARTHUR DENT")

        # Search for session
        res_sess = client.get("/api/v1/search/?q=sess-search", headers=self.headers)
        self.assertEqual(res_sess.status_code, 200)
        self.assertEqual(len(res_sess.json()["sessions"]), 1)

    def test_global_search_excludes_other_venues_sessions_and_users(self):
        # Regression: session and user search had no venue filter — any
        # authenticated user could enumerate other venues' session IDs
        # (feeding into the replay endpoints) and staff emails/roles.
        self._seed_other_venue_and_session(
            session_id="venue2-search-target", email="findme@othervenue.com"
        )

        res_sess = client.get("/api/v1/search/?q=venue2-search", headers=self.headers)
        self.assertEqual(res_sess.status_code, 200)
        self.assertEqual(res_sess.json()["sessions"], [])

        res_user = client.get("/api/v1/search/?q=findme", headers=self.headers)
        self.assertEqual(res_user.status_code, 200)
        self.assertEqual(res_user.json()["users"], [])

    def test_export_fraud_csv(self):
        db = TestingSessionLocal()
        try:
            sess = VerificationSession(
                id="fraud-export-789",
                venue_id=1,
                operator_id=1,
                state="FRAUD_REVIEW",
                risk_score=88.0,
                final_decision="fraud"
            )
            db.add(sess)
            db.commit()
        finally:
            db.close()

        res = client.get("/api/v1/export/csv/fraud", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("content-type", ""))
        self.assertIn("fraud-export-789", res.text)

    def test_export_fraud_csv_excludes_other_venues_by_default(self):
        # Regression: a door_staff at Venue 1 could previously omit
        # venue_id (or pass Venue 2's) to export another venue's
        # fraud-review sessions. Now defaults to the caller's own venue.
        db = TestingSessionLocal()
        try:
            db.add(Venue(id=2, name="Rival Pub", address="1 Other Street"))
            db.commit()
            db.add(VerificationSession(
                id="venue2-fraud-export", venue_id=2, operator_id=1,
                state="FRAUD_REVIEW", risk_score=90.0,
            ))
            db.commit()
        finally:
            db.close()

        res = client.get("/api/v1/export/csv/fraud", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("venue2-fraud-export", res.text)

        # Explicitly requesting another venue's export is also denied for
        # a non-super_admin (silently redirected back to their own venue).
        res_explicit = client.get("/api/v1/export/csv/fraud?venue_id=2", headers=self.headers)
        self.assertEqual(res_explicit.status_code, 200)
        self.assertNotIn("venue2-fraud-export", res_explicit.text)

    def test_analytics_dashboard(self):
        res = client.get("/api/v1/analytics/dashboard?days=7", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_verifications", data)
        self.assertIn("approved", data)
        self.assertIn("denied", data)

    def test_analytics_venues_requires_super_admin(self):
        # Regression: get_venue_performance had no role gate — any
        # authenticated door_staff could compare every venue's fraud rate.
        res = client.get("/api/v1/analytics/venues", headers=self.headers)
        self.assertEqual(res.status_code, 403)

        res_admin = client.get("/api/v1/analytics/venues", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(res_admin.status_code, 200)

if __name__ == "__main__":
    unittest.main()
