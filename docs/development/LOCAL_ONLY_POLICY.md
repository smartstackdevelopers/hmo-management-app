# HMore — Local-only development policy

**Decision date:** 2026-11-16 (reconfirmed)

The project is **not ready for hosting or production deployment**.  
All remaining development continues **exclusively in the local environment**.

## Allowed (local only)

- Local Docker (Postgres + Redis on localhost ports)
- Local PostgreSQL databases `hmore` and `hmore_test`
- Local Alembic migrations
- Local Super Admin bootstrap / password reset for native auth
- Local native authentication, registration, and approval workflows
- Local web (`localhost:3000`) and mobile (`localhost:8081` / Expo LAN)
- Local AI and backend integration
- Local security and acceptance testing

Keep application services accessible only through the intended local development environment.

## Prohibited until explicitly authorised later

- AWS deployment or any cloud hosting
- Production database changes
- Public internet exposure of services
- Production credentials
- Live user migration
- Go-Live
- App Store / Google Play publishing

**Do not** treat local database activation as production deployment.  
Local migrations and local end-to-end testing are required.  
**Do not** perform hosting or deployment steps unless explicitly authorised later.
