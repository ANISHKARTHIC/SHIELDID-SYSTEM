import unittest
from datetime import datetime, timezone, timedelta
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Customer, Document, Blacklist, Membership, VerificationSession, SessionStateEnum, Occupancy

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

    def test_admin_flush_with_open_occupancy_does_not_fk_violate(self):
        # Regression: Occupancy rows FK-reference both customer_id and
        # session_id. Flush used to delete VerificationSession/Customer rows
        # without clearing Occupancy first, which raised
        # occupancy_records_session_id_fkey / _customer_id_fkey and failed
        # the whole flush for any venue with someone currently checked in.
        db = TestingSessionLocal()
        try:
            cust = Customer(unique_id="OCCFLUSH001", name="Occupant Person")
            db.add(cust)
            db.commit()
            db.refresh(cust)

            session = VerificationSession(
                id="occ-flush-session-1",
                venue_id=1,
                operator_id=1,
                customer_id=cust.id,
                state=SessionStateEnum.APPROVED,
                final_decision="pass",
            )
            db.add(session)
            db.commit()

            db.add(Occupancy(venue_id=1, customer_id=cust.id, session_id=session.id))
            db.commit()
            customer_id = cust.id
        finally:
            db.close()

        res = client.post("/api/v1/admin/flush", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

        db = TestingSessionLocal()
        try:
            self.assertIsNone(db.query(Customer).filter(Customer.id == customer_id).first())
            self.assertIsNone(db.query(Occupancy).filter(Occupancy.customer_id == customer_id).first())
        finally:
            db.close()

    def test_admin_flush_spares_blacklisted_occupant(self):
        # A currently-inside customer who's also banned must survive the
        # flush entirely — including their Occupancy row — since flush only
        # spares blacklisted customers by skipping them, not by force-
        # deleting their occupancy record separately.
        db = TestingSessionLocal()
        try:
            cust = Customer(unique_id="OCCBAN001", name="Banned Occupant")
            db.add(cust)
            db.commit()
            db.refresh(cust)

            session = VerificationSession(
                id="occ-ban-session-1",
                venue_id=1,
                operator_id=1,
                customer_id=cust.id,
                state=SessionStateEnum.APPROVED,
                final_decision="pass",
            )
            db.add(session)
            db.add(Blacklist(customer_id=cust.id, reason="test"))
            db.commit()

            db.add(Occupancy(venue_id=1, customer_id=cust.id, session_id=session.id))
            db.commit()
            customer_id = cust.id
        finally:
            db.close()

        res = client.post("/api/v1/admin/flush", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(res.status_code, 200)

        db = TestingSessionLocal()
        try:
            self.assertIsNotNone(db.query(Customer).filter(Customer.id == customer_id).first())
            self.assertIsNotNone(db.query(Occupancy).filter(Occupancy.customer_id == customer_id).first())
        finally:
            db.close()

if __name__ == "__main__":
    unittest.main()
