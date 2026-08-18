import unittest
from app.services.risk_engine import calculate_risk
from app.services.data_validation import calculate_age, validate_extracted_data

class TestRiskEngineAndDataValidation(unittest.TestCase):
    def test_calculate_risk_low_risk(self):
        res = calculate_risk(
            ocr_confidence=98.0,
            quality_score=95.0,
            authenticity_score=92.0,
            is_over_18=True,
            venue_status={"blacklisted": False, "incidents": 0}
        )
        self.assertEqual(res["recommendation"], "PASS")
        self.assertTrue(res["risk_score"] < 30)

    def test_calculate_risk_underage(self):
        res = calculate_risk(
            ocr_confidence=98.0,
            quality_score=95.0,
            authenticity_score=90.0,
            is_over_18=False,
            venue_status={"blacklisted": False, "incidents": 0}
        )
        self.assertEqual(res["recommendation"], "DENY")
        self.assertGreaterEqual(res["risk_score"], 80)

    def test_calculate_risk_blacklisted(self):
        res = calculate_risk(
            ocr_confidence=98.0,
            quality_score=95.0,
            authenticity_score=90.0,
            is_over_18=True,
            venue_status={"blacklisted": True, "incidents": 2}
        )
        self.assertEqual(res["recommendation"], "DENY")
        self.assertGreaterEqual(res["risk_score"], 100)

    def test_calculate_age_adult(self):
        res = calculate_age("1995-05-15")
        self.assertIsNotNone(res["age"])
        self.assertTrue(res["is_over_18"])
        self.assertIsNone(res["error"])

    def test_calculate_age_underage(self):
        res = calculate_age("2020-01-01")
        self.assertFalse(res["is_over_18"])

    def test_calculate_age_invalid_date(self):
        res = calculate_age("not-a-date")
        self.assertIsNone(res["age"])
        self.assertIsNotNone(res["error"])

    def test_validate_extracted_data_complete(self):
        ocr_data = {
            "name": "JOHN DOE",
            "dob": "1990-01-01",
            "document_number": "DOE9001018AB1CD"
        }
        res = validate_extracted_data(ocr_data)
        self.assertTrue(res["is_valid"])
        self.assertEqual(len(res["missing_fields"]), 0)

    def test_validate_extracted_data_missing_fields(self):
        ocr_data = {"name": "JOHN DOE"}
        res = validate_extracted_data(ocr_data)
        self.assertFalse(res["is_valid"])
        self.assertIn("dob", res["missing_fields"])
        self.assertIn("document_number", res["missing_fields"])

if __name__ == "__main__":
    unittest.main()
