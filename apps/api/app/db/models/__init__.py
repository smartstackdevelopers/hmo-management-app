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
from app.db.models.managed_documents import (
    ManagedDocument,
    ManagedDocumentAccessGrant,
    ManagedDocumentAccessRequest,
    ManagedDocumentCategory,
    ManagedDocumentLink,
    ManagedDocumentReminderLog,
    ManagedDocumentRetentionReview,
    ManagedDocumentSignatureRequest,
    ManagedDocumentVersion,
    OrganisationDocumentSettings,
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
from app.db.models.support_plans import (
    SupportPlanContributor,
    SupportPlanGoal,
    SupportPlanGoalChange,
    SupportPlanGoalProgressNote,
    SupportPlanHistoryEvent,
    SupportPlanMilestone,
    SupportPlanMilestoneChange,
    SupportPlanProgressExport,
    SupportPlanReview,
    TenantSupportPlan,
)
from app.db.models.support_ops import CaseAssignment, DailyLog, Handover
from app.db.models.tenant import Tenant
from app.db.models.tenant_timeline import (
    TenantAppointment,
    TenantFollowUp,
    TenantFollowUpChange,
    TenantMeeting,
    TenantMeetingParticipant,
    TenantNeedGoal,
)
from app.db.models.user import User
from app.db.models.org_workflows import (
    OrganisationApprovalAssignment,
    OrganisationApprovalWorkflow,
    OrganisationApprovalWorkflowVersion,
    OrganisationCustomForm,
    OrganisationCustomFormSubmission,
    OrganisationCustomFormVersion,
    SecureSharingAccessLog,
    SecureSharingGrant,
)
from app.db.models.communication import (
    CommunicationAnnouncement,
    CommunicationAnnouncementRecipient,
    CommunicationDelivery,
    CommunicationMessage,
    CommunicationMessageRecipient,
    CommunicationScheduledReminder,
    CommunicationTemplate,
    CommunicationTranslation,
    CommunicationUserPreference,
)
from app.db.models.ai_usage import (
    AiBudgetReservation,
    AiModelPricing,
    AiUsageRecord,
    OrganisationAiBudget,
)
from app.db.models.notes_analysis import DailyLogAiAnalysis, DailyLogAiSuggestion
from app.db.models.case_summaries import CaseSummary
from app.db.models.document_checks import (
    DocumentCheck,
    DocumentCheckFinding,
    DocumentCheckObservation,
    DocumentCheckRule,
)
from app.db.models.support_plan_drafts import SupportPlanDraft
from app.db.models.housing_application_analysis import (
    HousingApplicationAnalysis,
    HousingApplicationAnalysisFinding,
)
from app.db.models.compliance_agent import ComplianceFinding, ComplianceSweep
from app.db.models.tenant_assistant import (
    TenantAssistantConversation,
    TenantAssistantMessage,
    TenantAssistantRateWindow,
)
from app.db.models.duplicate_detection import DuplicateDetectionFinding, DuplicateDetectionRun
from app.db.models.report_drafts import OperationalReportDraft
from app.db.models.ai_activity import (
    AiActivityLog,
    AiFeedbackReviewEvent,
    AiWrongAnswerFeedback,
)
from app.db.models.ai_feature_flags import (
    OrganisationAiFeatureFlag,
    OrganisationAiFeatureFlagHistory,
)
from app.db.models.catalogue import (
    CommunityService,
    CommunityServiceVerificationEvent,
    OpportunityListing,
)
from app.db.models.help_near_me import (
    CommunityServiceOutdatedReport,
    HelpNearMeSearchEvent,
)
from app.db.models.employment import (
    TenantCareerGoal,
    TenantCv,
    TenantInterviewNote,
    TenantJobApplication,
    TenantJobApplicationEvent,
    TenantSkillAssessment,
)
from app.db.models.job_matching import (
    JobListing,
    TenantJobMatch,
    TenantJobMatchPreferences,
    TenantSavedJob,
    TenantSavedTraining,
    TrainingOpportunity,
)
from app.db.models.wellbeing import (
    WellbeingCheckin,
    WellbeingDirectoryEntry,
    WellbeingResource,
    WellbeingResourceCompletion,
    WellbeingRoutine,
    WellbeingRoutineCompletion,
    WellbeingSavedResource,
)
from app.db.models.landlord_enterprise import PropertyInspection, RentRecord
from app.db.models.reporting_analytics import (
    EarlyWarningAlert,
    EarlyWarningThreshold,
    ReportExport,
    ScheduledReport,
    ScheduledReportRun,
)
from app.db.models.automation import (
    AutomationComplianceIssue,
    AutomationEscalation,
    AutomationRule,
    AutomationRuleRun,
)
from app.db.models.push_devices import PushDeviceToken
from app.db.models.idempotency import ClientIdempotencyKey
from app.db.models.device_sessions import MobileDeviceSession

__all__ = [
    "AuditEvent",
    "CaseAssignment",
    "ClientIdempotencyKey",
    "CommunityService",
    "CommunityServiceOutdatedReport",
    "CommunityServiceVerificationEvent",
    "Complaint",
    "HelpNearMeSearchEvent",
    "TenantCareerGoal",
    "TenantCv",
    "TenantInterviewNote",
    "TenantJobApplication",
    "TenantJobApplicationEvent",
    "TenantSkillAssessment",
    "JobListing",
    "TenantJobMatch",
    "TenantJobMatchPreferences",
    "TenantSavedJob",
    "TenantSavedTraining",
    "TrainingOpportunity",
    "WellbeingCheckin",
    "WellbeingDirectoryEntry",
    "WellbeingResource",
    "WellbeingResourceCompletion",
    "WellbeingRoutine",
    "WellbeingRoutineCompletion",
    "WellbeingSavedResource",
    "PropertyInspection",
    "RentRecord",
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
    "ManagedDocument",
    "ManagedDocumentAccessGrant",
    "ManagedDocumentAccessRequest",
    "ManagedDocumentCategory",
    "ManagedDocumentLink",
    "ManagedDocumentReminderLog",
    "ManagedDocumentRetentionReview",
    "ManagedDocumentSignatureRequest",
    "ManagedDocumentVersion",
    "HousingApplication",
    "HousingApplicationDecision",
    "HousingApplicationStatusHistory",
    "Incident",
    "IncidentFollowUp",
    "IncidentStatusHistory",
    "MembershipStatus",
    "MobileDeviceSession",
    "OccupancySiteSurvey",
    "OpportunityListing",
    "OccupancySurveyFinding",
    "OccupancySurveyRoomAssessment",
    "OperationalTask",
    "OrganisationDocumentSettings",
    "Organisation",
    "OrganisationMembership",
    "Property",
    "PushDeviceToken",
    "RecordStatus",
    "ReminderRecord",
    "Room",
    "SafeguardingReminder",
    "StaffShift",
    "StaffTrainingRecord",
    "SupportPlanContributor",
    "SupportPlanGoal",
    "SupportPlanGoalChange",
    "SupportPlanGoalProgressNote",
    "SupportPlanHistoryEvent",
    "SupportPlanMilestone",
    "SupportPlanMilestoneChange",
    "SupportPlanProgressExport",
    "SupportPlanReview",
    "Tenant",
    "TenantSupportPlan",
    "TenantAppointment",
    "TenantFollowUp",
    "TenantFollowUpChange",
    "TenantMeeting",
    "TenantMeetingParticipant",
    "TenantNeedGoal",
    "TenantVisit",
    "User",
    "WaitingListEntry",
    "CommunicationAnnouncement",
    "CommunicationAnnouncementRecipient",
    "CommunicationDelivery",
    "CommunicationMessage",
    "CommunicationMessageRecipient",
    "CommunicationScheduledReminder",
    "CommunicationTemplate",
    "CommunicationTranslation",
    "CommunicationUserPreference",
    "OrganisationApprovalAssignment",
    "OrganisationApprovalWorkflow",
    "OrganisationApprovalWorkflowVersion",
    "OrganisationCustomForm",
    "OrganisationCustomFormSubmission",
    "OrganisationCustomFormVersion",
    "SecureSharingAccessLog",
    "SecureSharingGrant",
    "OrganisationAiBudget",
    "AiModelPricing",
    "AiUsageRecord",
    "AiBudgetReservation",
    "DailyLogAiAnalysis",
    "DailyLogAiSuggestion",
    "CaseSummary",
    "DocumentCheck",
    "DocumentCheckFinding",
    "DocumentCheckObservation",
    "DocumentCheckRule",
    "SupportPlanDraft",
    "HousingApplicationAnalysis",
    "HousingApplicationAnalysisFinding",
    "ComplianceSweep",
    "ComplianceFinding",
    "TenantAssistantConversation",
    "TenantAssistantMessage",
    "TenantAssistantRateWindow",
    "DuplicateDetectionRun",
    "DuplicateDetectionFinding",
    "OperationalReportDraft",
    "AiActivityLog",
    "AiWrongAnswerFeedback",
    "AiFeedbackReviewEvent",
    "OrganisationAiFeatureFlag",
    "OrganisationAiFeatureFlagHistory",
    "ReportExport",
    "ScheduledReport",
    "ScheduledReportRun",
    "EarlyWarningThreshold",
    "EarlyWarningAlert",
    "AutomationRule",
    "AutomationRuleRun",
    "AutomationEscalation",
    "AutomationComplianceIssue",
]
