# Boss meeting — dummy auth (local only)

## Enable (already set for this machine)

| App | Flag |
| --- | --- |
| API | `HMORE_DEMO_AUTH=true` + `ENVIRONMENT=development` in `apps/api/.env` |
| Web | `NEXT_PUBLIC_DEMO_AUTH=1` in `apps/web/.env.local` |
| Mobile | `EXPO_PUBLIC_DEMO_AUTH=1` in `room-ready/.env` |

**Never set these in production.**

## Web (best for boss)

1. API + web running  
2. Open **http://localhost:3000/demo-login**  
3. Tap each role: Super Admin, Org Admin, Landlord, Tenant, Support Worker, Contractor  

## Mobile

1. Restart Expo: `npx expo start --lan --clear`  
2. Sign in → **six role buttons** (dummy auth)  
3. Pick a role — talks to FastAPI with a demo token  

## API check

```text
POST http://127.0.0.1:8000/api/v1/auth/demo/login
{"role":"super_admin"}
```

## Turn off later

Remove/set false: `HMORE_DEMO_AUTH`, `NEXT_PUBLIC_DEMO_AUTH`, `EXPO_PUBLIC_DEMO_AUTH`.
