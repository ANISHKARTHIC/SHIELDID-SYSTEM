import unittest
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import Venue, User, RoleEnum, VerificationSession, SessionStateEnum, SessionAuditLog
from backend.core.security import get_password_hash

class TestSupervisorAndReplayEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()
        self.supervisor_headers = auth_headers("testsupervisor@pub.com")

    def _seed_other_venue_manager(self):
        """Second venue with its own manager — used to verify supervisor/
        replay endpoints can't reach Venue 1's data from Venue 2."""
        db = TestingSessionLocal()
        try:
            db.add(Venue(id=2, name="Rival Pub", address="1 Other Street"))
            db.commit()
            db.add(User(
                id=20,
                venue_id=2,
                email="othervenuemanager@pub.com",
                hashed_password=get_password_hash("password"),
                role=RoleEnum.manager,
                is_active=True,
            ))
            db.commit()
        finally:
            db.close()
        return auth_headers("othervenuemanager@pub.com", "password")

    def test_fraud_queue_and_supervisor_decision(self):
        db = TestingSessionLocal()
        session_id = "fraud-session-001"
        try:
            sess = VerificationSession(
                id=session_id,
                venue_id=1,
                operator_id=1,
                state=SessionStateEnum.FRAUD_REVIEW,
                risk_score=92.5
            )
            db.add(sess)
            db.commit()
        finally:
            db.close()

        # 1. Check queue
        res_queue = client.get("/api/v1/supervisor/queue", headers=self.supervisor_headers)
        self.assertEqual(res_queue.status_code, 200)
        items = res_queue.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["session_id"], session_id)

        # 2. Add supervisor note
        res_note = client.post(f"/api/v1/supervisor/{session_id}/notes", json={
            "note_text": "Reviewed secondary document, looks valid"
        }, headers=self.supervisor_headers)
        self.assertEqual(res_note.status_code, 200)
        self.assertTrue(res_note.json()["success"])

        # 3. Make decision
        res_dec = client.post(f"/api/v1/supervisor/{session_id}/decision", json={
            "decision": "APPROVE"
        }, headers=self.supervisor_headers)
        self.assertEqual(res_dec.status_code, 200)
        self.assertEqual(res_dec.json()["new_state"], SessionStateEnum.APPROVED.value)

    def test_fraud_queue_excludes_other_venues(self):
        # Regression: get_fraud_queue had no venue filter — a manager at
        # any venue could see every other venue's fraud-review sessions.
        db = TestingSessionLocal()
        try:
            db.add(VerificationSession(
                id="venue1-fraud", venue_id=1, operator_id=1,
                state=SessionStateEnum.FRAUD_REVIEW, risk_score=80.0,
            ))
            db.commit()
        finally:
            db.close()

        other_headers = self._seed_other_venue_manager()
        res = client.get("/api/v1/supervisor/queue", headers=other_headers)
        self.assertEqual(res.status_code, 200)
        session_ids = [item["session_id"] for item in res.json()]
        self.assertNotIn("venue1-fraud", session_ids)

    def test_supervisor_note_and_decision_require_own_venue(self):
        # Regression: add_supervisor_note/make_supervisor_decision looked
        # up the session by ID alone — a manager at Venue 2 could attach
        # notes to or overturn Venue 1's fraud-review decision.
        db = TestingSessionLocal()
        session_id = "cross-venue-fraud"
        try:
            db.add(VerificationSession(
                id=session_id, venue_id=1, operator_id=1,
                state=SessionStateEnum.FRAUD_REVIEW, risk_score=95.0,
            ))
            db.commit()
        finally:
            db.close()

        other_headers = self._seed_other_venue_manager()

        res_note = client.post(
            f"/api/v1/supervisor/{session_id}/notes",
            json={"note_text": "trying to interfere"},
            headers=other_headers,
        )
        self.assertEqual(res_note.status_code, 404)

        res_dec = client.post(
            f"/api/v1/supervisor/{session_id}/decision",
            json={"decision": "APPROVE"},
            headers=other_headers,
        )
        self.assertEqual(res_dec.status_code, 404)

        # Confirm the session was genuinely untouched.
        db = TestingSessionLocal()
        try:
            sess = db.query(VerificationSession).filter(VerificationSession.id == session_id).first()
            self.assertEqual(sess.state, SessionStateEnum.FRAUD_REVIEW)
        finally:
            db.close()

    def test_replay_and_timeline(self):
        db = TestingSessionLocal()
        session_id = "replay-test-002"
        try:
            sess = VerificationSession(
                id=session_id,
                venue_id=1,
                operator_id=1,
                state=SessionStateEnum.APPROVED,
                final_decision="pass",
                risk_score=5.0
            )
            db.add(sess)
            db.commit()

            log = SessionAuditLog(
                session_id=session_id,
                operator_id=1,
                state_from=SessionStateEnum.CREATED.value,
                state_to=SessionStateEnum.APPROVED.value,
                device_info="iPhone 15 Pro"
            )
            db.add(log)
            db.commit()
        finally:
            db.close()

        # 1. Fetch replay package
        res_replay = client.get(f"/api/v1/replay/{session_id}", headers=self.headers)
        self.assertEqual(res_replay.status_code, 200)
        data = res_replay.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertEqual(data["final_decision"], "pass")

        # 2. Fetch timeline
        res_timeline = client.get(f"/api/v1/replay/{session_id}/timeline", headers=self.headers)
        self.assertEqual(res_timeline.status_code, 200)
        tl = res_timeline.json()
        self.assertEqual(tl["session_id"], session_id)
        self.assertEqual(len(tl["timeline"]), 1)
        self.assertEqual(tl["timeline"][0]["state_to"], SessionStateEnum.APPROVED.value)

    def test_replay_requires_own_venue(self):
        # Regression: get_session_replay/get_session_timeline/
        # get_session_artifacts had no venue check at all — any
        # authenticated staff at any venue could read another venue's
        # full verification package (OCR data, face similarity, image
        # paths) just by knowing the session ID.
        db = TestingSessionLocal()
        session_id = "cross-venue-replay"
        try:
            db.add(VerificationSession(
                id=session_id, venue_id=1, operator_id=1,
                state=SessionStateEnum.APPROVED, final_decision="pass",
            ))
            db.commit()
        finally:
            db.close()

        other_headers = self._seed_other_venue_manager()

        res_replay = client.get(f"/api/v1/replay/{session_id}", headers=other_headers)
        self.assertEqual(res_replay.status_code, 404)

        res_timeline = client.get(f"/api/v1/replay/{session_id}/timeline", headers=other_headers)
        self.assertEqual(res_timeline.status_code, 404)

        res_artifacts = client.get(f"/api/v1/replay/{session_id}/artifacts", headers=other_headers)
        self.assertEqual(res_artifacts.status_code, 404)

if __name__ == "__main__":
    unittest.main()
