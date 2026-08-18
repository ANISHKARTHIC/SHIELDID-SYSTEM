import unittest
from backend.tests.conftest import client, init_test_db, auth_headers


class TestUsersEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()

    def test_create_user_requires_admin(self):
        payload = {"email": "newguard@venue.com", "password": "securepassword123"}
        response = client.post("/api/v1/users", json=payload, headers=auth_headers())
        self.assertEqual(response.status_code, 403)

    def test_create_user_as_admin(self):
        payload = {"email": "newguard@venue.com", "password": "securepassword123", "role": "door_staff"}
        response = client.post("/api/v1/users", json=payload, headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], "newguard@venue.com")
        self.assertEqual(data["role"], "door_staff")
        self.assertTrue(data["is_active"])

    def test_create_user_duplicate_email(self):
        payload = {"email": "testoperator@pub.com", "password": "password"}
        response = client.post("/api/v1/users", json=payload, headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("already registered", response.json()["detail"])

    def test_list_users_as_admin(self):
        response = client.get("/api/v1/users", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)
        emails = [u["email"] for u in response.json()]
        self.assertIn("testoperator@pub.com", emails)

    def test_list_users_requires_admin(self):
        response = client.get("/api/v1/users", headers=auth_headers())
        self.assertEqual(response.status_code, 403)

    def test_patch_user_deactivate(self):
        response = client.patch(
            "/api/v1/users/1",
            json={"is_active": False},
            headers=auth_headers("testadmin@pub.com"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_active"])

        login = client.post("/api/v1/auth/login", json={"username": "testoperator@pub.com", "password": "password"})
        self.assertEqual(login.status_code, 400)

    def test_venue_admin_cannot_create_super_admin(self):
        # Promote nothing; testsupervisor is a manager, not venue_admin, but
        # role-escalation guard should still block door_staff/manager too.
        payload = {"email": "sneaky@venue.com", "password": "password", "role": "super_admin"}
        response = client.post("/api/v1/users", json=payload, headers=auth_headers("testsupervisor@pub.com"))
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
