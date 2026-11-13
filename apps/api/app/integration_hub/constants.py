"""F8.9 integration hub extended catalog."""

from __future__ import annotations

HUB_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("accounting", "Accounting Software"),
    ("payments", "Payment Providers"),
    ("email", "Email Services"),
    ("sms", "SMS Services"),
    ("cloud_storage", "Cloud Storage"),
    ("identity_verification", "Identity Verification"),
    ("esignatures", "Electronic Signatures"),
    ("government_info", "Government Information Services"),
    ("property_management", "Property Management"),
    ("lms", "Learning Management"),
    ("crm", "CRM Platforms"),
    ("reporting", "Reporting and Analytics"),
    ("calendar", "Calendar Services"),
    ("ai_services", "AI Services"),
    ("community_services", "Community Services"),
)

HMORE_MODULE_KEYS: tuple[str, ...] = (
    "tenants",
    "properties",
    "landlord_enterprise",
    "maintenance",
    "contractor_marketplace",
    "rent_payments",
    "lms",
    "digital_id_esign",
    "benefits_navigator",
    "tenant_engagement",
    "ai_gateway",
    "notifications",
)

FOUNDATION_PROVIDERS: tuple[tuple[str, str, str], ...] = (
    ("accounting_sandbox", "accounting", "Accounting connector (sandbox)"),
    ("stripe_sandbox", "payments", "Payment provider (sandbox)"),
    ("sendgrid_sandbox", "email", "Email provider (sandbox)"),
    ("twilio_sandbox", "sms", "SMS provider (sandbox)"),
    ("s3_compatible", "cloud_storage", "Cloud storage (sandbox)"),
    ("idv_sandbox", "identity_verification", "Identity verification (sandbox)"),
    ("esign_sandbox", "esignatures", "E-signature provider (sandbox)"),
    ("govuk_info", "government_info", "Government information (read-only sandbox)"),
    ("property_pms_sandbox", "property_management", "Property management (sandbox)"),
    ("lms_bridge", "lms", "LMS bridge"),
    ("crm_sandbox", "crm", "CRM (sandbox)"),
    ("reporting_sandbox", "reporting", "Reporting export (sandbox)"),
    ("calendar_sandbox", "calendar", "Calendar (sandbox)"),
    ("ai_gateway", "ai_services", "AI Gateway"),
    ("community_service_generic", "community_services", "Community services"),
)

ADDON_DISCLAIMER = (
    "Connections are active only after successful tests. Production financial or government links require explicit approval."
)
