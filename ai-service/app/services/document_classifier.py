import re

# Same 16-char UK driving licence number shape the OCR field parser looks
# for (app/services/ocr/uk_driving_licence_processor.py), reused here as
# real evidence of document content rather than guessed from a filename.
_LICENCE_NUMBER_REGEX = re.compile(r'\b[A-Z]{5}\d{6}[A-Z]{2}[A-Z0-9]{3}\b')
# MRZ line shape, matching the pattern the passport OCR parser looks for.
_MRZ_REGEX = re.compile(r'^[A-Z0-9<]{40,45}$')

_LICENCE_MARKERS = ("DRIVING LICENCE", "DRIVING LICENSE", "DVLA", "DRIVER")
_PASSPORT_MARKERS = ("PASSPORT", "PASSEPORT")


def classify_document(image_bytes: bytes, filename: str = "") -> dict:
    """
    Classifies the document type from real text content in the image via
    OCR, instead of guessing from the filename or image aspect ratio.
    Confidence is derived from the actual evidence found (marker text
    matches, licence-number/MRZ shape matches, and their OCR confidences),
    not a fixed constant.
    """
    from app.services.ocr.easy_ocr_provider import EasyOCRProvider

    try:
        lines = EasyOCRProvider().read_raw_lines(image_bytes)
    except Exception:
        # No legible text at all — can't classify by content. Caller
        # decides how to handle "unknown" (e.g. still gated by the
        # face-presence check upstream).
        return {"document_type": "unknown", "confidence": 0.0}

    licence_evidence: list[float] = []
    passport_evidence: list[float] = []

    for text, conf in lines:
        cleaned = text.replace(" ", "")

        if any(marker in text for marker in _LICENCE_MARKERS):
            licence_evidence.append(conf)
        if any(marker in text for marker in _PASSPORT_MARKERS):
            passport_evidence.append(conf)
        if _LICENCE_NUMBER_REGEX.search(cleaned):
            licence_evidence.append(max(conf, 80.0))
        if _MRZ_REGEX.match(cleaned):
            passport_evidence.append(max(conf, 80.0))

    if not licence_evidence and not passport_evidence:
        return {"document_type": "unknown", "confidence": 0.0}

    if len(licence_evidence) >= len(passport_evidence):
        detected_class = "uk_driving_licence"
        evidence = licence_evidence
    else:
        detected_class = "passport"
        evidence = passport_evidence

    # More independent evidence lines and higher OCR confidence on them
    # both raise confidence; capped well under 100 since this is still a
    # heuristic over OCR text, not a trained visual classifier.
    avg_conf = sum(evidence) / len(evidence)
    evidence_boost = min(len(evidence) * 8.0, 24.0)
    confidence = min(0.95, (avg_conf / 100.0) * 0.7 + (evidence_boost / 100.0))

    return {
        "document_type": detected_class,
        "confidence": round(confidence, 3),
    }
