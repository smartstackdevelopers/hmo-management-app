# F8.6 Digital ID & E-Signatures Architecture

Complements F2.11 `managed_documents` and existing `documents.sign.*` permissions — does not replace core auth or storage.

- `digital_identity_records` — verification lifecycle (manual or sandbox provider)
- `digital_identity_documents` — private `file_metadata` links
- `esign_signing_requests` — multi-signer workflows (sequential/parallel) with SHA-256 integrity
- `esign_signature_events` — consent and method audit trail
- Providers default to `sandbox`; paid integrations require env approval

API prefix: `/api/v1/digital-id-esign`

Gate: `DIGITAL_ID_ESIGN_GLOBAL_ENABLED=false`
