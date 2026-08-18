import unittest
from datetime import datetime, timezone, timedelta
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, Document, Blacklist, Membership, VerificationSession, SessionStateEnum

class TestVisitorsEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()

    def test_get_visitors_empty(self):
        res = client.get("/api/v1/visitors", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), [])

    def test_get_visitors_with_data(self):
        db = TestingSessionLocal()
        try:
            # Seed a customer
            dob = datetime(1995, 6, 15, tzinfo=timezone.utc)
            cust = Customer(
                unique_id="DOE950615AB1CD",
                name="JANE DOE",
                dob=dob,
                vip_tier="Gold",
                notes="Regular VIP guest"
            )
            db.add(cust)
            db.commit()
            db.refresh(cust)

            doc = Document(
                customer_id=cust.id,
                doc_type="uk_driving_licence",
                doc_number="DOE950615AB1CD",
                expiry_date=datetime(2035, 6, 15, tzinfo=timezone.utc),
                nationality="GBR"
            )
            db.add(doc)

            mem = Membership(
                customer_id=cust.id,
                tier="VIP"
            )
            db.add(mem)

            session = VerificationSession(
                id="test-session-123",
                venue_id=1,
                operator_id=1,
                customer_id=cust.id,
                state=SessionStateEnum.APPROVED,
                final_decision="pass"
            )
            db.add(session)
            db.commit()
        finally:
            db.close()

        res = client.get("/api/v1/visitors", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        visitors = res.json()
        self.assertEqual(len(visitors), 1)
        v = visitors[0]
        self.assertEqual(v["name"], "JANE DOE")
        self.assertEqual(v["documentNumber"], "DOE950615AB1CD")
        self.assertEqual(v["documentType"], "uk_driving_licence")
        self.assertEqual(v["membership"], "VIP")
        self.assertEqual(v["vipTier"], "Gold")
        self.assertEqual(v["visitCount"], 1)
        self.assertTrue(v["age"] >= 18)

    def test_admin_flush(self):
        db = TestingSessionLocal()
        try:
            cust = Customer(unique_id="FLUSH123", name="FLUSH ME")
            db.add(cust)
            db.commit()
        finally:
            db.close()

        res = client.post("/api/v1/admin/flush", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])

if __name__ == "__main__":
    unittest.main()
