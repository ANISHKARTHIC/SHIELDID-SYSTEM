import unittest
from backend.tests.conftest import client, init_test_db, auth_headers

class TestVenuesEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()
        self.admin_headers = auth_headers("testadmin@pub.com")

    def test_get_and_update_venue_config(self):
        # 1. Get config
        res = client.get("/api/v1/venues/1/config", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("allowed_documents", data)
        self.assertIn("verification_mode", data)

        # 2. Update config (requires admin role)
        update_payload = {
            "verification_mode": "ai_assisted",
            "retention_days_success": 14
        }
        res_update = client.put("/api/v1/venues/1/config", json=update_payload, headers=self.admin_headers)
        self.assertEqual(res_update.status_code, 200)

        # 3. Verify changes
        res_verify = client.get("/api/v1/venues/1/config", headers=self.headers)
        self.assertEqual(res_verify.status_code, 200)
        self.assertEqual(res_verify.json()["verification_mode"], "ai_assisted")
        self.assertEqual(res_verify.json()["retention_days_success"], 14)

    def test_get_and_update_venue_policy(self):
        res = client.get("/api/v1/venues/1/policy", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["minimum_age"], 18)

        # Update policy (requires admin role)
        update_payload = {
            "minimum_age": 21,
            "require_face_match": True,
            "face_similarity_threshold": 0.85
        }
        res_update = client.put("/api/v1/venues/1/policy", json=update_payload, headers=self.admin_headers)
        self.assertEqual(res_update.status_code, 200)

        res_verify = client.get("/api/v1/venues/1/policy", headers=self.headers)
        self.assertEqual(res_verify.status_code, 200)
        self.assertEqual(res_verify.json()["minimum_age"], 21)
        self.assertTrue(res_verify.json()["require_face_match"])
        self.assertEqual(res_verify.json()["face_similarity_threshold"], 0.85)

if __name__ == "__main__":
    unittest.main()
