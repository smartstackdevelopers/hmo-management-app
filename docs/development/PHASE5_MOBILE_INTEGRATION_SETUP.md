# F5.6 Community mobile integration — setup and test

## Prerequisites

- `develop` includes F5.1–F5.5 migrations through `20261110_3800_f55`
- Tenant Auth0 user with `tenant` role and organisation membership

## Mobile

1. Start API and Expo app (`room-ready`).
2. Sign in as a tenant.
3. Home → **Open Community**, or Account → **Community and career**.
4. From the hub, open each section and confirm live API data:
   - Community support → directory filters / detail
   - Help near me → postcode search, map/list, report
   - Skills and career → assessment, CVs, PDF
   - Find jobs / training / applications → F5.4 + F5.3 tracker
   - Wellbeing / routines → check-in, disclaimer, private records

## Automated tests

```bash
cd room-ready
npx jest __tests__/phase5CommunityHub.test.ts __tests__/tenantMobile.test.ts --runInBand
```

Optional API regression (no new migration for F5.6):

```bash
cd apps/api
python -m pytest tests/test_f55_wellbeing.py tests/test_f54_job_matching.py tests/test_f53_employment_prep.py tests/test_f52_help_near_me.py tests/test_f51_community_directory.py -q -m "not postgres"
```

## Known limits

- Device Android/iOS UI runs require a simulator or handset.
- Job source APIs (Adzuna/Reed) remain optional; search still works when AI/sources are unavailable.
