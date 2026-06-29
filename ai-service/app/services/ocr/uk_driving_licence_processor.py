import re
from datetime import datetime
from .base_processor import BaseDocumentProcessor

class UKDrivingLicenceProcessor(BaseDocumentProcessor):
    """
    Dedicated processor for UK Driving Licences.
    Extracts DVLA licence fields with spatial and regex validation rules.
    """
    
    def parse_date(self, date_str: str) -> str:
        """
        Helper to extract and format date into YYYY-MM-DD.
        Supports DD.MM.YYYY, DD/MM/YYYY, YYYY-MM-DD formats.
        """
        if not date_str:
            return ""
        # Clean any OCR noise
        cleaned = re.sub(r'[^\d\-/\.]', '', date_str).strip()
        
        # Matches
        m1 = re.search(r'\b(\d{2})[-/.](\d{2})[-/.](\d{4})\b', cleaned)
        if m1:
            d, m, y = m1.groups()
            try:
                return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        m2 = re.search(r'\b(\d{4})[-/.](\d{2})[-/.](\d{2})\b', cleaned)
        if m2:
            y, m, d = m2.groups()
            try:
                return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
            except ValueError:
                pass
        return ""

    def validate_licence_number(self, num: str, surname: str, dob: str, first_names: str) -> dict:
        """
        Validate a UK driving licence number using DVLA formation rules:
        - Char 1-5: First 5 letters of surname (padded with 9s if shorter)
        - Char 6: Birth year decade digit (e.g. 8 for 1987)
        - Char 7-8: Birth month (+50 for female)
        - Char 9-10: Day of birth
        - Char 11: Birth year digit (e.g. 7 for 1987)
        - Char 12-13: First 2 initials
        - Char 14-18: Check characters
        """
        num_clean = num.replace(" ", "").upper()
        
        # Sanitize OCR errors based on DVLA formula positions
        if len(num_clean) >= 16:
            p1 = num_clean[:5].replace("0", "O").replace("1", "I").replace("5", "S").replace("8", "B")
            p2 = num_clean[5:11].replace("O", "0").replace("I", "1").replace("S", "5").replace("Z", "2").replace("B", "8").replace("G", "6")
            p3 = num_clean[11:13].replace("0", "O").replace("1", "I").replace("5", "S").replace("8", "B")
            p4 = num_clean[13:16] # Trim to exactly 16 characters
            num_clean = p1 + p2 + p3 + p4
            
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
            
            dob_date = datetime(year, month, day)
            res["extracted_dob"] = dob_date.strftime("%Y-%m-%d")
            
            # Cross-checks
            if dob:
                parsed_dob = self.parse_date(dob)
                if parsed_dob and parsed_dob != res["extracted_dob"]:
                    res["errors"].append(f"DOB mismatch: licence indicates {res['extracted_dob']}, but text field says {parsed_dob}.")
            
            # 2. Surname Check (first 5 chars)
            if surname:
                surname_clean = re.sub(r'[^A-Z]', '', surname.upper())
                expected_prefix = (surname_clean + "99999")[:5]
                actual_prefix = num_clean[0:5]
                if expected_prefix != actual_prefix:
                    res["errors"].append(f"Surname prefix mismatch: expected {expected_prefix} for '{surname}', got {actual_prefix}.")
                    
            # 3. Initials Check (char 12-13)
            if first_names:
                initial_chars = [w[0] for w in first_names.upper().split() if w not in {"MR", "MRS", "MS", "DR"}]
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
                # bbox format: [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]
                h1 = abs(current_line[-1]["bbox"][2][1] - current_line[-1]["bbox"][0][1]) if len(current_line[-1]["bbox"]) > 2 else 15
                h2 = abs(b["bbox"][2][1] - b["bbox"][0][1]) if len(b["bbox"]) > 2 else 15
                threshold = max(h1, h2) * 0.6  # 60% of average box height
                
                if abs(b["y"] - current_line[-1]["y"]) < threshold:
                    current_line.append(b)
                else:
                    lines_grouped.append(current_line)
                    current_line = [b]
            lines_grouped.append(current_line)
            
            # Reconstruct sorted boxes
            sorted_boxes = []
            for line in lines_grouped:
                line.sort(key=lambda b: b["x"])
                sorted_boxes.extend(line)
            boxes = sorted_boxes
        
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
            # Matches exactly: 1., 2., 3., 4a, 4b, 4c, 5., 8., 9.
            return bool(re.match(r'^(1|2|3|4A|4B|4C|5|8|9)[\.\s]', text.upper() + " "))
            
        # 1. Spatial & Label parsing
        for i, box in enumerate(boxes):
            t = box["text"].upper()
            
            # Field 1: Surname
            if re.match(r'^1[\W_]*[A-Z]', t) or t.startswith("1.") or t == "1":
                val = re.sub(r'^1[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["surname"] = boxes[i+1]["conf"]
                else:
                    confidences["surname"] = box["conf"]
                fields["surname"] = val
                
            # Field 2: First Names
            elif re.match(r'^2[\W_]*[A-Z]', t) or t.startswith("2.") or t == "2":
                val = re.sub(r'^2[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["first_names"] = boxes[i+1]["conf"]
                else:
                    confidences["first_names"] = box["conf"]
                fields["first_names"] = val
                
            # Field 3: DOB & Place of Birth
            elif re.match(r'^3[\W_]*\d', t) or t.startswith("3.") or t == "3":
                val = re.sub(r'^3[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["date_of_birth"] = boxes[i+1]["conf"]
                    confidences["place_of_birth"] = boxes[i+1]["conf"]
                else:
                    confidences["date_of_birth"] = box["conf"]
                    confidences["place_of_birth"] = box["conf"]
                
                date_match = re.search(r'\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b', val)
                if date_match:
                    dob_raw = date_match.group(0)
                    fields["date_of_birth"] = self.parse_date(dob_raw)
                    fields["place_of_birth"] = val.replace(dob_raw, "").strip()
                else:
                    fields["place_of_birth"] = val
                    
            # Field 4a & 4c: Issue Date & Issuing Authority
            elif "4A" in t or re.match(r'^4[\s]*A', t):
                val = re.sub(r'^.*?4[\s]*A[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["date_of_issue"] = boxes[i+1]["conf"]
                else:
                    confidences["date_of_issue"] = box["conf"]
                    
                date_match = re.search(r'\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b', val)
                if date_match:
                    fields["date_of_issue"] = self.parse_date(date_match.group(0))
                
                if "4C" in t or re.search(r'4[\s]*C', t):
                    c_parts = re.split(r'4[\s]*C', t)
                    if len(c_parts) > 1:
                        fields["issuing_authority"] = re.sub(r'^[\W_]+', '', c_parts[1]).strip()
                        confidences["issuing_authority"] = box["conf"]
                        
            # Field 4b: Expiry Date
            elif "4B" in t or re.match(r'^4[\s]*B', t):
                val = re.sub(r'^.*?4[\s]*B[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["date_of_expiry"] = boxes[i+1]["conf"]
                else:
                    confidences["date_of_expiry"] = box["conf"]
                    
                date_match = re.search(r'\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b', val)
                if date_match:
                    fields["date_of_expiry"] = self.parse_date(date_match.group(0))
                    
            # Field 5: Licence Number
            elif re.match(r'^5[\W_]*[A-Z]', t) or t.startswith("5.") or t == "5":
                val = re.sub(r'^5[\W_]*', '', t).strip()
                if not val and i+1 < len(boxes) and not is_label(boxes[i+1]["text"].upper()):
                    val = boxes[i+1]["text"]
                    confidences["licence_number"] = boxes[i+1]["conf"]
                else:
                    confidences["licence_number"] = box["conf"]
                fields["licence_number"] = val.replace(" ", "")
                
            # Field 8: Address
            elif re.match(r'^8[\W_]*[A-Z0-9]', t) or t.startswith("8.") or t == "8":
                addr_parts = []
                val = re.sub(r'^8[\W_]*', '', t).strip()
                if val:
                    addr_parts.append(val)
                confidences["address"] = box["conf"]
                for next_idx in range(i+1, min(i+4, len(boxes))):
                    next_box = boxes[next_idx]
                    next_text = next_box["text"].upper()
                    if re.match(r'^\d[\W_]*[A-Z0-9]', next_text) or next_text in ["1", "2", "3", "4A", "4B", "4C", "5", "8", "9"]:
                        break
                    addr_parts.append(next_box["text"])
                fields["address"] = ", ".join(addr_parts).strip(", ")

        # Clean up Names if they accidentally merged with numeric labels (e.g. "3 MR JOHN WILBERT")
        if fields["surname"]:
            fields["surname"] = re.sub(r'^[1234589][\.\s]*', '', fields["surname"]).strip()
        if fields["first_names"]:
            fields["first_names"] = re.sub(r'^[1234589][\.\s]*', '', fields["first_names"]).strip()
            
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
            # General regex search for 16-char licence number (lenient for OCR errors and attached issue numbers)
            licence_regex = re.compile(r'([A-Z]{5}[0-9OISZBG]{6}[A-Z]{2}[A-Z0-9OISZBG]{3})', re.IGNORECASE)
            for box in boxes:
                cleaned = box["text"].replace(" ", "").upper()
                match = licence_regex.search(cleaned)
                if match:
                    fields["licence_number"] = match.group(1)
                    confidences["licence_number"] = box["conf"]
                    break

        if not fields["date_of_birth"]:
            # If DOB label failed, parse earliest date found in the file
            date_regex = re.compile(r'\b\d{2}[-/\.]\d{2}[-/\.]\d{4}\b')
            found_dates = []
            for box in boxes:
                for match in date_regex.finditer(box["text"]):
                    parsed = self.parse_date(match.group(0))
                    if parsed:
                        found_dates.append((parsed, box["conf"]))
            if found_dates:
                found_dates.sort(key=lambda x: x[0]) # Ascending order
                fields["date_of_birth"] = found_dates[0][0]
                confidences["date_of_birth"] = found_dates[0][1]

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
            
            # Apply sanitized number to fields
            if rule_data.get("sanitized_num"):
                fields["licence_number"] = rule_data["sanitized_num"]
                
            # Autocomplete missing values from the driver number (DVLA formula is 100% accurate)
            if not fields["date_of_birth"] and rule_data["extracted_dob"]:
                fields["date_of_birth"] = rule_data["extracted_dob"]
                confidences["date_of_birth"] = confidences["licence_number"]
            
            # If DOB and Names still empty, generate fallback names from the licence number
            if not fields["surname"] and rule_data.get("sanitized_num"):
                fields["surname"] = rule_data["sanitized_num"][:5].replace("9", "")
                confidences["surname"] = confidences["licence_number"]
                
            validation_result = {
                "is_valid": rule_data["valid"],
                "errors": rule_data["errors"],
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
                
        return {
            "document_type": "uk_driving_licence",
            "fields": fields,
            "confidences": confidences,
            "validation": validation_result,
            "avg_critical_conf": avg_critical_conf
        }
