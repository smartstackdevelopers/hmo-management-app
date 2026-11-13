from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.emergency_access import router as emergency_access_router
from app.api.v1.files import router as files_router
from app.api.v1.health import router as health_router
from app.api.v1.isolation_probes import router as isolation_router
from app.api.v1.occupancy_surveys import router as occupancy_surveys_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.complaints import router as complaints_router
from app.api.v1.maintenance import router as maintenance_router
from app.api.v1.managed_documents import router as managed_documents_router
from app.api.v1.communication import router as communication_router
from app.api.v1.push import router as push_router
from app.api.v1.device_sessions import router as device_sessions_router
from app.api.v1.org_workflows import router as org_workflows_router
from app.api.v1.reporting import router as reporting_router
from app.api.v1.automation import router as automation_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.room_occupancy import router as room_occupancy_router
from app.api.v1.finance import router as finance_router
from app.api.v1.council_portal import router as council_portal_router
from app.api.v1.privacy import router as privacy_router
from app.api.v1.backups import router as backups_router
from app.api.v1.performance import router as performance_router
from app.api.v1.ai_usage import internal_router as ai_usage_internal_router
from app.api.v1.ai_usage import router as ai_usage_router
from app.api.v1.notes_analysis import router as notes_analysis_router
from app.api.v1.case_summaries import router as case_summaries_router
from app.api.v1.document_checks import router as document_checks_router
from app.api.v1.support_plan_drafts import router as support_plan_drafts_router
from app.api.v1.housing_application_analysis import router as housing_application_analysis_router
from app.api.v1.compliance_agent import router as compliance_agent_router
from app.api.v1.tenant_assistant import router as tenant_assistant_router
from app.api.v1.duplicate_detection import router as duplicate_detection_router
from app.api.v1.operational_search import router as operational_search_router
from app.api.v1.report_drafts import router as report_drafts_router
from app.api.v1.ai_activity import router as ai_activity_router
from app.api.v1.ai_feature_flags import router as ai_feature_flags_router
from app.api.v1.evidence import router as evidence_router
from app.api.v1.housing import router as housing_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.ops import router as ops_router
from app.api.v1.organisations import router as organisations_router
from app.api.v1.properties import router as properties_router
from app.api.v1.rbac import router as rbac_router
from app.api.v1.rooms import router as rooms_router
from app.api.v1.support import router as support_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.tenant_me import router as tenant_me_router
from app.api.v1.community_services import router as community_services_router
from app.api.v1.help_near_me import router as help_near_me_router
from app.api.v1.employment import router as employment_router
from app.api.v1.job_matching import router as job_matching_router
from app.api.v1.wellbeing import router as wellbeing_router
from app.api.v1.landlord_enterprise import router as landlord_enterprise_router
from app.api.v1.voice_calling import router as voice_calling_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.tenant_timeline import router as tenant_timeline_router
from app.api.v1.support_plans import dash_router as support_plans_dash_router
from app.api.v1.support_plans import router as support_plans_router
from app.api.v1.support_plans import tenant_self_router as support_plans_tenant_self_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(rbac_router)
api_v1_router.include_router(organisations_router)
api_v1_router.include_router(isolation_router)
api_v1_router.include_router(tenants_router)
api_v1_router.include_router(tenant_me_router)
api_v1_router.include_router(community_services_router)
api_v1_router.include_router(help_near_me_router)
api_v1_router.include_router(employment_router)
api_v1_router.include_router(job_matching_router)
api_v1_router.include_router(wellbeing_router)
api_v1_router.include_router(landlord_enterprise_router)
api_v1_router.include_router(opportunities_router)
api_v1_router.include_router(tenant_timeline_router)
api_v1_router.include_router(support_plans_router)
api_v1_router.include_router(support_plans_dash_router)
api_v1_router.include_router(support_plans_tenant_self_router)
api_v1_router.include_router(properties_router)
api_v1_router.include_router(rooms_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(emergency_access_router)
api_v1_router.include_router(files_router)
api_v1_router.include_router(occupancy_surveys_router)
api_v1_router.include_router(support_router)
api_v1_router.include_router(ops_router)
api_v1_router.include_router(compliance_router)
api_v1_router.include_router(incidents_router)
api_v1_router.include_router(housing_router)
api_v1_router.include_router(evidence_router)
api_v1_router.include_router(complaints_router)
api_v1_router.include_router(maintenance_router)
api_v1_router.include_router(managed_documents_router)
api_v1_router.include_router(communication_router)
api_v1_router.include_router(push_router)
api_v1_router.include_router(device_sessions_router)
api_v1_router.include_router(org_workflows_router)
api_v1_router.include_router(reporting_router)
api_v1_router.include_router(automation_router)
api_v1_router.include_router(integrations_router)
api_v1_router.include_router(room_occupancy_router)
api_v1_router.include_router(finance_router)
api_v1_router.include_router(council_portal_router)
api_v1_router.include_router(privacy_router)
api_v1_router.include_router(backups_router)
api_v1_router.include_router(performance_router)
api_v1_router.include_router(ai_usage_router)
api_v1_router.include_router(ai_usage_internal_router)
api_v1_router.include_router(notes_analysis_router)
api_v1_router.include_router(case_summaries_router)
api_v1_router.include_router(document_checks_router)
api_v1_router.include_router(support_plan_drafts_router)
api_v1_router.include_router(housing_application_analysis_router)
api_v1_router.include_router(compliance_agent_router)
api_v1_router.include_router(tenant_assistant_router)
api_v1_router.include_router(duplicate_detection_router)
api_v1_router.include_router(operational_search_router)
api_v1_router.include_router(report_drafts_router)
api_v1_router.include_router(ai_activity_router)
api_v1_router.include_router(ai_feature_flags_router)
api_v1_router.include_router(voice_calling_router)
