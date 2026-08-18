import unittest
from backend.tests.conftest import client, init_test_db

class TestAuthEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()

    def test_register_success(self):
        payload = {
            "username": "newguard",
            "email": "guard@venue.com",
            "password": "securepassword123"
        }
        response = client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "guard@venue.com")
        # username is derived from the email (consistent with /login, which
        # has no separate username field to echo back)
        self.assertEqual(data["username"], "guard")
        self.assertIn("token", data)

    def test_register_duplicate_email(self):
        payload = {
            "username": "testop",
            "email": "testoperator@pub.com",
            "password": "password"
        }
        response = client.post("/api/v1/auth/register", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("already registered", response.json()["detail"])

    def test_login_success(self):
        payload = {
            "username": "testoperator@pub.com",
            "password": "password"
        }
        response = client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "testoperator@pub.com")
        self.assertIn("token", data)

    def test_login_invalid_password(self):
        payload = {
            "username": "testoperator@pub.com",
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/login", json=payload)
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid credentials", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
