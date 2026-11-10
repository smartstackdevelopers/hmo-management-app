# Staff mobile setup (F4.2)

The Expo app is `room-ready/`. From the monorepo root:

```bash
npm install
npm run typecheck -w room-ready
npm test -w room-ready
npm run start -w room-ready
```

Sign in with Auth0 using a user whose active role is `support_worker`, `organisation_admin`, or `maintenance_contractor`. Tenant sign-in still opens the F4.1 tabs. Copy `room-ready/.env.example` to `room-ready/.env` and set the same public Auth0 and API variables as the tenant app. Do not put an Auth0 client secret in the app.

```bash
EXPO_PUBLIC_HMORE_API_URL=http://localhost:8000/api/v1
EXPO_PUBLIC_AUTH0_DOMAIN=your-tenant.uk.auth0.com
EXPO_PUBLIC_AUTH0_CLIENT_ID=
EXPO_PUBLIC_AUTH0_AUDIENCE=https://api.hmore.local
EXPO_PUBLIC_AUTH0_SCHEME=roomready
```

Run the FastAPI app on port 8000. Staff screens call the existing `/api/v1` routes listed in `docs/architecture/STAFF_MOBILE_ARCHITECTURE.md`.

## What to expect on a device

- Dictation needs a development build that includes `expo-speech-recognition`. In Expo Go, or when the recogniser is missing, the note screen says speech recognition is not available and the text field still works. Optional AI rewrite is separate and is off until the organisation enables it. See `docs/development/VOICE_NOTES_SETUP.md`.
- Drafts stay on the device until a sync receives HTTP 2xx. Turn on airplane mode, save a note, and the screen should say it is not on the server yet.
- Occupancy shows surveys or an empty list, plus a Phase 6 notice. It does not show a live people count.
- Notifications are still the in-app inbox. The app registers an Expo push token when notification permission and a real EAS project id are present. Without Expo API credentials that registration does not deliver a notification to the device. See `docs/development/PUSH_NOTIFICATIONS_SETUP.md`.
- Photo upload accepts JPEG, PNG, and WebP up to 10 MB. A larger or different file is rejected before upload.

`apps/mobile` remains a pointer to this Expo project. Do not use Expo web as the admin dashboard.
