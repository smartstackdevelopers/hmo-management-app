# Tenant — training guide

**Who:** `tenant` role — self-service.  
**Web:** `/account` (limited). **Primary:** HMore mobile app.

## Login & profile

1. Install HMore from organisation link (when store build available).
2. Sign in with Auth0.
3. **Profile** / settings: preferred name, phone, language, accessibility (`/(app)/accessibility`).

## Housing & repairs

- **Tenancy** tab: housing information from API.
- **Maintenance → New request:** title, description, property context, **photos** (camera permission).
- Track status under **Maintenance** — not emergency priority unless staff escalate.

## Support & wellbeing

- **Support** tab, support plans (read-only where configured).
- **Wellbeing** / community modules if organisation enabled (Phase 5).

## Community & employment

- **Help near me**, **Community hub**, **Employment**, **Job matching** — only if enabled for your org.

## Documents & assistant

- **Documents:** upload/download via secure API — stay on organisation Wi‑Fi or mobile data with HTTPS.
- **Assistant:** AI answers are guidance — not housing decisions.

## Notifications

- Allow notifications for reminders; content stays generic on lock screen (no case notes).

## Security

- Enable biometric unlock optional — session still tied to Auth0.
- **Security** screen: password change (where legacy path), device sessions, lost device report.

## FAQs

**Q: Application rejected?**  
A: AI does not reject applications — staff/org admin decide.

## Screenshots

`docs/training/assets/screenshots/tenant-mobile/` — home, maintenance new, documents.
