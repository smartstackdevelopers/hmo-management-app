# Biometric unlock and remote sign-out setup (F4.6)

From the monorepo root:

```bash
npm install
npm run typecheck -w room-ready
npm test -w room-ready
```

API unit tests, from `apps/api`:

```bash
python -m pytest tests/test_f46_device_sessions.py tests/test_f41_tenant_mobile.py::test_alembic_head_revises_f41_tenant_mobile
```

Apply migration `20261110_3300_f46` with the API's usual Alembic upgrade. It revises `20261110_3200_f45` and adds `mobile_device_sessions`. No biometric data is stored. Tokens stay out of AsyncStorage.

`room-ready` depends on `expo-local-authentication` `~57.0.3`. Fingerprint and face prompts need a development build (`npm run start:dev -w room-ready`, then `npm run ios -w room-ready` or `npm run android -w room-ready`). Expo Go does not verify Face ID. Jest mocks `expo-local-authentication`. CI does not run a device prompt and does not prove that a phone accepted a fingerprint or a face.

## Auth0

The current device calls Auth0 `POST /oauth/revoke` with its own refresh token when that token is in SecureStore, on sign-out and when the API reports `device_session_revoked`. That call is skipped when there is no refresh token.

Full revocation of refresh tokens on other devices is not implemented. These environment variables are optional and unused by the API today:

```bash
AUTH0_MGMT_DOMAIN=
AUTH0_MGMT_CLIENT_ID=
AUTH0_MGMT_CLIENT_SECRET=
```

Leaving them empty is the expected MVP setup. Setting them does not make the API call Auth0. Other phones can still refresh at Auth0 until those refresh tokens expire. They cannot call HMore once their device session is `revoked` or `lost` and they send `X-Device-Session-Id`.

## What to expect

- Organisation sign-in still happens through Auth0. The biometric switch appears on the tenant Account screen, the staff More screen, and Privacy & Security. Turning it on asks the operating system first. Cancelling leaves the switch off.
- After sign-in, the app registers an installation and sends `X-Device-Session-Id` on later API calls. Web clients that omit the header still work.
- Sign out revokes this device's row. Sign out device and Report lost act on the listed rows. A revoked installation cannot be registered again. The next organisation login uses a new installation id.
- A 401 `device_session_revoked` clears SecureStore tokens, stops sync, and shows a sign-in message. Offline drafts remain for that same user.
- While the phone is offline, a remote revoke is not visible until the next API call or sync check. Local drafts can still be opened on the unlocked device during that gap.

See `docs/architecture/BIOMETRIC_REMOTE_SIGNOUT_ARCHITECTURE.md`.
