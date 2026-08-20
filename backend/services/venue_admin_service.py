from typing import Optional
from sqlalchemy.orm import Session

from backend.models.models import Venue
from backend.services.venue_service import venue_service


class VenueAdminService:
    def create_venue(self, db: Session, name: str, address: str, max_capacity: Optional[int]) -> Venue:
        venue = Venue(name=name, address=address, max_capacity=max_capacity)
        db.add(venue)
        db.commit()
        db.refresh(venue)
        # Seed default config/policy rows eagerly rather than relying on
        # venue_service's lazy auto-create on first GET.
        venue_service.get_venue_configuration(db, venue.id)
        venue_service.get_venue_policy(db, venue.id)
        return venue

    def list_venues(self, db: Session, include_inactive: bool = False) -> list[Venue]:
        query = db.query(Venue)
        if not include_inactive:
            query = query.filter(Venue.is_active.is_(True))
        return query.order_by(Venue.id).all()

    def get_venue(self, db: Session, venue_id: int) -> Optional[Venue]:
        return db.query(Venue).filter(Venue.id == venue_id).first()

    def update_venue(self, db: Session, venue_id: int, updates: dict) -> Optional[Venue]:
        venue = self.get_venue(db, venue_id)
        if not venue:
            return None
        for key, value in updates.items():
            if value is not None and hasattr(venue, key):
                setattr(venue, key, value)
        db.commit()
        db.refresh(venue)
        return venue

    def deactivate_venue(self, db: Session, venue_id: int) -> Optional[Venue]:
        # Deactivate, never hard-delete — Venue is FK'd from User,
        # VerificationSession, Incident, Notification, VenueConfiguration,
        # PolicySchema, and Occupancy.
        venue = self.get_venue(db, venue_id)
        if not venue:
            return None
        venue.is_active = False
        db.commit()
        db.refresh(venue)
        return venue


venue_admin_service = VenueAdminService()
