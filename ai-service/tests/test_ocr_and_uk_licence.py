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

    def test_parse_date_handles_ocr_dropped_periods(self):
        # Regression: EasyOCR frequently drops small punctuation like the
        # periods in a UK licence's compact date fields. The old cleaning
        # step stripped whitespace entirely (not just non-date chars),
        # which glued "15 06 2020" into "15062020" — a shape no date
        # pattern matched, silently leaving the field empty.
        self.assertEqual(self.processor.parse_date("15 06 2020"), "2020-06-15")
        self.assertEqual(self.processor.parse_date("15  06  2020"), "2020-06-15")
        # Every separator dropped, including spaces — falls back to DD MM
        # YYYY interpretation of the glued digit run.
        self.assertEqual(self.processor.parse_date("15062020"), "2020-06-15")

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

    def test_issuing_authority_extracted_from_standalone_4c_line(self):
        # Regression: real DVLA cards print 4a/4b/4c as three separate
        # lines, not merged into one OCR box. issuing_authority used to be
        # populated only via a nested check inside the 4A branch, so it
        # silently stayed empty for this — the normal — case, since there
        # was no standalone "elif 4C" branch at all.
        ocr_results = [
            self._box("1. SMITH", y=80),
            self._box("2. JOHN MICHAEL", y=110),
            self._box("3. 01.01.1990 UK", y=140),
            self._box("4a. 15.06.2020", y=170),
            self._box("4b. 14.06.2030", y=200),
            self._box("4c. DVLA", y=230),
            self._box("5. SMITH901010JM9IJ", y=260),
        ]
        result = self.processor.process(ocr_results)
        fields = result["fields"]
        self.assertEqual(fields["issuing_authority"], "DVLA")
        self.assertEqual(fields["date_of_issue"], "2020-06-15")
        self.assertEqual(fields["date_of_expiry"], "2030-06-14")

    def test_issuing_authority_extracted_from_merged_4a_4c_line(self):
        # The original merged-box code path (4a and 4c OCR'd onto the same
        # line) must keep working alongside the new standalone-4C branch.
        ocr_results = [
            self._box("1. SMITH", y=80),
            self._box("2. JOHN", y=110),
            self._box("3. 01.01.1990", y=140),
            self._box("4a. 15.06.2020 4c. DVLA", y=170),
            self._box("4b. 14.06.2030", y=200),
            self._box("5. SMITH901010JO9IJ", y=230),
        ]
        result = self.processor.process(ocr_results)
        fields = result["fields"]
        self.assertEqual(fields["issuing_authority"], "DVLA")
        self.assertEqual(fields["date_of_issue"], "2020-06-15")

    def test_full_extraction_survives_ocr_dropped_periods(self):
        # Regression: realistic noisy OCR output with periods dropped from
        # every field (common — periods are small and easily missed by the
        # text detector, especially at lower resolution/blur). Before the
        # date-regex fix, date_of_issue/date_of_expiry silently stayed
        # empty and place_of_birth incorrectly retained the full "01 01
        # 1990 UK" string instead of extracting just "UK".
        ocr_results = [
            self._box("1 SMITH", y=80),
            self._box("2 JOHN MICHAEL", y=110),
            self._box("3 01 01 1990 UK", y=140),
            self._box("4a 15 06 2020", y=170),
            self._box("4b 14 06 2030", y=200),
            self._box("4c DVLA", y=230),
            self._box("5 SMITH901010JM9IJ", y=260),
        ]
        result = self.processor.process(ocr_results)
        fields = result["fields"]
        self.assertEqual(fields["date_of_birth"], "1990-01-01")
        self.assertEqual(fields["place_of_birth"], "UK")
        self.assertEqual(fields["date_of_issue"], "2020-06-15")
        self.assertEqual(fields["date_of_expiry"], "2030-06-14")
        self.assertEqual(fields["issuing_authority"], "DVLA")
        self.assertTrue(result["validation"]["is_valid"])

    def test_miss_title_excluded_from_initials_check(self):
        # Regression: found on a real UK licence — "MISS GRACELIN
        # PRIYANKA" was mismatched against a genuinely correct licence
        # number because "MISS" wasn't in the title stopword list, so the
        # initials check picked "MG" (Miss, Gracelin) instead of "GP"
        # (Gracelin, Priyanka) and falsely flagged the number as invalid.
        res = self.processor.validate_licence_number(
            num="HENRY061082GP9TF",
            surname="HENRY",
            dob="08.11.2002",
            first_names="MISS GRACELIN PRIYANKA",
        )
        self.assertTrue(res["valid"], res["errors"])
        self.assertEqual(res["errors"], [])

    def test_check_digit_position_14_gets_letter_to_digit_correction(self):
        # Regression: position 14 (the DVLA formula's "arbitrary digit,
        # typically 9") previously had zero character-confusion
        # correction — a printed "9" that EasyOCR misread as "I" (visually
        # similar in the DVLA card font) passed straight through
        # uncorrected. Confirmed on a real card: HENRY061082GP9TF OCR'd as
        # HENRY061082GPITF. The formula itself can't recover the exact
        # original digit (position 14 carries no checkable information —
        # it's arbitrary by design), but it must at least get the standard
        # letter/digit confusion correction applied, same as every other
        # digit position in the number.
        res = self.processor.validate_licence_number(
            num="HENRY061082GPITF",
            surname="HENRY",
            dob="08.11.2002",
            first_names="MISS GRACELIN PRIYANKA",
        )
        self.assertTrue(res["valid"], res["errors"])
        self.assertEqual(res["sanitized_num"][13], "1")  # I -> 1, not left as I

if __name__ == "__main__":
    unittest.main()
