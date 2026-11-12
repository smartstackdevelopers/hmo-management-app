# Mobile App Store & Google Play release (F7.7)

**App:** unified Expo project `room-ready` (tenant + staff shells).  
**Bundle IDs:** `com.roomready.app` (unchanged — confirm against existing store listings).

## Preconditions

- [ ] F7.6 production API live + HTTPS URL approved
- [ ] Auth0 native app configured (UK/EU tenant)
- [ ] Apple Developer + Google Play Console access — **PENDING APPROVAL**
- [ ] Privacy policy URL + support contact — `room-ready/store/STORE_OWNER_INPUTS.md`
- [ ] EAS project UUID in `EXPO_PUBLIC_EAS_PROJECT_ID`

## EAS build (does not submit)

```bash
cd room-ready
# Set secrets: eas secret:create --scope project --name EXPO_PUBLIC_HMORE_API_URL --value https://...
npm run build:ios
npm run build:android
```

Profiles: `development`, `preview` (internal APK), `production` (AAB + iOS store).

## Submit (owner approval only)

1. Complete TestFlight / Play internal testing checklist in F7.7 report.
2. Merge `store/eas.submit.json.example` into local EAS config or use CLI flags.
3. `eas submit --platform ios --profile production` — **after explicit sign-off**
4. `eas submit --platform android --profile production` — **after explicit sign-off**

Never commit signing keys or Play service account JSON.

## Production API guard

`validateProductionApiUrl()` in `lib/hmore/release/productionApi.ts` — used in release tests.
