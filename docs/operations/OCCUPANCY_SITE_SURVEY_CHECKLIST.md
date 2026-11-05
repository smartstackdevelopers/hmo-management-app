# Occupancy Site-Survey Checklist (F1.10)

**Purpose:** Structured field checklist for assessing whether a property/site is suitable for HMore supported-housing operations and for gathering information needed before any future room-occupancy camera/sensor programme.

**Out of scope:** Camera installation, live video, computer vision, facial recognition, biometric monitoring, and automated occupancy counting. Those remain gated by DPIA and later phases.

**Status of fields:** Items marked **Proposed assessment field** are practical survey prompts; they are not claimed as a signed-off HMore legal requirement unless already stated in the approved proposal.

**Disclaimer:** Completing this checklist does **not** certify legal, planning, fire, or housing-regulation compliance.

---

## Instructions for surveyors

1. Confirm organisation and property identity with the Organisation Admin or landlord contact.
2. Walk the site with a site contact where possible.
3. Record observations honestly; mark unknowns as *Further information required*.
4. Attach evidence only via HMore private file storage (never public links).
5. Record findings and recommended actions with severity.
6. Set an overall feasibility status supported by findings (operational assessment only).
7. Do not enable or discuss camera build until DPIA/signage/retention gates are complete.

---

## A. Site identification

| Field | Value / notes |
| --- | --- |
| Organisation | |
| Property name | |
| Property reference / ID | |
| Address | |
| Survey date | |
| Surveyor name | |
| Surveyor user ID (if known) | |
| Site contact name / role | |
| Site contact details | |
| Survey status | draft / in_progress / completed |

---

## B. Building assessment

| Check | Observation | Suitability notes |
| --- | --- | --- |
| Building type | | |
| General condition | | |
| Number of floors | | |
| Access arrangements (entry control, keys, staffed reception) | | |
| Common areas (corridors, lounges, stairs) | | |
| Emergency exits | | |
| Fire safety provisions observed (alarms, extinguishers, signage) — *observation only* | | |
| General suitability for intended housing/support use | | |

**Proposed assessment field:** Note any obvious maintenance backlog that would block safe occupancy operations.

---

## C. Room assessment (repeat per room)

| Field | Value / notes |
| --- | --- |
| Room identifier / label | |
| Linked HMore room ID (if exists) | |
| Room type (bedroom / communal / office / other) | |
| Approximate dimensions or area (*if available*) | |
| Intended use | |
| Capacity considerations (*do not invent statutory limits*) | |
| Current condition | | |
| Ventilation | | |
| Lighting | | |
| Heating | | |
| Privacy | | |
| Accessibility | | |
| Suitability notes | | |
| Identified risks | | |

**Proposal gate prompts (camera programme — assessment only):**

| Prompt | Notes |
| --- | --- |
| Is this a bedroom, bathroom, or changing room? | Cameras must never be proposed for these spaces. |
| Existing cameras/sensors present? | Record make/model/location only; do not connect. |
| Intended viewer roles (if occupancy counting were later approved) | Org Admin / permitted Support Worker only per proposal. |
| Accuracy / update-frequency needs (*proposed*) | |
| Signage / notice feasibility | |

---

## D. Facilities and utilities

| Facility | Available? | Condition | Notes |
| --- | --- | --- | --- |
| Water supply | | | |
| Electricity | | | |
| Heating | | | |
| Ventilation | | | |
| Sanitation | | | |
| Internet / connectivity | | | |
| Waste management | | | |
| Kitchen facilities | | | |
| Laundry facilities | | | |
| Shared facilities | | | |

---

## E. Health, safety, and accessibility

| Check | Observation | Verification status | Applicable reference (*if known*) |
| --- | --- | --- | --- |
| Fire safety observations | | observed / not verified / N/A | |
| Emergency evacuation arrangements | | | |
| First-aid arrangements | | | |
| General hazards | | | |
| Safe access and circulation | | | |
| Accessibility considerations | | | |
| Lighting and visibility | | | |
| Maintenance issues | | | |
| Other site-specific risks | | | |

Do not tick “compliant” unless an applicable standard has been verified by a competent person. Prefer *observed*, *not verified*, or *further assessment required*.

---

## F. Evidence log

| Evidence ref | Related section / room / finding | Private file ID | Notes |
| --- | --- | --- | --- |
| | | | |

Use HMore `POST /api/v1/files` and store the returned file id — never public bucket URLs.

---

## G. Feasibility summary

| Overall status | Tick one |
| --- | --- |
| Suitable | |
| Suitable subject to actions | |
| Not currently suitable | |
| Further assessment required | |

**Summary narrative:**

**Missing information:**

**Recommendations / remedial actions:**

**Reviewer name / date:**

---

## Explicit non-goals

- No camera build, streaming, recording, or people-counting software in this pack.
- No facial recognition and no identity tracking.
- No claim that HMore has completed a DPIA for this site until separately documented.
