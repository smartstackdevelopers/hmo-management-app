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
from app.db.models.compliance import SafeguardingReminder, StaffTrainingRecord
from app.db.models.complaints import (
    Complaint,
    ComplaintCategory,
    ComplaintDeadlineChange,
    ComplaintDeadlineRule,
    ComplaintEscalation,
    ComplaintFile,
    ComplaintHistoryEvent,
    ComplaintNote,
    ComplaintStatusHistory,
)
from app.db.models.evidence import (
    EvidenceChecklistItem,
    EvidenceChecklistTemplate,
    EvidenceItemFile,
    EvidencePack,
    EvidenceReviewHistory,
)
from app.db.models.housing import (
    HousingApplication,
    HousingApplicationDecision,
    HousingApplicationStatusHistory,
    WaitingListEntry,
)
from app.db.models.maintenance import (
    MaintenanceApproval,
    MaintenanceCategory,
    MaintenanceEmergencyContent,
    MaintenanceHistoryEvent,
    MaintenanceNote,
    MaintenancePriorityChange,
    MaintenanceRequest,
    MaintenanceRequestFile,
    MaintenanceStatusHistory,
    MaintenanceVisit,
)
from app.db.models.incidents import Incident, IncidentFollowUp, IncidentStatusHistory
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
    "Complaint",
    "ComplaintCategory",
    "ComplaintDeadlineChange",
    "ComplaintDeadlineRule",
    "ComplaintEscalation",
    "ComplaintFile",
    "ComplaintHistoryEvent",
    "ComplaintNote",
    "ComplaintStatusHistory",
    "DailyLog",
    "EmergencyAccess",
    "EvidenceChecklistItem",
    "EvidenceChecklistTemplate",
    "EvidenceItemFile",
    "EvidencePack",
    "EvidenceReviewHistory",
    "FileMetadata",
    "Handover",
    "HMoreRole",
    "MaintenanceApproval",
    "MaintenanceCategory",
    "MaintenanceEmergencyContent",
    "MaintenanceHistoryEvent",
    "MaintenanceNote",
    "MaintenancePriorityChange",
    "MaintenanceRequest",
    "MaintenanceRequestFile",
    "MaintenanceStatusHistory",
    "MaintenanceVisit",
    "HousingApplication",
    "HousingApplicationDecision",
    "HousingApplicationStatusHistory",
    "Incident",
    "IncidentFollowUp",
    "IncidentStatusHistory",
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
    "SafeguardingReminder",
    "StaffShift",
    "StaffTrainingRecord",
    "Tenant",
    "TenantVisit",
    "User",
    "WaitingListEntry",
]
