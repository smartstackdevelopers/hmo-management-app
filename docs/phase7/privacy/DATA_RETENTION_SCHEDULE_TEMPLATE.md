# Data retention schedule (template)

Organisations must complete this schedule with **authorised legal review**. HMore does not pre-fill statutory retention periods.

| Category code | Category | Retention period | Review date | Legal basis / hold exceptions | Deletion method |
|---------------|----------|------------------|-------------|------------------------------|-----------------|
| tenant_profiles | | _To be confirmed_ | | | |
| housing_applications | | | | | |
| incident_safeguarding | | | | Safeguarding may require extended retention | |
| documents_media | | | | | Secure delete from private storage |
| ai_processing | | | | | Activity log policy TBC |
| room_occupancy_counts | | | | Occupancy gate retention policy | Celery sweep when configured |

**Software:** mirror active rows in Dashboard → Privacy → Retention (`PUT /api/v1/privacy/retention`).
