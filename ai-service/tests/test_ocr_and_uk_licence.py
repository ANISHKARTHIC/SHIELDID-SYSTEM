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

if __name__ == "__main__":
    unittest.main()
