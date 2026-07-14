from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all the models, so that Base has them before being
# imported by Alembic
from backend.models.models import *
from backend.models.analytics_models import *
