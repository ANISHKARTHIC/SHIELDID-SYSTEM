from sqlalchemy.orm import Session
from backend.models.models import Venue, VenueConfiguration, PolicySchema
import json

class VenueService:
    def get_venue_configuration(self, db: Session, venue_id: int) -> VenueConfiguration:
        config = db.query(VenueConfiguration).filter(VenueConfiguration.venue_id == venue_id).first()
        if not config:
            # Create default config if missing
            config = VenueConfiguration(venue_id=venue_id)
            db.add(config)
            db.commit()
            db.refresh(config)
        return config

    def get_venue_policy(self, db: Session, venue_id: int) -> PolicySchema:
        policy = db.query(PolicySchema).filter(PolicySchema.venue_id == venue_id).first()
        if not policy:
            # Create default policy if missing
            policy = PolicySchema(venue_id=venue_id)
            db.add(policy)
            db.commit()
            db.refresh(policy)
        return policy

    def update_configuration(self, db: Session, venue_id: int, updates: dict) -> VenueConfiguration:
        config = self.get_venue_configuration(db, venue_id)
        for key, value in updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        db.commit()
        db.refresh(config)
        return config

    def update_policy(self, db: Session, venue_id: int, updates: dict) -> PolicySchema:
        policy = self.get_venue_policy(db, venue_id)
        for key, value in updates.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        db.commit()
        db.refresh(policy)
        return policy

venue_service = VenueService()
