# Local demo links (meeting / boss)

## Real HMore (PostgreSQL + Auth0) — use after Docker + bootstrap

| What | URL |
| --- | --- |
| **Web login** | http://localhost:3000/auth/login |
| **Dashboard** | http://localhost:3000/dashboard |
| **Super Admin orgs** | http://localhost:3000/dashboard/super-admin/organisations |
| **Platform admin** | http://localhost:3000/dashboard/platform-admin |
| **API docs** | http://127.0.0.1:8000/docs |
| **API health** | http://127.0.0.1:8000/health |

Login: Auth0 only (same email as `scripts/meeting-demo.local.env` / bootstrap).

## Mobile (Expo)

| What | URL / action |
| --- | --- |
| **Laptop (browser)** | http://localhost:8081 |
| **Android phone** | Install **Expo Go** → scan QR from `npm run start -w room-ready` |
| **API (phone)** | `EXPO_PUBLIC_HMORE_API_URL=http://YOUR_PC_IP:8000/api/v1` in `room-ready/.env` |

Auth0 mobile: set `EXPO_PUBLIC_AUTH0_CLIENT_ID` (Native app in Auth0). Until then use web for Super Admin.

## Legacy mobile demo only (not Super Admin)

| What | URL |
| --- | --- |
| Demo API | http://localhost:3001/health |
| Login | `landlord@roomready.co.uk` / `Password123` |

## One command to prepare DB + roles + start windows

```powershell
cd "D:\hmore app"
.\scripts\start-meeting-demo.ps1
```

Requires **Docker Desktop Running** and `scripts/meeting-demo.local.env` with `MEETING_ADMIN_EMAIL`.