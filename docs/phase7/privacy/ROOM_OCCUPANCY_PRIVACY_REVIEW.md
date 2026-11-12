# Room occupancy privacy review (F6.5 / F7.2)

**Live camera / ingest status:** **BLOCKED** until organisation privacy gate complete.  
**Formal deferral:** `docs/phase6/F6.5_OCCUPANCY_FORMAL_DEFERRAL.md`

## Proposal checks

| Requirement | Technical status |
|-------------|------------------|
| No facial recognition | **PASS** (design + tests) |
| No identity tracking | **PASS** |
| No cameras in bedrooms/bathrooms/changing rooms | Organisation configuration + signage gate |
| No raw video storage by default | **PASS** (counts only) |
| Edge-based counting | Supported when gate complete + devices configured |
| DPIA approval | **PENDING APPROVAL** — `dpia_status` default `not_started` |
| Access logging | Corrections and gate updates audited |
| Live ingest | **403** when gate incomplete |

## Linked records

- F7.2 privacy DPIA entry `room_occupancy_live` (status not auto-approved)
- F7.2 dashboard surfaces `room_occupancy_privacy_gate` from live database row

## Outstanding actions

1. Organisation completes feasibility, DPIA, signage, retention, camera compatibility in Room Occupancy UI.
2. Authorised administrator records formal approval — HMore never auto-approves.
