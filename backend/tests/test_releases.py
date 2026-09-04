import io
import unittest
from unittest.mock import patch

from backend.tests.conftest import client, init_test_db, auth_headers


class TestReleasesEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()

    def test_latest_release_empty_when_none_published(self):
        response = client.get("/api/v1/releases/latest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["latest_version"])
        self.assertIsNone(data["update_url"])

    def test_publish_release_requires_super_admin(self):
        apk = ("venuepass-1.1.0.apk", io.BytesIO(b"fake apk bytes"), "application/vnd.android.package-archive")
        response = client.post(
            "/api/v1/releases",
            data={"version": "1.1.0", "release_notes": "Bug fixes"},
            files={"apk": apk},
            headers=auth_headers(),  # door_staff
        )
        self.assertEqual(response.status_code, 403)

    def test_publish_and_fetch_latest_release(self):
        apk = ("venuepass-1.1.0.apk", io.BytesIO(b"fake apk bytes"), "application/vnd.android.package-archive")
        with patch("backend.api.release_router.storage_service.upload_apk", return_value="app_releases/venuepass-1.1.0.apk"), \
             patch("backend.api.release_router.storage_service.get_presigned_url", return_value="https://example.com/signed-url"):
            response = client.post(
                "/api/v1/releases",
                data={"version": "1.1.0", "release_notes": "Bug fixes"},
                files={"apk": apk},
                headers=auth_headers("testadmin@pub.com"),
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["version"], "1.1.0")
            self.assertTrue(data["is_latest"])

            latest = client.get("/api/v1/releases/latest")
            self.assertEqual(latest.status_code, 200)
            latest_data = latest.json()
            self.assertEqual(latest_data["latest_version"], "1.1.0")
            self.assertEqual(latest_data["update_url"], "https://example.com/signed-url")
            self.assertEqual(latest_data["release_notes"], "Bug fixes")

    def test_publishing_new_version_supersedes_old_latest(self):
        with patch("backend.api.release_router.storage_service.upload_apk", return_value="app_releases/x.apk"), \
             patch("backend.api.release_router.storage_service.get_presigned_url", return_value="https://example.com/signed-url"):
            apk1 = ("v1.apk", io.BytesIO(b"v1"), "application/vnd.android.package-archive")
            client.post(
                "/api/v1/releases",
                data={"version": "1.0.1", "release_notes": ""},
                files={"apk": apk1},
                headers=auth_headers("testadmin@pub.com"),
            )
            apk2 = ("v2.apk", io.BytesIO(b"v2"), "application/vnd.android.package-archive")
            client.post(
                "/api/v1/releases",
                data={"version": "1.0.2", "release_notes": ""},
                files={"apk": apk2},
                headers=auth_headers("testadmin@pub.com"),
            )

            latest = client.get("/api/v1/releases/latest").json()
            self.assertEqual(latest["latest_version"], "1.0.2")

            releases = client.get("/api/v1/releases", headers=auth_headers("testadmin@pub.com")).json()
            self.assertEqual(len(releases), 2)
            latest_flags = {r["version"]: r["is_latest"] for r in releases}
            self.assertTrue(latest_flags["1.0.2"])
            self.assertFalse(latest_flags["1.0.1"])

    def test_publish_duplicate_version_rejected(self):
        with patch("backend.api.release_router.storage_service.upload_apk", return_value="app_releases/x.apk"), \
             patch("backend.api.release_router.storage_service.get_presigned_url", return_value="https://example.com/signed-url"):
            apk1 = ("v1.apk", io.BytesIO(b"v1"), "application/vnd.android.package-archive")
            client.post(
                "/api/v1/releases",
                data={"version": "1.0.1", "release_notes": ""},
                files={"apk": apk1},
                headers=auth_headers("testadmin@pub.com"),
            )
            apk_dup = ("v1-again.apk", io.BytesIO(b"v1-again"), "application/vnd.android.package-archive")
            response = client.post(
                "/api/v1/releases",
                data={"version": "1.0.1", "release_notes": ""},
                files={"apk": apk_dup},
                headers=auth_headers("testadmin@pub.com"),
            )
            self.assertEqual(response.status_code, 409)

    def test_publish_rejects_non_apk_file(self):
        not_apk = ("readme.txt", io.BytesIO(b"not an apk"), "text/plain")
        response = client.post(
            "/api/v1/releases",
            data={"version": "1.1.0", "release_notes": ""},
            files={"apk": not_apk},
            headers=auth_headers("testadmin@pub.com"),
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
