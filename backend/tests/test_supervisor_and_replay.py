import unittest
from backend.tests.conftest import client, init_test_db, TestingSessionLocal, auth_headers
from backend.models.models import VerificationSession, SessionStateEnum, SessionAuditLog

class TestSupervisorAndReplayEndpoints(unittest.TestCase):
    def setUp(self):
        init_test_db()
        self.headers = auth_headers()
        self.supervisor_headers = auth_headers("testsupervisor@pub.com")

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

if __name__ == "__main__":
    unittest.main()
