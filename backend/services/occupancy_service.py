from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from backend.models.models import Occupancy, OccupancyStatusEnum, Customer


class OccupancyService:
    def get_current_occupants(self, db: Session, venue_id: int) -> list[Occupancy]:
        return (
            db.query(Occupancy)
            .filter(Occupancy.venue_id == venue_id, Occupancy.exited_at.is_(None))
            .order_by(Occupancy.entered_at.desc())
            .all()
        )

    def get_live_count(self, db: Session, venue_id: int) -> int:
        return (
            db.query(Occupancy)
            .filter(Occupancy.venue_id == venue_id, Occupancy.exited_at.is_(None))
            .count()
        )

    def check_out(self, db: Session, occupancy_id: int, checked_out_by_id: int, venue_id: int) -> Optional[Occupancy]:
        # venue_id scoping matches check_out_by_customer below — without
        # it, any door_staff+ operator could force-checkout another
        # venue's occupant by guessing/incrementing occupancy_id, since
        # occupancy IDs are plain sequential integers with no per-venue
        # namespace.
        record = db.query(Occupancy).filter(
            Occupancy.id == occupancy_id, Occupancy.venue_id == venue_id
        ).first()
        if not record:
            return None
        if record.exited_at is not None:
            raise ValueError("This occupancy record is already checked out.")
        record.exited_at = datetime.now(timezone.utc)
        record.status = OccupancyStatusEnum.CHECKED_OUT
        record.checked_out_by_id = checked_out_by_id
        db.commit()
        db.refresh(record)
        return record

    def check_out_by_customer(self, db: Session, venue_id: int, customer_id: int, checked_out_by_id: int) -> Optional[Occupancy]:
        record = (
            db.query(Occupancy)
            .filter(Occupancy.venue_id == venue_id, Occupancy.customer_id == customer_id, Occupancy.exited_at.is_(None))
            .first()
        )
        if not record:
            return None
        return self.check_out(db, record.id, checked_out_by_id)


occupancy_service = OccupancyService()
