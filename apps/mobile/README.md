# Mobile (Expo)

The production mobile surface is React Native + Expo.

F1.1 does **not** move the existing Room Ready Expo app. `TARGET_ARCHITECTURE.md` keeps `room-ready/` in place until a later chore updates import paths, EAS config, and CI together.

Current Expo application: [`../../room-ready`](../../room-ready)

That app remains the tenant and staff mobile reference. It is included in the npm workspace as `room-ready`. CI typechecks it. Do not treat Expo web as the HMore admin dashboard; that is `apps/web`.
