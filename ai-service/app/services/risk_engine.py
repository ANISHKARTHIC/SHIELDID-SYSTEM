def calculate_risk(
    ocr_confidence: float,
    quality_score: float,
    authenticity_score: float,
    is_over_18: bool,
    venue_status: dict
) -> dict:
    """
    Generate a weighted recommendation based on AI and venue data.
    """
    risk_score = 0
    recommendation = "PASS"
    
    # 1. Base AI scores
    if ocr_confidence < 90:
        risk_score += 20
    if quality_score < 80:
        risk_score += 15
    if authenticity_score < 70:
        risk_score += 30
    elif authenticity_score < 85:
        risk_score += 10
        
    # 2. Age Check
    if not is_over_18:
        risk_score += 100 # Immediate red flag
        
    # 3. Venue Status
    if venue_status.get("blacklisted"):
        risk_score += 100
        
    incidents = venue_status.get("incidents", 0)
    if incidents > 0:
        risk_score += (incidents * 20)
        
    # Determine Recommendation
    if risk_score >= 80:
        recommendation = "DENY"
    elif risk_score >= 30:
        recommendation = "CHECK"
    else:
        recommendation = "PASS"
        
    return {
        "risk_score": risk_score,
        "recommendation": recommendation
    }
