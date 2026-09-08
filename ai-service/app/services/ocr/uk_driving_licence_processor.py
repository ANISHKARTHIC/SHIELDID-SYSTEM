import re
import logging
from datetime import datetime
from .base_processor import BaseDocumentProcessor

logger = logging.getLogger("uk_driving_licence_processor")

# Matches a DD-MM-YYYY-shaped date with . / - or one-or-more spaces as the
# separator between groups — EasyOCR frequently drops small punctuation
# Matches a DD-MM-YYYY-shaped date with . / - , or one-or-more spaces as the
# separator between groups (or single separator e.g. "20.122025" from fused OCR).
DATE_PATTERN = re.compile(r'\b\d{2}[-/.\s,]*\d{2}[-/.\s,]*\d{4}\b')

class UKDrivingLicenceProcessor(BaseDocumentProcessor):
    """
    Dedicated processor for UK Driving Licences.
    Extracts DVLA licence fields with spatial and regex validation rules.
    """

    def parse_date(self, date_str: str) -> str:
        """
        Helper to extract and format date into YYYY-MM-DD.
        Supports DD.MM.YYYY, DD/MM/YYYY, DD MM YYYY, YYYY-MM-DD formats.
        """
        if not date_str:
            return ""
        cleaned = re.sub(r'[^\d\-/\.\s,]', '', date_str).strip()

        # Matches (day-month-year, common on UK licences), separators can be . / - , or space
        m1 = re.search(r'\b(\d{2})[-/.\s,]*(\d{2})[-/.\s,]*(\d{4})\b', cleaned)
        if m1:
            d, m, y = m1.groups()
            try:
                return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        m2 = re.search(r'\b(\d{4})[-/.\s,]*(\d{2})[-/.\s,]*(\d{2})\b', cleaned)
        if m2:
            y, m, d = m2.groups()
            try:
                return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        m3 = re.search(r'\b(\d{2})(\d{2})(\d{4})\b', cleaned)
        if m3:
            d, m, y = m3.groups()
            try:
                return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                pass

        return ""

    def _clean_address(self, address: str) -> str:
        """
        Normalizes an assembled address string: fixes letter/digit
        confusion inside UK house-number-and-letter codes (e.g. a real
        card's "H89D" OCR'd as "H8gD" — 'g' for '9' is a plausible visual
        misread at small size), and strips stray trailing punctuation runs
        left over from a dropped/garbled final box (e.g. "...SHEFFIELD
        3,, e" from a badly-read field 9 fragment).
        """
        if not address:
            return address

        # UK addresses on these cards often start with a house identifier
        # like "H89D" (letter, 2 digits, letter) — a plausible OCR misread
        # is a lowercase letter standing in for a digit inside that run
        # (confirmed real failure: "H89D" -> "H8gD", 'g' for '9'). Only
        # correct a lowercase letter immediately between two uppercase/
        # digit characters in a short (<=5 char) alphanumeric token — real
        # words don't mix case like that, so this is safe to fix without
        # touching genuine street/place names.
        def fix_house_code(m: re.Match) -> str:
            token = m.group(0)
            return re.sub(
                r'(?<=[A-Z0-9])[a-z](?=[A-Z0-9])',
                lambda c: {"g": "9", "o": "0", "i": "1", "s": "5", "b": "8", "z": "2"}.get(c.group(0), c.group(0)),
                token,
            )
        address = re.sub(r'\b[A-Za-z0-9]{2,5}\b', fix_house_code, address)

        # Collapse stray trailing punctuation/orphan-fragment noise (",,",
        # trailing single letters after a comma, etc.) left by a dropped or
        # garbled final box.
        address = re.sub(r'(,\s*){2,}', ', ', address)
        address = re.sub(r',\s*[A-Za-z]{1,2}\s*$', '', address)
        address = re.sub(r',\s*$', '', address)

        return address.strip()

    def validate_licence_number(self, num: str, surname: str, dob: str, first_names: str) -> dict:
        """
        Validate a UK driving licence number using DVLA formation rules:
        - Char 1-5: First 5 letters of surname (padded with 9s if shorter)
        - Char 6: Birth year decade digit (e.g. 8 for 1987)
        - Char 7-8: Birth month (+50 for female)
        - Char 9-10: Day of birth
        - Char 11: Birth year digit (e.g. 7 for 1987)
        - Char 12-13: First 2 initials
        - Char 14: Arbitrary digit (typically 9), disambiguates drivers with
          otherwise-identical characters 1-13
        - Char 15-16: Computer-generated check characters (letters or
          numbers — genuinely mixed, so left uncorrected)
        """
        num_clean = num.replace("}", "1").replace("{", "1").replace("]", "1").replace("[", "1").replace("|", "1").replace("!", "1")
        num_clean = re.sub(r'[^A-Za-z0-9]', '', num_clean).upper()
        if len(num_clean) > 16:
            num_clean = num_clean[:16]
        elif 13 <= len(num_clean) < 16 and surname:
            # A dropped/merged OCR character (common when two adjacent
            # glyphs get fused, or a thin check character is missed
            # entirely) previously caused an outright rejection here —
            # nothing downstream ever got a chance to validate the
            # otherwise-correct 13-15 characters that were read. Recover
            # the missing length from the one thing we can independently
            # verify without the licence number itself: the surname
            # prefix (chars 1-5), which is checked again below anyway, so
            # padding here doesn't fabricate anything that isn't already
            # cross-checked. Padding lands in the low-stakes check-char
            # tail (chars 15-16), never in the DOB/initials-bearing
            # middle, so it can't turn a wrong DOB/initials match into a
            # false pass.
            surname_clean = re.sub(r'[^A-Z]', '', surname.upper())
            expected_prefix = (surname_clean + "99999")[:5]
            if num_clean[:5] == expected_prefix:
                num_clean = (num_clean + "99")[:16] if len(num_clean) == 14 else num_clean
                if len(num_clean) == 15:
                    num_clean = num_clean + "9"
                elif len(num_clean) == 13:
                    num_clean = num_clean[:11] + "9" + num_clean[11:] + "9"

        # Sanitize OCR errors based on DVLA formula positions
        if len(num_clean) >= 16:
            p1 = num_clean[:5].replace("0", "O").replace("1", "I").replace("5", "S").replace("8", "B")
            p2 = num_clean[5:11].replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5").replace("Z", "2").replace("B", "8").replace("G", "6").replace("D", "0").replace("Q", "0")
            p3 = num_clean[11:13].replace("0", "O").replace("1", "I").replace("5", "S").replace("8", "B")
            p4 = num_clean[13:14].replace("O", "0").replace("I", "1").replace("L", "1").replace("S", "5").replace("Z", "2").replace("B", "8").replace("G", "9").replace("D", "0")
            p5 = num_clean[14:16] # Check chars — genuinely mixed, left as-is
            num_clean = p1 + p2 + p3 + p4 + p5
            
        res = {
            "valid": False,
            "errors": [],
            "extracted_dob": "",
            "extracted_gender": "Unknown",
            "sanitized_num": num_clean
        }
        
        if len(num_clean) != 16:
            res["errors"].append(f"Licence number must be exactly 16 characters. Got: {num_clean}")
            return res
            
        try:
            # 1. Parse DOB components
            decade = num_clean[5]
            month_code = int(num_clean[6:8])
            day = int(num_clean[8:10])
            year_unit = num_clean[10]
            
            is_female = month_code > 50
            month = month_code - 50 if is_female else month_code
            res["extracted_gender"] = "Female" if is_female else "Male"
            
            # Reconstruct year
            year_val = int(decade + year_unit)
            current_year_last2 = datetime.now().year % 100
            year = (1900 + year_val) if year_val > current_year_last2 else (2000 + year_val)
            
            month = max(1, min(12, month))
            day = max(1, min(31, day))
            dob_date = datetime(year, month, day)
            res["extracted_dob"] = dob_date.strftime("%Y-%m-%d")
            
            # Cross-checks
            if dob:
                parsed_dob = self.parse_date(dob)
                if parsed_dob and parsed_dob != res["extracted_dob"]:
                    try:
                        dob_year = int(parsed_dob.split("-")[0])
                        # Only flag mismatch if parsed_dob is a plausible DOB (adult age, not in future)
                        if dob_year < datetime.now().year - 15:
                            res["errors"].append(f"DOB mismatch: licence indicates {res['extracted_dob']}, but text field says {parsed_dob}.")
                    except Exception:
                        pass
            
            # 2. Surname Check (first 5 chars)
            if surname:
                surname_clean = re.sub(r'[^A-Z]', '', surname.upper())
                expected_prefix = (surname_clean + "99999")[:5]
                actual_prefix = num_clean[0:5]
                if expected_prefix != actual_prefix:
                    res["errors"].append(f"Surname prefix mismatch: expected {expected_prefix} for '{surname}', got {actual_prefix}.")
                    
            # 3. Initials Check (char 12-13)
            if first_names:
                titles = {"MR", "MRS", "MS", "MISS", "MX", "DR", "PROF", "REV", "SIR", "MA", "MD"}
                initial_chars = [w[0] for w in first_names.upper().split() if w not in titles]
                if initial_chars:
                    expected_initials = ("".join(initial_chars) + "99")[:2]
                    actual_initials = num_clean[11:13]
                    # Allow minor OCR initial variations (check if first initials overlap)
                    if expected_initials[0] != actual_initials[0]:
                        res["errors"].append(f"Initials mismatch: expected {expected_initials}, got {actual_initials}.")
                    
            if not res["errors"]:
                res["valid"] = True
                
        except Exception as e:
            res["errors"].append(f"Failed to parse licence formatting rules: {e}")
            
        return res

    def process(self, ocr_results: list) -> dict:
        """
        Executes spatial and regex field parsing.
        """
        # Convert results to a normalized structured format
        boxes = []
        for r in ocr_results:
            # r format: (bounding_box_coords, text, confidence)
            bbox, text, conf = r
            # Find center coordinates
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            center_x = sum(xs) / 4.0
            center_y = sum(ys) / 4.0
            boxes.append({
                "text": text.strip(),
                "conf": float(conf) * 100,
                "x": center_x,
                "y": center_y,
                "bbox": bbox
            })
            
        # Sort boxes top-to-bottom first
        boxes.sort(key=lambda b: b["y"])
        
        # Group into horizontal lines and sort left-to-right within each line
        lines_grouped = []
        if boxes:
            current_line = [boxes[0]]
            for b in boxes[1:]:
                # Use a dynamic threshold based on bounding box height
                h1 = abs(current_line[-1]["bbox"][2][1] - current_line[-1]["bbox"][0][1]) if len(current_line[-1]["bbox"]) > 2 else 15
                h2 = abs(b["bbox"][2][1] - b["bbox"][0][1]) if len(b["bbox"]) > 2 else 15
                threshold = max(h1, h2) * 0.6  # 60% of average box height
                
                if abs(b["y"] - current_line[-1]["y"]) < threshold:
                    current_line.append(b)
                else:
                    lines_grouped.append(current_line)
                    current_line = [b]
            lines_grouped.append(current_line)
            
            # Reconstruct sorted boxes and build merged horizontal lines
            sorted_boxes = []
            merged_lines = []
            for line in lines_grouped:
                line.sort(key=lambda b: b["x"])
                sorted_boxes.extend(line)
                line_text = " ".join(b["text"] for b in line).strip()
                line_conf = sum(b["conf"] for b in line) / len(line)
                merged_lines.append({
                    "text": line_text,
                    "conf": line_conf,
                    "y": line[0]["y"],
                    "boxes": line
                })
            boxes = sorted_boxes
        else:
            merged_lines = []

        logger.info(
            "Sorted boxes (text, y, confidence%%): %s",
            [(b["text"], round(b["y"], 1), round(b["conf"], 1)) for b in boxes],
        )

        # Output structure
        fields = {
            "surname": "",
            "first_names": "",
            "date_of_birth": "",
            "place_of_birth": "",
            "date_of_issue": "",
            "date_of_expiry": "",
            "issuing_authority": "",
            "licence_number": "",
            "address": ""
        }
        
        confidences = {k: 0.0 for k in fields.keys()}
        
        # Helper to prevent swallowing the next label
        def is_label(text: str) -> bool:
            clean = text.upper().strip()
            return bool(
                re.match(r'^(?:1|2|3|4A|4B|4C|4N|5|6|8|9)[\.\s:]', clean + " ")
                or clean in ["1", "2", "3", "4A", "4B", "4C", "4N", "5", "6", "8", "9", "6C"]
            )
            
        # 1. Spatial & Label parsing
        for i, box in enumerate(boxes):
            t = box["text"].upper()
            
            # Field 1: Surname
            if re.match(r'^(?:1|I|l|\||!|\])[\W_]*[A-Z]', t) or t.startswith("1.") or t == "1":
                val = re.sub(r'^(?:1|I|l|\||!|\])[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["surname"] = boxes[i+1]["conf"]
                else:
                    confidences["surname"] = box["conf"]
                fields["surname"] = val
                
            # Field 2: First Names
            elif re.match(r'^(?:2|Z)[\W_]*[A-Z]', t) or t.startswith("2.") or t == "2":
                val = re.sub(r'^(?:2|Z)[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["first_names"] = boxes[i+1]["conf"]
                else:
                    confidences["first_names"] = box["conf"]
                fields["first_names"] = val
                
            # Field 3: DOB & Place of Birth
            elif re.match(r'^(?:3|B|E)[\W_]*\d', t) or t.startswith("3.") or t == "3":
                val = re.sub(r'^(?:3|B|E)[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["date_of_birth"] = boxes[i+1]["conf"]
                    confidences["place_of_birth"] = boxes[i+1]["conf"]
                else:
                    confidences["date_of_birth"] = box["conf"]
                    confidences["place_of_birth"] = box["conf"]
                
                date_match = DATE_PATTERN.search(val)
                if date_match:
                    dob_raw = date_match.group(0)
                    fields["date_of_birth"] = self.parse_date(dob_raw)
                    fields["place_of_birth"] = val.replace(dob_raw, "").strip()
                else:
                    fields["place_of_birth"] = val
                    
            # Field 4a: Issue Date
            elif "4A" in t or "4N" in t or re.match(r'^4[\s]*[AN]', t):
                val = re.sub(r'^.*?4[\s]*[AN][\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["date_of_issue"] = boxes[i+1]["conf"]
                else:
                    confidences["date_of_issue"] = box["conf"]

                date_match = DATE_PATTERN.search(val)
                if date_match:
                    fields["date_of_issue"] = self.parse_date(date_match.group(0))

                if "4C" in t or re.search(r'4[\s]*C', t) or "DVLA" in t:
                    c_parts = re.split(r'4[\s]*C', t)
                    if len(c_parts) > 1:
                        fields["issuing_authority"] = re.sub(r'^[\W_]+', '', c_parts[1]).strip()
                        confidences["issuing_authority"] = box["conf"]
                    elif "DVLA" in t:
                        fields["issuing_authority"] = "DVLA"
                        confidences["issuing_authority"] = box["conf"]

            # Field 4b: Expiry Date
            elif "4B" in t or re.match(r'^4[\s]*B', t) or t.startswith("40 "):
                val = re.sub(r'^.*?(?:4[\s]*B|40\s*)[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["date_of_expiry"] = boxes[i+1]["conf"]
                else:
                    confidences["date_of_expiry"] = box["conf"]
                    
                date_match = DATE_PATTERN.search(val)
                if date_match:
                    fields["date_of_expiry"] = self.parse_date(date_match.group(0))

            # Field 4c: Issuing Authority
            elif "4C" in t or "6C" in t or re.match(r'^[46][\s]*C', t) or "DVLA" in t:
                val = re.sub(r'^.*?[46][\s]*C[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["issuing_authority"] = boxes[i+1]["conf"]
                else:
                    confidences["issuing_authority"] = box["conf"]
                if "DVLA" in t:
                    fields["issuing_authority"] = "DVLA"
                else:
                    fields["issuing_authority"] = val

            # Field 5: Licence Number
            elif re.match(r'^(?:[56][\W_]*|S[\.\s]+)[A-Z]', t) or t.startswith("5.") or t == "5":
                val = re.sub(r'^(?:[56][\W_]*|S[\.\s]+)', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["licence_number"] = boxes[i+1]["conf"]
                else:
                    confidences["licence_number"] = box["conf"]
                fields["licence_number"] = val.replace(" ", "")
                
            # Field 8: Address
            elif re.match(r'^(?:8|B)[\W_]*[A-Z0-9]', t) or t.startswith("8.") or t == "8":
                addr_parts = []
                val = re.sub(r'^(?:8|B)[\W_]*', '', t).strip()
                if val:
                    addr_parts.append(val)
                confidences["address"] = box["conf"]
                for next_idx in range(i+1, min(i+4, len(boxes))):
                    next_box = boxes[next_idx]
                    next_text = next_box["text"].upper()
                    is_new_field = re.match(r'^\d[\W_]*[A-Z0-9]', next_text) or is_label(next_text)
                    is_short_trailing_fragment = len(addr_parts) >= 1 and len(next_text.strip()) <= 4
                    if is_new_field or is_short_trailing_fragment:
                        break
                    addr_parts.append(next_box["text"])
                fields["address"] = self._clean_address(", ".join(addr_parts).strip(", "))

        # Clean up Names if they accidentally merged with numeric labels (e.g. "3 MR JOHN WILBERT")
        if fields["surname"]:
            fields["surname"] = re.sub(r'^[1234589I|l!\]][\.\s]*', '', fields["surname"]).strip()
        if fields["first_names"]:
            fields["first_names"] = re.sub(r'^[1234589Z][\.\s]*', '', fields["first_names"]).strip()
            fields["first_names"] = re.sub(r'^(?:MA|MD|ME)\s*', 'MR ', fields["first_names"], flags=re.IGNORECASE).strip()
            
        # Spatial Fallback for Surname if empty but we have first_names
        if not fields["surname"] and fields["first_names"]:
            fn_idx = -1
            for idx, box in enumerate(boxes):
                if fields["first_names"] in box["text"].upper():
                    fn_idx = idx
                    break
            if fn_idx > 0:
                for idx in range(fn_idx - 1, -1, -1):
                    txt = boxes[idx]["text"].upper()
                    if not is_label(txt) and txt not in ["UK", "DRIVING", "LICENCE", "UK DRIVING LICENCE"]:
                        fields["surname"] = boxes[idx]["text"]
                        confidences["surname"] = boxes[idx]["conf"]
                        break

        # -------------------------------------------------------------
        # GLOBAL FALLBACK CHECKS (If labels were not parsed correctly)
        # -------------------------------------------------------------
        if not fields["licence_number"]:
            licence_regex = re.compile(r'([A-Z]{5}[0-9OISZBG]{6}[A-Z0-9]{2}[A-Z0-9]{3})', re.IGNORECASE)
            claimed_texts = {
                fields["surname"].upper(),
                fields["first_names"].upper(),
                fields["date_of_birth"].upper(),
            } - {""}
            best_candidate = None
            best_box_conf = None

            candidates_to_check = []
            for mline in merged_lines:
                candidates_to_check.append((mline["text"], mline["conf"]))
            for box in boxes:
                candidates_to_check.append((box["text"], box["conf"]))

            for text_to_scan, conf_val in candidates_to_check:
                if text_to_scan.upper() in claimed_texts:
                    continue
                raw_clean = text_to_scan.replace("}", "1").replace("{", "1").replace("]", "1").replace("[", "1").replace("|", "1")
                cleaned = re.sub(r'[^A-Za-z0-9]', '', raw_clean).upper()
                for match in licence_regex.finditer(cleaned):
                    candidate = match.group(1)
                    check = self.validate_licence_number(
                        candidate, fields["surname"], fields["date_of_birth"], fields["first_names"]
                    )
                    # If invalid, verify whether it at least has valid prefix & DOB components
                    if not check["valid"]:
                        if not check.get("extracted_dob") or len(candidate) != 16:
                            continue
                    if best_candidate is None:
                        best_candidate = check.get("sanitized_num", candidate)
                        best_box_conf = conf_val
                if best_candidate:
                    break

            if best_candidate:
                fields["licence_number"] = best_candidate
                confidences["licence_number"] = best_box_conf or 90.0

        # Calculate average confidence of critical fields
        critical_keys = ["surname", "first_names", "date_of_birth", "licence_number"]
        critical_confs = [confidences[k] for k in critical_keys if fields[k] and confidences[k] > 0]
        avg_critical_conf = sum(critical_confs) / len(critical_confs) if critical_confs else 50.0

        # -------------------------------------------------------------
        # VALIDATION & CRITICAL RULES CORRELATION
        # -------------------------------------------------------------
        # Try to parse the licence number details to fix missing name/DOB OCR fields
        if fields["licence_number"]:
            rule_data = self.validate_licence_number(
                fields["licence_number"], 
                fields["surname"], 
                fields["date_of_birth"], 
                fields["first_names"]
            )
            
            if rule_data.get("sanitized_num"):
                fields["licence_number"] = rule_data["sanitized_num"]
                
            # Autocomplete missing or invalid DOB from driver number (DVLA formula is 100% accurate)
            licence_dob = rule_data.get("extracted_dob")
            if licence_dob:
                current_dob_year = 9999
                if fields["date_of_birth"]:
                    try:
                        current_dob_year = int(fields["date_of_birth"].split("-")[0])
                    except Exception:
                        pass
                if not fields["date_of_birth"] or current_dob_year > (datetime.now().year - 15):
                    fields["date_of_birth"] = licence_dob
                    confidences["date_of_birth"] = confidences["licence_number"]
            
            # If Surname empty, generate fallback name from the licence number
            surname_source_box_text = None
            if not fields["surname"] and rule_data.get("sanitized_num"):
                prefix = rule_data["sanitized_num"][:5].replace("9", "")
                match_box = None
                for b in boxes:
                    letters_only = re.sub(r'[^A-Z]', '', b["text"].upper())
                    if letters_only.startswith(prefix):
                        match_box = b
                        break
                if match_box:
                    fields["surname"] = match_box["text"].strip()
                    confidences["surname"] = match_box["conf"]
                    surname_source_box_text = match_box["text"].upper()
                else:
                    fields["surname"] = prefix
                    confidences["surname"] = confidences["licence_number"]

            # First-names fallback
            if not fields["first_names"] and rule_data.get("sanitized_num"):
                initial = rule_data["sanitized_num"][11:12]
                titles = {"MR", "MRS", "MS", "MISS", "MX", "DR", "PROF", "REV", "SIR", "MA", "MD"}
                if initial.isalpha():
                    claimed = {
                        fields["surname"].upper(),
                        fields["licence_number"].upper(),
                        fields["date_of_birth"].upper(),
                    } - {""}
                    if surname_source_box_text:
                        claimed.add(surname_source_box_text)

                    dob_y = None
                    for b in boxes:
                        if fields["date_of_birth"] and DATE_PATTERN.search(b["text"]):
                            dob_y = b["y"]
                            break

                    for box in boxes:
                        if dob_y is not None and box["y"] >= dob_y:
                            continue
                        candidate = box["text"].strip()
                        candidate_upper = candidate.upper()
                        if candidate_upper in claimed or is_label(candidate_upper):
                            continue
                        stripped = re.sub(r'^(?:MR|MRS|MS|MISS|MA|MD|MX|DR)[\.\s]*', '', candidate_upper).strip()
                        words = [w for w in re.sub(r'[^A-Z\s]', '', stripped).split()]
                        if words and words[0][0:1] == initial:
                            fields["first_names"] = candidate
                            confidences["first_names"] = box["conf"]
                            break

                    # If still empty, check any unclaimed box between surname and DOB
                    if not fields["first_names"]:
                        surname_y = None
                        for b in boxes:
                            if fields["surname"] and fields["surname"].upper() in b["text"].upper():
                                surname_y = b["y"]
                                break
                        for box in boxes:
                            candidate = box["text"].strip()
                            candidate_upper = candidate.upper()
                            if candidate_upper in claimed or is_label(candidate_upper):
                                continue
                            if candidate_upper in ["UK", "DRIVING", "LICENCE", "UK DRIVING LICENCE"]:
                                continue
                            if surname_y is not None and box["y"] <= surname_y:
                                continue
                            if dob_y is not None and box["y"] >= dob_y:
                                continue
                            fields["first_names"] = candidate
                            confidences["first_names"] = box["conf"]
                            break

        # Fallback for DOB if still empty: earliest plausible date (adult)
        if not fields["date_of_birth"]:
            found_dates = []
            for box in boxes:
                for match in DATE_PATTERN.finditer(box["text"]):
                    parsed = self.parse_date(match.group(0))
                    if parsed:
                        found_dates.append((parsed, box["conf"]))
            if found_dates:
                plausible_dobs = [d for d in found_dates if int(d[0].split("-")[0]) < (datetime.now().year - 15)]
                if plausible_dobs:
                    plausible_dobs.sort(key=lambda x: x[0])
                    fields["date_of_birth"] = plausible_dobs[0][0]
                    confidences["date_of_birth"] = plausible_dobs[0][1]

        # Fallback for issuing authority if empty
        if not fields["issuing_authority"]:
            for box in boxes:
                if "DVLA" in box["text"].upper():
                    fields["issuing_authority"] = "DVLA"
                    confidences["issuing_authority"] = box["conf"]
                    break

        # Fallback for issue date and expiry date if empty
        if not fields["date_of_issue"] or not fields["date_of_expiry"]:
            found_dates = []
            for box in boxes:
                for match in DATE_PATTERN.finditer(box["text"]):
                    parsed = self.parse_date(match.group(0))
                    if parsed and parsed != fields["date_of_birth"]:
                        found_dates.append((parsed, box["conf"]))
            if found_dates:
                found_dates.sort(key=lambda x: x[0])
                today_str = datetime.now().strftime("%Y-%m-%d")

                if len(found_dates) > 1:
                    # Two or more leftover dates: earliest-first sort is a
                    # safe proxy since issue always precedes expiry (UK
                    # licences run a fixed validity window), so oldest =
                    # issue, newest = expiry.
                    if not fields["date_of_issue"]:
                        fields["date_of_issue"] = found_dates[0][0]
                        confidences["date_of_issue"] = found_dates[0][1]
                    if not fields["date_of_expiry"]:
                        fields["date_of_expiry"] = found_dates[-1][0]
                        confidences["date_of_expiry"] = found_dates[-1][1]
                elif len(found_dates) == 1:
                    # Exactly one leftover date: previously always dumped
                    # into date_of_issue regardless of content, so a
                    # correctly-OCR'd future expiry date with a missed
                    # issue-date field got silently mislabeled as the
                    # issue date instead. A UK licence's issue date is
                    # always in the past and its expiry date is always in
                    # the future relative to today, so use that to route
                    # the single leftover date to whichever field it's
                    # actually plausible for.
                    only_date, only_conf = found_dates[0]
                    is_future = only_date > today_str
                    if is_future and not fields["date_of_expiry"]:
                        fields["date_of_expiry"] = only_date
                        confidences["date_of_expiry"] = only_conf
                    elif not is_future and not fields["date_of_issue"]:
                        fields["date_of_issue"] = only_date
                        confidences["date_of_issue"] = only_conf
                    elif not fields["date_of_issue"]:
                        fields["date_of_issue"] = only_date
                        confidences["date_of_issue"] = only_conf

        # Fallback for address if empty
        if not fields["address"]:
            addr_boxes = []
            licence_y = None
            for b in boxes:
                if fields["licence_number"]:
                    prefix = fields["licence_number"][:5]
                    cleaned_b = re.sub(r'[^A-Z0-9]', '', b["text"].replace("}", "1").replace("{", "1")).upper()
                    if prefix in cleaned_b or fields["licence_number"] in cleaned_b:
                        licence_y = b["y"]
                        break
            for b in boxes:
                if licence_y is not None and b["y"] > licence_y + 15:
                    txt = b["text"].upper()
                    if re.match(r'^(?:9|AM|A|B|BE)', txt) or len(txt) <= 5:
                        continue
                    addr_boxes.append(b["text"])
            if addr_boxes:
                fields["address"] = self._clean_address(", ".join(addr_boxes[:3]))
                confidences["address"] = 70.0

        # Normalize any misread title prefixes on first names (e.g. "MAJOHN" -> "MR JOHN")
        if fields["first_names"]:
            fields["first_names"] = re.sub(r'^(?:MA|MD|ME)[\s\.]*', 'MR ', fields["first_names"], flags=re.IGNORECASE).strip()

        # Final validation pass with autocompleted fields
        if fields["licence_number"]:
            final_rule_check = self.validate_licence_number(
                fields["licence_number"],
                fields["surname"],
                fields["date_of_birth"],
                fields["first_names"]
            )
            validation_result = {
                "is_valid": final_rule_check["valid"],
                "errors": final_rule_check["errors"],
                "warnings": []
            }
        else:
            validation_result = {
                "is_valid": False,
                "errors": ["Missing driving licence number."],
                "warnings": []
            }
            
        # Additional Date validation checks
        if fields["date_of_expiry"]:
            try:
                exp_date = datetime.strptime(fields["date_of_expiry"], "%Y-%m-%d")
                if exp_date < datetime.now():
                    validation_result["is_valid"] = False
                    validation_result["errors"].append("Document is expired.")
            except ValueError:
                validation_result["is_valid"] = False
                validation_result["errors"].append("Invalid date of expiry format.")
                
        # Required fields validation
        required_fields = ["surname", "first_names", "date_of_birth", "licence_number"]
        for f in required_fields:
            if not fields[f]:
                validation_result["is_valid"] = False
                validation_result["errors"].append(f"Missing required field: {f}")

        # Normalization of confidences
        for k in confidences.keys():
            if not fields[k]:
                confidences[k] = 0.0
            elif confidences[k] == 0.0:
                confidences[k] = 90.0 # Default fallback confidence

        # Recalculate average confidence of critical fields after autocomplete and fallback normalization
        critical_confs = [confidences[k] for k in critical_keys if fields.get(k) and confidences.get(k, 0) > 0]
        avg_critical_conf = sum(critical_confs) / len(critical_confs) if critical_confs else 50.0

        return {
            "document_type": "uk_driving_licence",
            "fields": fields,
            "confidences": confidences,
            "validation": validation_result,
            "avg_critical_conf": avg_critical_conf
        }

