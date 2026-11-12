# HMore mobile store release assets (F7.7)

**Do not invent** privacy URLs, support emails, or company legal names. Replace `PENDING_APPROVAL` placeholders with client-provided values.

| Item | File | Status |
| --- | --- | --- |
| Apple description | `metadata/apple/description.en-GB.txt` | Template |
| Google full description | `metadata/google/full_description.en-GB.txt` | Template |
| Privacy policy URL | `STORE_OWNER_INPUTS.md` | **PENDING APPROVAL** |
| Support URL / email | `STORE_OWNER_INPUTS.md` | **PENDING APPROVAL** |
| Screenshots | `screenshots/` | Add per store guidelines |
| Submit config | `eas.submit.json.example` | Copy locally; never commit keys |

Build: `npm run build:ios` / `npm run build:android` (requires EAS login + credentials).

Submit: **explicit project owner approval only** — `eas submit` after TestFlight/internal testing passes.
