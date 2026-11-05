# F1.9 Dashboard shell testing

```text
cd apps/web
npm run typecheck
npm run lint
npx playwright test e2e/dashboard.spec.ts e2e/health.spec.ts
```

## Coverage

| Case | How |
| --- | --- |
| Nav permission filtering | Playwright imports `filterNavItems` |
| Role home mapping / wrong-role deny helpers | Playwright imports `dashboardAccess` |
| Unauthenticated `/dashboard` | Redirect or Auth0-not-configured empty state |
| Public home + unauthorized page | Playwright UI |
| Mobile menu control | Viewport 390×844 when shell renders |

Live Auth0 login and real membership routing are **not** claimed as production-verified in CI (placeholder tenant).
