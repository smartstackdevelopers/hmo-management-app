# Biometric unlock and remote sign-out (F4.6)

Auth0 remains the identity provider. Fingerprint or face unlock does not log a person in. It only uncovers an Auth0 session that is already stored in SecureStore on that phone. The operating system keeps the biometric check. HMore never receives a fingerprint, a face image, or a biometric template, and the API has no column for them.

## Device sessions

Migration `20261110_3300_f46` revises `20261110_3200_f45` and adds `mobile_device_sessions`. Each row is one installation for one user inside one organisation. The client generates `installation_id`. The unique key is `(user_id, installation_id)`.

Statuses are `active`, `revoked`, and `lost`. Organisation row-level security matches the other tenant tables. Audit events are `device_session.registered`, `device_session.revoked`, and `device_session.reported_lost`. The metadata is installation id, platform, status, and an optional reason. It does not include biometric data or tokens.

`POST /api/v1/device-sessions` creates an active row or refreshes one that is already active. If that installation is `revoked` or `lost`, the API returns 403 `session_revoked` and leaves the row unchanged. The phone has to sign in with Auth0 again and send a new `installation_id`. The old installation is not turned back on.

The signed-in user can list and revoke their own rows. An organisation admin or super admin can revoke or report lost any session in the organisation they are acting in. A session in another organisation returns 403. Reporting lost sets `status=lost` and fills the same revocation columns.

## Request header

After registration, the mobile client sends `X-Device-Session-Id` on API calls. The value is the session row id, kept in SecureStore. It is not an access token.

If the header is present and the row is missing, belongs to someone else, or is `revoked` or `lost`, the API returns 401 `device_session_revoked` and does not update `last_seen_at`. An active row updates `last_seen_at`. If the header is absent, the request continues. Web clients do not send it. A modified mobile build that omits the header is not blocked by this check.

`GET /api/v1/device-sessions/current` is the exception. It returns the row, including `revoked` and `lost`, so the phone can read the status. An unknown id still returns 401 `device_session_revoked`.

## Phone

`expo-local-authentication` is the OS prompt. The on/off preference is a SecureStore flag (`hmore.biometric.unlock`). Turning it on requires `authenticateAsync` to return success. The app lock opens only after that success. The stored flag alone does not unlock.

Leaving the app covers the screen. Coming back asks for fingerprint or face when the preference is on and a session is present. The other button signs out and starts Auth0 login again. The OS device passcode is not accepted as a substitute (`disableDeviceFallback`).

On sign-out, the app revokes the current device session, calls Auth0 `/oauth/revoke` with the refresh token when one is stored, opens Auth0 logout, and clears SecureStore tokens and the device-session ids. A 401 `device_session_revoked` from any API call does the same local cleanup without waiting for the user to open settings. Push deep links do not open a confidential screen while the lock is up or the device is revoked.

Offline drafts are not deleted. They stay encrypted and bound to the user and organisation from F4.5. Sync Now does not run while the stored status is `revoked` or `lost`. The next sign-in of that same user can still see those drafts. A different account cannot.

## Auth0 refresh tokens

The current phone can revoke the refresh token it holds, because that token is on the device. This MVP does not call the Auth0 Management API. `AUTH0_MGMT_DOMAIN`, `AUTH0_MGMT_CLIENT_ID`, and `AUTH0_MGMT_CLIENT_SECRET` may be set, and the API records that they are present, but it does not request a management token and it does not revoke refresh tokens for other devices. Those refresh tokens stay valid at Auth0 until they expire, or until a later change uses the Management API. The HMore API still rejects those devices when they send their device-session id.

## What is not proven here

CI does not show a biometric prompt and does not use a physical iPhone or Android phone. Face ID in particular needs a development build; Expo Go does not verify it. A device that is offline keeps its local tokens until it next reaches the API or the sync status check. Drafts already on the phone remain readable to the person who holds the unlocked device. The header check is not a proof that the caller is the genuine mobile app.
