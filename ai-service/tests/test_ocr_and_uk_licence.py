import unittest
from app.services.ocr.uk_driving_licence_processor import UKDrivingLicenceProcessor
from app.services.ocr.easy_ocr_provider import EasyOCRProvider

class TestOCRAndUKLicence(unittest.TestCase):
    def setUp(self):
        self.processor = UKDrivingLicenceProcessor()
        self.provider = EasyOCRProvider()

    def test_parse_date_formats(self):
        self.assertEqual(self.processor.parse_date("19.12.1995"), "1995-12-19")
        self.assertEqual(self.processor.parse_date("19/12/1995"), "1995-12-19")
        self.assertEqual(self.processor.parse_date("1995-12-19"), "1995-12-19")
        self.assertEqual(self.processor.parse_date("invalid"), "")

    def test_parse_uk_driver_number_male(self):
        # SMITH901018AB9IJ
        # Surname: SMITH
        # Decade: 9 (1990)
        # Month: 01 (Jan, male)
        # Day: 01
        # Year unit: 0 (1990)
        # Initials: AB
        res = self.provider.parse_uk_driver_number("SMITH901010AB9IJ")
        self.assertIsNotNone(res)
        self.assertEqual(res["surname_prefix"], "SMITH")
        self.assertEqual(res["dob"], "1990-01-01")
        self.assertEqual(res["gender"], "Male")
        self.assertEqual(res["initials"], "AB")

    def test_parse_uk_driver_number_female(self):
        # Month code 51 -> Jan (51 - 50 = 1) -> Female
        res = self.provider.parse_uk_driver_number("JONES851155CD8KL")
        self.assertIsNotNone(res)
        self.assertEqual(res["gender"], "Female")
        self.assertEqual(res["dob"], "1985-01-15")

    def test_validate_licence_number_rules(self):
        # 16-char DVLA number
        licence_num = "SMITH901010AB9IJ"
        res = self.processor.validate_licence_number(
            num=licence_num,
            surname="SMITH",
            dob="01.01.1990",
            first_names="ALICE BOB"
        )
        self.assertEqual(res["extracted_dob"], "1990-01-01")
        self.assertEqual(res["extracted_gender"], "Male")

    @staticmethod
    def _box(text, y, x=10, conf=0.9, h=20):
        # Minimal 4-point bbox shaped like EasyOCR's readtext output.
        return ([[x, y], [x + 100, y], [x + 100, y + h], [x, y + h]], text, conf)

    def test_fallback_licence_regex_rejects_garbled_box_when_surname_known(self):
        # Real-world failure mode: field 5's own label match fails, and a
        # merged EasyOCR box (name + DOB digits + initials concatenated by
        # the OCR engine's own text-region detector) coincidentally fits the
        # 16-char licence-number shape. The fallback must not accept it once
        # a genuine surname is already known from field 1, since its
        # DVLA-encoded surname prefix will not match.
        ocr_results = [
            self._box("1. SMITH", y=100),
            self._box("2. JOHN", y=130),
            self._box("3. 01-01-1990", y=160),
            # Field 5 label parsing fails; only this garbled merged box is
            # present, coincidentally 16 chars and shape-valid.
            self._box("JOHNI011081JWIFN", y=400),
        ]
        result = self.processor.process(ocr_results)
        self.assertNotEqual(result["fields"]["licence_number"], "JOHNI011081JWIFN")

    def test_fallback_licence_regex_accepts_genuine_match(self):
        ocr_results = [
            self._box("1. SMITH", y=100),
            self._box("2. JOHN", y=130),
            self._box("3. 01-01-1990", y=160),
            # No "5." label prefix (OCR dropped it), but the number itself
            # correctly encodes the surname/DOB/initials above.
            self._box("SMITH901010JO9IJ", y=400),
        ]
        result = self.processor.process(ocr_results)
        self.assertEqual(result["fields"]["licence_number"], "SMITH901010JO9IJ")

if __name__ == "__main__":
    unittest.main()
