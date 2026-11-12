"""Imports every model so Base.metadata knows about all tables.
The model classes themselves live in app/models/."""
from app.models import Briefing, Claim, Meeting, Source  # noqa: F401
