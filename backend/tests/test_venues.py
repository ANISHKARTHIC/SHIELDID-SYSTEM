import unittest
from backend.tests.conftest import client, init_test_db, auth_headers


class TestVenuesEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()

    def test_create_venue_as_super_admin(self):
        payload = {"name": "The Other Venue", "address": "99 Second St", "max_capacity": 150}
        response = client.post("/api/v1/venues", json=payload, headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "The Other Venue")
        self.assertEqual(data["max_capacity"], 150)
        self.assertTrue(data["is_active"])

    def test_create_venue_requires_super_admin(self):
        payload = {"name": "Nope", "address": "nowhere"}
        response = client.post("/api/v1/venues", json=payload, headers=auth_headers("testsupervisor@pub.com"))
        self.assertEqual(response.status_code, 403)
        response = client.post("/api/v1/venues", json=payload, headers=auth_headers())
        self.assertEqual(response.status_code, 403)

    def test_list_venues_scoping(self):
        client.post(
            "/api/v1/venues",
            json={"name": "Second Venue", "address": "42 Elsewhere"},
            headers=auth_headers("testadmin@pub.com"),
        )

        # super_admin sees all venues
        response = client.get("/api/v1/venues", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()), 2)

        # non-super_admin only sees their own venue
        response = client.get("/api/v1/venues", headers=auth_headers())
        self.assertEqual(response.status_code, 200)
        venues = response.json()
        self.assertEqual(len(venues), 1)
        self.assertEqual(venues[0]["id"], 1)

    def test_get_other_venue_requires_super_admin(self):
        create_res = client.post(
            "/api/v1/venues",
            json={"name": "Third Venue", "address": "1 Nowhere"},
            headers=auth_headers("testadmin@pub.com"),
        )
        other_venue_id = create_res.json()["id"]

        response = client.get(f"/api/v1/venues/{other_venue_id}", headers=auth_headers())
        self.assertEqual(response.status_code, 403)

        response = client.get(f"/api/v1/venues/{other_venue_id}", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)

    def test_update_venue_as_venue_admin_own_venue(self):
        response = client.put(
            "/api/v1/venues/1",
            json={"max_capacity": 200},
            headers=auth_headers("testadmin@pub.com"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["max_capacity"], 200)

    def test_update_venue_requires_admin_role(self):
        response = client.put(
            "/api/v1/venues/1",
            json={"max_capacity": 999},
            headers=auth_headers(),
        )
        self.assertEqual(response.status_code, 403)

    def test_deactivate_venue_soft_deletes(self):
        create_res = client.post(
            "/api/v1/venues",
            json={"name": "Doomed Venue", "address": "13 Unlucky Ln"},
            headers=auth_headers("testadmin@pub.com"),
        )
        venue_id = create_res.json()["id"]

        response = client.delete(f"/api/v1/venues/{venue_id}", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_active"])

        # Still fetchable directly (not hard-deleted)
        response = client.get(f"/api/v1/venues/{venue_id}", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)

        # Excluded from the default active-only list
        response = client.get("/api/v1/venues", headers=auth_headers("testadmin@pub.com"))
        ids = [v["id"] for v in response.json()]
        self.assertNotIn(venue_id, ids)

    def test_deactivate_venue_requires_super_admin(self):
        response = client.delete("/api/v1/venues/1", headers=auth_headers("testsupervisor@pub.com"))
        self.assertEqual(response.status_code, 403)
        response = client.delete("/api/v1/venues/1", headers=auth_headers())
        self.assertEqual(response.status_code, 403)

    def test_update_venue_partial_does_not_null_untouched_fields(self):
        client.put(
            "/api/v1/venues/1",
            json={"name": "Baseline Pub", "address": "1 Baseline St", "max_capacity": 100},
            headers=auth_headers("testadmin@pub.com"),
        )

        response = client.put(
            "/api/v1/venues/1",
            json={"max_capacity": 250},
            headers=auth_headers("testadmin@pub.com"),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["max_capacity"], 250)
        self.assertEqual(data["name"], "Baseline Pub")
        self.assertEqual(data["address"], "1 Baseline St")

    def test_get_venue_config_includes_occupancy_auto_expire_hours(self):
        response = client.get("/api/v1/venues/1/config", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("occupancy_auto_expire_hours", response.json())
        self.assertEqual(response.json()["occupancy_auto_expire_hours"], 6)

    def test_update_venue_config_occupancy_auto_expire_hours(self):
        response = client.put(
            "/api/v1/venues/1/config",
            json={"occupancy_auto_expire_hours": 12},
            headers=auth_headers("testadmin@pub.com"),
        )
        self.assertEqual(response.status_code, 200)

        followup = client.get("/api/v1/venues/1/config", headers=auth_headers("testadmin@pub.com"))
        self.assertEqual(followup.json()["occupancy_auto_expire_hours"], 12)


if __name__ == "__main__":
    unittest.main()
