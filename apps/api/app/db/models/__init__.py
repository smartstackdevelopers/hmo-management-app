"""Import all models so Alembic and metadata see every table."""

from app.db.models.audit import AuditEvent
from app.db.models.emergency_access import EmergencyAccess
from app.db.models.enums import HMoreRole, MembershipStatus, RecordStatus
from app.db.models.file_metadata import FileMetadata
from app.db.models.membership import OrganisationMembership
from app.db.models.occupancy_survey import (
    OccupancySiteSurvey,
    OccupancySurveyFinding,
    OccupancySurveyRoomAssessment,
)
from app.db.models.organisation import Organisation
from app.db.models.property import Property
from app.db.models.room import Room
from app.db.models.scheduling import (
    OperationalTask,
    ReminderRecord,
    StaffShift,
    TenantVisit,
)
from app.db.models.support_ops import CaseAssignment, DailyLog, Handover
from app.db.models.tenant import Tenant
from app.db.models.user import User

__all__ = [
    "AuditEvent",
    "CaseAssignment",
    "DailyLog",
    "EmergencyAccess",
    "FileMetadata",
    "Handover",
    "HMoreRole",
    "MembershipStatus",
    "OccupancySiteSurvey",
    "OccupancySurveyFinding",
    "OccupancySurveyRoomAssessment",
    "OperationalTask",
    "Organisation",
    "OrganisationMembership",
    "Property",
    "RecordStatus",
    "ReminderRecord",
    "Room",
    "StaffShift",
    "Tenant",
    "TenantVisit",
    "User",
]
