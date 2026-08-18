import unittest
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, VerificationSession, SessionStateEnum, User

class TestAnalyticsAndSearchEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

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

    def test_analytics_dashboard(self):
        res = client.get("/api/v1/analytics/dashboard?days=7", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_verifications", data)
        self.assertIn("approved", data)
        self.assertIn("denied", data)

if __name__ == "__main__":
    unittest.main()
