from datetime import datetime
from dateutil import parser
import logging
import math

logger = logging.getLogger("data_validation")

def calculate_age(dob_str: str) -> dict:
    """
    Parses DOB and calculates current age.
    """
    try:
        # dayfirst=True: UK documents (the only document types this service
        # parses) use DD/MM/YYYY, but dateutil.parser.parse defaults to
        # month-first for ambiguous numeric dates (e.g. "03/04/1990" would
        # otherwise parse as March 4th instead of April 3rd). ISO
        # "YYYY-MM-DD" strings — what the licence processor's own
        # parse_date normally hands this function — are unambiguous and
        # unaffected by this flag either way.
        dob = parser.parse(dob_str, dayfirst=True)
        today = datetime.today()

        # Calculate precise age
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

        is_over_18 = age >= 18

        return {
            "age": age,
            "is_over_18": is_over_18,
            "error": None
        }
    except Exception as e:
        logger.debug("calculate_age failed to parse dob_str=%r: %s", dob_str, e)
        return {
            "age": None,
            "is_over_18": None,
            "error": "Invalid date format"
        }

def validate_extracted_data(ocr_data: dict) -> dict:
    """
    Validates required fields and checks date formats.
    """
    required_fields = ["name", "dob", "document_number"]
    missing_fields = [f for f in required_fields if not ocr_data.get(f)]
    
    age_check = {"age": None, "is_over_18": None}
    if ocr_data.get("dob"):
        age_check = calculate_age(ocr_data["dob"])
        
    is_valid = len(missing_fields) == 0 and age_check["error"] is None

    return {
        "is_valid": is_valid,
        "missing_fields": missing_fields,
        "age_verification": age_check
    }
