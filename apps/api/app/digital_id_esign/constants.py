"""F8.6 digital ID and e-signatures constants."""

from __future__ import annotations

IDENTITY_DOCUMENT_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("passport", "Passport"),
    ("driving_licence", "Driving Licence"),
    ("national_id", "National Identity Document"),
    ("other", "Other approved identity evidence"),
)

DEFAULT_ESIGN_TEMPLATES: tuple[tuple[str, str], ...] = (
    ("tenancy_agreement", "Tenancy agreement"),
    ("property_inspection", "Property inspection form"),
    ("contractor_agreement", "Contractor agreement"),
    ("maintenance_completion", "Maintenance completion form"),
    ("staff_acknowledgement", "Staff acknowledgement form"),
    ("consent_form", "Approved consent form"),
    ("organisational_agreement", "Organisational agreement"),
)

SIGNATURE_METHODS = frozenset({"drawn", "typed", "click_to_sign", "provider_advanced"})

ADVANCED_CONSENT_PHRASE = (
    "I confirm I intend to sign this document. This record is not a qualified advanced electronic "
    "signature unless an approved trust service provider and legal review are active."
)

ADDON_DISCLAIMER = (
    "Digital ID and e-signatures extend HMore managed documents. Basic in-platform signatures remain "
    "distinct from provider-verified or legally assessed advanced electronic signatures."
)
