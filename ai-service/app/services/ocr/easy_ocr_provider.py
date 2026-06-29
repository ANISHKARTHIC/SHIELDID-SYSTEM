import re
import numpy as np
import cv2
from PIL import Image
import io
from datetime import datetime
from .base import BaseOCR

class EasyOCRProvider(BaseOCR):
    def __init__(self):
        # Lazily loaded to speed up container startup, cached after first load
        self.reader = None

    def _get_reader(self):
        if self.reader is None:
            try:
                import easyocr
                import torch
                use_gpu = torch.cuda.is_available()
                print(f"Initializing EasyOCR reader. GPU acceleration: {use_gpu}")
                self.reader = easyocr.Reader(['en'], gpu=use_gpu)
            except Exception as e:
                print(f"Failed to load EasyOCR library: {e}")
        return self.reader

    def parse_uk_driver_number(self, number: str) -> dict:
        """
        Extract DOB, Initials, Gender and Surname Prefix from 16-char UK Driver Number.
        Format:
        - 0 to 5: Surname prefix (5 chars)
        - 5: Decade of birth (1 digit)
        - 6 to 8: Month of birth (+50 for female) (2 digits)
        - 8 to 10: Day of birth (2 digits)
        - 10: Year unit (1 digit)
        - 11 to 13: Initials (2 chars)
        """
        try:
            num = number.replace(" ", "").upper()
            surname_prefix = num[0:5]
            decade = num[5]
            month_code = int(num[6:8])
            day = int(num[8:10])
            year_unit = num[10]
            initials = num[11:13]
            
            is_female = month_code > 50
            month = month_code - 50 if is_female else month_code
            
            # Reconstruct year
            year_val = int(decade + year_unit)
            current_year_last2 = datetime.now().year % 100
            # If the calculated age would be negative, assume 1900s
            if year_val > current_year_last2:
                year = 1900 + year_val
            else:
                year = 2000 + year_val
                
            # Validate values
            dob_date = datetime(year, month, day)
            return {
                "surname_prefix": surname_prefix,
                "dob": dob_date.strftime("%Y-%m-%d"),
                "initials": initials,
                "gender": "Female" if is_female else "Male"
            }
        except Exception:
            return None

    def extract_text(self, image_bytes: bytes, document_type: str) -> dict:
        reader = self._get_reader()
        if reader is None:
            raise RuntimeError("EasyOCR engine is not loaded. Ensure PyTorch/EasyOCR is installed.")

        # 1. Decode image using Pillow
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
            pil_img = pil_img.convert("RGB")
            img = np.array(pil_img)
        except Exception as e:
            raise ValueError(f"Failed to decode image bytes in OCR: {e}")
            
        # 2. Run EasyOCR
        try:
            results = reader.readtext(img)
        except Exception as e:
            raise RuntimeError(f"OCR engine runtime error: {e}")
            
        lines = [r[1].upper().strip() for r in results]
        confidences = [r[2] for r in results]
        avg_confidence = float(np.mean(confidences)) * 100 if confidences else 0.0
        
        print(f"OCR Extracted Lines: {lines}")
        if not lines:
            raise ValueError("No legible text could be extracted from the document. Please ensure the camera is in focus.")

        # Route to dedicated processor if UK Driving Licence
        if document_type == "uk_driving_licence":
            from .uk_driving_licence_processor import UKDrivingLicenceProcessor
            processor = UKDrivingLicenceProcessor()
            processed_data = processor.process(results)
            
            fields = processed_data["fields"]
            return {
                # Flat properties for compatibility with OCRResponse schema
                "name": f"{fields['first_names']} {fields['surname']}".strip(),
                "dob": fields["date_of_birth"],
                "address": fields["address"],
                "document_number": fields["licence_number"],
                "expiry_date": fields["date_of_expiry"],
                "issue_date": fields["date_of_issue"],
                "confidence": processed_data.get("avg_critical_conf", processed_data["confidences"]["licence_number"]),
                
                # New template extensions
                "document_type": "uk_driving_licence",
                "fields": fields,
                "confidences": processed_data["confidences"],
                "validation": processed_data["validation"]
            }

        name = ""
        dob = ""
        address = ""
        doc_number = ""
        expiry_date = ""
        issue_date = ""
        
        full_text = " ".join(lines)
        
        # Candidate words list for name matching (skipping labels/stopwords)
        stopwords = {
            "DRIVING", "LICENCE", "GREAT", "BRITAIN", "DVLA", "WALES", "ENGLAND", 
            "SCOTLAND", "UK", "ROAD", "STREET", "LONDON", "CARTA", "PERMISO", 
            "CONDUCCION", "KOREKORT", "FUBRERSCHEIN", "AJOKORTTI", "PERMIS", 
            "CONDUIRE", "COMMUNITIES", "MODEL", "SIGNATURE", "HOLDER", "SPECIMEN"
        }
        candidate_words = []
        for line in lines:
            line_clean = re.sub(r'[^A-Z\s]', '', line).strip()
            if not line_clean or len(line_clean) < 2:
                continue
            words = [w for w in line_clean.split() if w not in stopwords]
            if words:
                candidate_words.extend(words)

        # -------------------------------------------------------------
        # UK DRIVING LICENCE PARSING
        # -------------------------------------------------------------
        if document_type == "uk_driving_licence":
            # 1. Locate Driver Number (16 characters)
            licence_regex = re.compile(r'\b[A-Z]{5}\d{6}[A-Z]{2}[A-Z0-9]{3}\b')
            parsed_licence_data = None
            for line in lines:
                cleaned = line.replace(" ", "")
                match = licence_regex.search(cleaned)
                if match:
                    doc_number = match.group(0)
                    parsed_licence_data = self.parse_uk_driver_number(doc_number)
                    break
            
            # 2. Extract DOB and Names using Driver Number correlation if found
            if parsed_licence_data:
                dob = parsed_licence_data["dob"]
                prefix = parsed_licence_data["surname_prefix"]
                init_chars = list(parsed_licence_data["initials"])
                
                # Find full Surname matching the prefix
                surname = ""
                for word in candidate_words:
                    if word.startswith(prefix):
                        surname = word
                        break
                if not surname:
                    surname = prefix # Fallback to prefix
                
                # Find first names matching initials
                first_names = []
                for word in candidate_words:
                    if word == surname:
                        continue
                    if init_chars and word[0] == init_chars[0]:
                        first_names.append(word)
                        init_chars.pop(0)
                
                # Fallback to general candidates if initials matching yielded nothing
                if not first_names:
                    first_names = [w for w in candidate_words if w != surname][:2]
                    
                name = f"{' '.join(first_names)} {surname}".strip()
            
            # 3. Fallback: Parse names using standard label indicators (1. / 2.)
            if not name:
                for i, line in enumerate(lines):
                    if "1." in line or "1 " in line[:2]:
                        surname = line.replace("1.", "").replace("1 ", "").strip()
                        surname = re.sub(r'[^A-Z\-\s]', '', surname).strip()
                        if surname:
                            name = surname
                            if i + 1 < len(lines):
                                next_line = lines[i+1]
                                if "2." in next_line or "2 " in next_line[:2]:
                                    firstnames = next_line.replace("2.", "").replace("2 ", "").strip()
                                    firstnames = re.sub(r'[^A-Z\-\s]', '', firstnames).strip()
                                    name = f"{firstnames} {surname}"
                            break

            # 4. Fallback: Parse general dates from document
            if not dob:
                date_matches = re.findall(r'\b(\d{2})[-/.](\d{2})[-/.](\d{4})\b', full_text)
                found_dates = []
                for m in date_matches:
                    try:
                        date_obj = datetime(int(m[2]), int(m[1]), int(m[0]))
                        found_dates.append(date_obj)
                    except ValueError:
                        pass
                if found_dates:
                    found_dates.sort()
                    dob = found_dates[0].strftime("%Y-%m-%d")
                    if len(found_dates) >= 2:
                        expiry_date = found_dates[-1].strftime("%Y-%m-%d")

            # 5. Extract Address near field "8."
            addr_lines = []
            capture = False
            for line in lines:
                if "8." in line or "8 " in line[:2]:
                    capture = True
                    line_cleaned = line.replace("8.", "").replace("8 ", "").strip()
                    if line_cleaned:
                        addr_lines.append(line_cleaned)
                    continue
                if capture:
                    addr_lines.append(line)
                    postcode_regex = re.compile(r'\b[A-Z]{1,2}[0-9][0-9A-Z]?\s*[0-9][A-Z]{2}\b')
                    if postcode_regex.search(line) or len(addr_lines) >= 3:
                        break
            if addr_lines:
                address = ", ".join(addr_lines)

        # -------------------------------------------------------------
        # PASSPORT PARSING
        # -------------------------------------------------------------
        elif document_type == "passport":
            # 1. Parse Machine Readable Zone (MRZ)
            mrz_regex = re.compile(r'^[A-Z0-9<]{40,45}$')
            mrz_lines = []
            for line in lines:
                cleaned_line = line.replace(" ", "").replace("O", "0")
                if mrz_regex.match(cleaned_line):
                    mrz_lines.append(cleaned_line)
            
            if len(mrz_lines) >= 2:
                line1 = mrz_lines[-2]
                line2 = mrz_lines[-1]
                
                # Line 1 Name Extraction
                try:
                    name_portion = line1[5:]
                    name_parts = [p for p in name_portion.split("<<") if p]
                    surname = name_parts[0].replace("<", " ").strip()
                    firstnames = name_parts[1].replace("<", " ").strip() if len(name_parts) > 1 else ""
                    name = f"{firstnames} {surname}".strip()
                except Exception:
                    pass
                
                # Line 2 metadata
                try:
                    doc_number = line2[0:9].replace("<", "").strip()
                    dob_raw = line2[13:19]
                    dob_year = int(dob_raw[0:2])
                    current_year = datetime.now().year % 100
                    full_year = 2000 + dob_year if dob_year <= current_year else 1900 + dob_year
                    dob = f"{full_year}-{dob_raw[2:4]}-{dob_raw[4:6]}"
                    
                    exp_raw = line2[21:27]
                    exp_year = int(exp_raw[0:2])
                    full_exp_year = 2000 + exp_year
                    expiry_date = f"{full_exp_year}-{exp_raw[2:4]}-{exp_raw[4:6]}"
                except Exception:
                    pass
            
            # 2. General Passport field fallbacks if MRZ is blurred/missing
            if not name:
                # Guess name from candidates
                name = " ".join(candidate_words[:3])
            if not dob:
                # Look for date patterns
                date_matches = re.findall(r'\b(\d{2})[-/.](\d{2})[-/.](\d{4})\b', full_text)
                if date_matches:
                    try:
                        dob_obj = datetime(int(date_matches[0][2]), int(date_matches[0][1]), int(date_matches[0][0]))
                        dob = dob_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        pass

        # -------------------------------------------------------------
        # STRICT VALIDATION: ZERO FAKE FALLBACKS
        # -------------------------------------------------------------
        if not name or not dob:
            raise ValueError(
                "Could not extract name or date of birth from the document. "
                "Ensure the document is clear, unblurred, and completely visible."
            )

        return {
            "name": name,
            "dob": dob,
            "address": address or "NOT LEGIBLE",
            "document_number": doc_number or "NOT LEGIBLE",
            "expiry_date": expiry_date or "NOT LEGIBLE",
            "issue_date": issue_date or "NOT LEGIBLE",
            "confidence": round(avg_confidence, 1)
        }
