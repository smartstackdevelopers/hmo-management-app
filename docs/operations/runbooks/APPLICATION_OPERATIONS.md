# Application operations

Safe troubleshooting for web, API, AI, and mobile. **Requires authorised operator access** — use least privilege.

## Web application (`apps/web`)

### Health and availability

| Symptom | Check | Safe action |
| --- | --- | --- |
| Site down | Load `/` and `/health` | Verify hosting process; check API base URL env |
| Login loop | Auth0 dashboard, cookie domain | Confirm `AUTH0_*` and callback URLs |
| Blank dashboard | Browser devtools network | API 401/403 → auth or role; 5xx → escalate API |
| Slow pages | `/dashboard/performance` (authorised) | Review F7.4 probes; API latency |

### Login failures

1. Confirm Auth0 status (external).
2. Verify user has organisation membership and active role (`HMoreRole` enum — six roles only).
3. If MFA required: `AUTH0_REQUIRE_MFA_CLAIM=true` in production — user must complete MFA in IdP.
4. Check `/unauthorized` for permission denials (expected for wrong role).

### API connectivity from web

- Env: `NEXT_PUBLIC_API_BASE_URL` must match live API origin (HTTPS in production).
- CORS: production API settings must allow web origin (`apps/api` settings module).

### Restart (non-production / approved maintenance)

Restart Next.js process or ECS web task. No database impact.

---

## FastAPI backend (`apps/api`)

### Health checks

```http
GET /health
GET /api/v1/health
```

Expected: `status: ok`, service version present.

### API failures

| Symptom | Investigation | Resolution |
| --- | --- | --- |
| 503 on AI proxy routes | AI service health, `AI_SERVICE_TOKEN` | Restart AI; verify secrets |
| 401 on all routes | Auth0 JWKS, clock skew | Fix IdP; check `AUTH0_DOMAIN` |
| 403 organisation | Missing `X-Organisation-Id` or membership | Fix client headers / membership |
| 500 spikes | Sentry / logs | Identify stack trace; hotfix or rollback **image** only |

### Database connection failures

1. Verify `DATABASE_URL` / Secrets Manager value.
2. Check RDS/security group (production) or local Postgres up.
3. Connection pool exhaustion: reduce concurrent workers; scale API tasks **PENDING CAPACITY APPROVAL**.

**Warning:** Do not run `DROP DATABASE` or destructive SQL without written approval and isolated target.

### Request timeouts

- Review reverse proxy / ALB idle timeout.
- Long reports: may need async job pattern — check Celery queue, not infinite sync timeout.

### Restart

1. Deploy new task or restart Uvicorn process.
2. Celery workers separate restart — see DATABASE_OPERATIONS → Redis/Celery.

---

## AI services (`apps/ai-service`)

### Health

`GET /health` and `GET /api/v1/health`.

### Failure modes

| Issue | Cause | Action |
| --- | --- | --- |
| 503 workflows disabled | Token unset or feature flags | Set `AI_SERVICE_TOKEN`; check org AI flags |
| Provider errors | `OPENAI_API_KEY` / routing | Verify secrets; check usage caps dashboard |
| Timeouts | Model latency | Retry; reduce payload; escalate provider status |
| Human approval stuck | Support plan / housing drafts | Staff must approve in UI — AI does not auto-approve |

### Usage limits

Organisation AI usage caps (F3) — monitor super-admin / org dashboards when enabled. Alert meaning: approaching cap → slow or block new AI calls.

### Reporting incorrect AI output

Staff: use AI feedback endpoints where implemented; record in case notes. Not an automatic incident unless data leakage suspected → security plan.

---

## Mobile (`room-ready`)

### Login issues

- Auth0 native app configuration (client ID, redirect).
- Production API URL validation (`validateProductionApiUrl()` — HTTPS, no dev hosts).

### API connectivity

- `EXPO_PUBLIC_HMORE_API_URL` (or project equivalent) must match API.
- Certificate / TLS errors: fix server chain, not app bypass.

### Push notifications (F4)

Failures: check device registration API, FCM/APNs credentials **PENDING APPROVAL** in store ops docs (`room-ready/store/`).

### Offline sync (F4)

- Drafts stored locally (SecureStore / encrypted draft pattern).
- Sync failures: check network, idempotency headers on API; review mobile logs; user can retry when online.

### Upload failures

- File size/type limits on API (F1.8).
- S3 IAM role or local storage path for dev.

### Crashes

- Sentry mobile DSN **PENDING APPROVAL**.
- Reproduce on staging build; capture build channel from EAS.

---

## Room occupancy incidents

| Scenario | Action |
| --- | --- |
| Camera/sensor failure | **No live ingest** until gate approved; log maintenance ticket |
| Incorrect counts | Use correction workflow if gate complete; else feasibility/DPIA path |
| Device disconnect | Physical ops + landlord; no remote bedroom cameras per policy |
| Privacy complaint | DPO path → breach/complaints procedure; preserve audit logs |
| Unauthorised access | Security incident plan; revoke sessions (`device sessions` F4.6) |
| Data retention | F7.2 retention templates — no automatic deletion without approval |

Do **not** enable live ingest without recorded DPIA approval in app gate.
