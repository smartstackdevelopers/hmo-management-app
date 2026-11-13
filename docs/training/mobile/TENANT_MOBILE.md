# Tenant mobile app — user manual

**App:** HMore (Expo, `room-ready`). **Install:** App Store / Play when organisation publishes build (F7.7).

## Installation & first launch

1. Install from official store link only.
2. Open app → Auth0 login.
3. Optional: enable biometrics after first successful login (**Settings / Security**).

## Main areas (tabs)

| Area | Route | Backend |
| --- | --- | --- |
| Home | `/(tabs)/index` | FastAPI |
| Tenancy | `/(tabs)/tenancy` | Housing |
| Maintenance | `/(tabs)/maintenance`, `/maintenance/new` | Maintenance API |
| Support | `/(tabs)/support` | Support plans |
| More | `/(tabs)/more` | Settings links |

## Repairs with photos

1. **Maintenance → New**.
2. Complete form — property/room as guided.
3. Attach photos — camera or library.
4. Submit — wait for sync if offline (draft queue).

## Documents

- Upload PDF/images within size limits; downloads use signed URLs via API.

## Community & jobs

- **Help near me**, **Community**, **Employment**, **Job matching** — if tabs visible, org enabled modules.

## Notifications

- Allow when prompted; opens deep link to inbox/tasks (generic preview).

## Language & accessibility

- **Accessibility** screen; i18n where strings provided (EN/UR partial).

## Troubleshooting

| Issue | Action |
| --- | --- |
| Cannot login | Check Auth0 user exists; contact OA |
| API error | Confirm `EXPO_PUBLIC_HMORE_API_URL` HTTPS in production build |
| Stuck offline draft | Open **Offline drafts** → retry sync |

Use fictional names in exercises only (e.g. “Alex Example”).
