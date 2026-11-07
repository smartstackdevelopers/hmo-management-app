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
from app.api.v1.org_workflows import router as org_workflows_router
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
api_v1_router.include_router(org_workflows_router)
