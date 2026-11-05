# MFA configuration (Auth0)

HMore does not implement a custom MFA challenge UI. MFA is Auth0-managed.

## Requirement

Proposal and Phase 1 exit criteria require MFA on staff and admin authentication paths:

- Super Admin
- Organisation Admin
- Landlord (web primary)
- Support Worker
- Maintenance & Contractors

Tenant self-service mobile login may use a separate Auth0 application or connection policy. Do not weaken staff MFA to accommodate tenants.

## Dashboard steps

1. Security → Multifactor Auth.
2. Enable at least one strong factor (Authenticator app / OTP recommended).
3. Avoid SMS-only MFA for staff when a stronger factor is available.
4. Configure recovery codes according to Auth0 guidance and store recovery procedures offline with the operations team. Do not put recovery secrets in git.

## Enforce MFA for the staff web application

Preferred approach: Post-Login Action that requires MFA for the Regular Web Application client id.

Example Action (paste into Auth0 Actions → Post Login; set secret `STAFF_WEB_CLIENT_ID`):

```javascript
exports.onExecutePostLogin = async (event, api) => {
  if (event.client.client_id === event.secrets.STAFF_WEB_CLIENT_ID) {
    api.multifactor.enable("any", { allowRememberBrowser: false });
  }
};
```

Alternative: tenant-wide “Always require Multi-factor Authentication” when every Auth0 application in the tenant is staff-only.

## API defence in depth

FastAPI setting `AUTH0_REQUIRE_MFA_CLAIM=true` rejects access tokens that do not show MFA in the `amr` claim for staff-oriented routes that depend on `require_mfa`.

Enable this only after confirming Auth0 includes `amr: ["mfa"]` (or equivalent) on access tokens for your tenant plan and Action configuration.

## Failure handling

- Failed MFA challenges remain in Auth0 Universal Login; HMore must not offer a bypass.
- Lockout and retry behaviour follow Auth0 tenant settings.
- Support staff must not ask users for passwords or OTP codes over insecure channels.

## Verification status

MFA is **not verified** in this repository until a real Auth0 UK/EU tenant has MFA enabled, the Post-Login Action (or always-on policy) is active, and a staff user completes an MFA challenge during web login. Mocked unit tests do not satisfy that criterion.
