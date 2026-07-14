from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional
import io
import csv

from backend.api.deps import get_db
from backend.models.models import VerificationSession

router = APIRouter(prefix="/api/v1/export", tags=["export"])

@router.get("/csv/fraud")
async def export_fraud_csv(
    days: int = 30,
    venue_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Exports a CSV of fraud reviews over the last N days."""
    start_date = date.today() - timedelta(days=days)
    
    query = db.query(VerificationSession).filter(
        VerificationSession.created_at >= start_date,
        VerificationSession.state == "FRAUD_REVIEW"
    )
    
    if venue_id:
        query = query.filter(VerificationSession.venue_id == venue_id)
        
    sessions = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Session ID", "Venue ID", "Operator ID", "Created At", "Risk Score", "Final Decision"])
    
    for s in sessions:
        writer.writerow([
            s.id, s.venue_id, s.operator_id, s.created_at.isoformat(), s.risk_score, s.final_decision
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=fraud_report.csv"}
    )
