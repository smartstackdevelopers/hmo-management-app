# HMore — Proposal-Exact Complete Implementation Plan v1.0

**Smart Stack Developers**

1:1 with Smart Vite Project Proposal v1.3. Zero feature gap in core scope.

| | |
| --- | --- |
| Product name in delivery | HMore |
| Requirements source | Smart Vite Project Proposal v1.3 |
| Delivery structure | Proposal Section 10 (7 phases) |
| Feature inventory | Proposal Sections 3 to 9 (complete) |
| Add-ons | Proposal Section 11 (optional, separate) |
| Document ID | HMORE-PROP-EXACT-1.0 |
| Date | 2026-11-01 |

No timeline estimates in this document.

If this plan is fully implemented, HMore matches proposal core scope.

---

## 0. Alignment rules (no difference policy)

### Source of truth

Smart Vite Project Proposal v1.3 is the requirements contract. HMore is the delivery product name for the same scope. This plan does not remove, weaken, or replace any core proposal requirement. Optional add-ons stay optional exactly as Section 11.

### What must match the proposal exactly

- 14 platform modules with every listed capability
- Exactly 6 user roles (no extra core roles, no missing roles)
- 6 AI agents on one shared capped AI service
- Web + iOS + Android
- Room occupancy privacy rules and 10 required features
- Technology stack from Section 8
- Security, privacy, and compliance from Section 9
- Delivery order from Section 10 (7 phases)
- Section 11 items only as optional add-ons

### Naming map

| Proposal term | HMore delivery term |
| --- | --- |
| Smart Vite | HMore |
| Smart Vite Backend API | HMore Backend API (Python + FastAPI) |
| Room Ready baseline code | Reference/reuse only; target architecture is the proposal stack |

### Working rule

Implement HMore using this plan. Requirements must match Smart Vite Proposal v1.3 with no feature gap.

Use the proposal stack: Next.js web, Expo mobile, Python FastAPI backend, PostgreSQL + pgvector, LangGraph AI service, Celery + Redis, private S3, AWS UK/EU.

Six roles only. Human approval for important AI actions. Caps required.

Work only the phase number that is specified. Meet that phase exit checklist fully before the next phase.

---

## 1. Technology stack (Proposal Section 8 — exact)

| Layer | Required stack |
| --- | --- |
| Web dashboard | Next.js + TypeScript + Tailwind CSS |
| Mobile iOS/Android | React Native + Expo |
| Backend API | Python + FastAPI, REST with OpenAPI |
| Database | PostgreSQL (+ pgvector for search/embeddings) |
| AI | Tiered LLM API + LangGraph workflows; usage caps |
| Login/identity | Managed identity: Entra External ID or Auth0 |
| Background jobs | Celery + Redis (or managed queue); batch AI jobs |
| Files | Private S3-compatible storage |
| Cloud | AWS, UK/EU region |
| Cameras/sensors | Edge people counting; ONVIF/RTSP; WebSockets/MQTT (confirm) |
| Quality | GitHub Actions, Pytest, Playwright |
| Monitoring | Sentry or equivalent |

### Architecture rule

One shared backend for web, iOS, and Android. AI is a separate shared service called through controlled gateway patterns. Do not invent a different primary backend language for the core business API.

### Target repo shape

```text
hmore/
  apps/web                 # Next.js
  apps/mobile              # Expo (from current room-ready as starting UI)
  apps/api                 # Python FastAPI (proposal backend)
  apps/ai-service          # LangGraph + tiered LLM gateway
  packages/shared-contracts
  infra/                   # docker, AWS, CI
  docs/
```

The current Node/Express API may be used only as temporary reference while the FastAPI domain is built to the proposal. The final production backend must be Python + FastAPI.

---

## 2. Six roles (Proposal Section 3 — exact)

| Role | Duties |
| --- | --- |
| Super Admin | Creates and manages organisations; platform-wide settings and monitoring |
| Organisation Admin | Users, settings, and workflows; reviews applications and decisions; compliance checks, reports, and audit logs; room occupancy and alerts |
| Landlord | Properties, rooms, and vacancies; tenancies, inspections, and rent records; repair status on own properties |
| Tenant | Own profile, plan, and documents; report repairs and complaints; find local services, jobs, and training |
| Support Worker | Notes, plans, visits, and tasks; employment support (skills, CVs, jobs, training); incident reports and follow-ups |
| Maintenance & Contractors | Work orders and repair updates; photos and proof of completion; scheduling and job approvals |

Removed roles from older drafts are **not** separate roles: Council Officer, Housing/Property Manager, Employment Support Worker, Compliance Officer, Facilities Manager, Finance Officer, Auditor. Their duties are folded as in the proposal. Council Portal is a Section 11 add-on only.

---

## 3. Complete feature inventory (Proposal Section 4 — all 14 modules)

Every bullet below is mandatory core scope. Implementation is incomplete if any bullet is missing.

### 01 Accounts & Access

- Role-based permissions for six roles
- MFA and session control
- Separate data per organisation
- Audit logs and logged emergency access

### 02 Tenant Management

- Contacts, consent, and preferences
- Tenancy, needs, and goals
- Meetings, appointments, and follow-ups
- Tenant timeline and own-record access

### 03 Housing Management

- Properties, rooms, and vacancies
- Applications and waiting lists
- Evidence checklist and Evidence Pack Generator
- Approval tracking and council-ready exports

### 04 Staff Management

- Caseloads, daily logs, and handovers
- Rota, visits, and tasks
- Training and safeguarding reminders
- Incident reports and workload dashboards

### 05 Support Plans

- Personal goals and milestones
- Weekly and monthly reviews
- Employment and independent-living goals
- Progress report export

### 06 Jobs & Skills

- Skills assessment and CV builder
- Job and training suggestions from verified sources
- Application tracker and interview prep
- Personal Career Roadmap

### 07 Community Services

- Food banks, kitchens, and clothing banks
- Help Near Me postcode search
- Opening hours and eligibility
- Report outdated listings

### 08 Maintenance & Complaints

- Report issues with photos
- Priorities, deadlines, and escalation
- Contractor scheduling and approvals
- Emergency instructions for gas or fire

### 09 Wellbeing

- Check-ins and daily routine planner
- Exercise and mindfulness resources
- Local wellbeing directory
- Support Navigator (not a clinical tool)

### 10 Organisations & Approvals

- Approval queues and decision history
- Custom forms and workflows
- Secure sharing and audit-log access
- Optional Council Portal only as a Section 11 add-on

### 11 Communication

- In-app messages
- Push, email, and SMS
- Reminders and alerts
- Emergency announcements and translation

### 12 Documents

- Upload, OCR, and version history
- Smart Document Checker
- Expiry reminders
- E-signatures, retention, and access requests

### 13 Reports & Analytics

- Occupancy, applications, and complaints
- Caseloads and plan completion
- PDF, CSV, and Excel export
- Scheduled reports and early-warning alerts

### 14 Room Occupancy

- Live people count per room
- Status and capacity alerts
- History and usage reports
- No facial recognition (see occupancy section)

---

## 4. AI agents and cost control (Proposal Section 5 — exact)

All six agents share one AI service. Fixed step-by-step workflows. Rules and search first. Model calls only where valuable. People stay in control.

| Agent | Runtime note | Must deliver |
| --- | --- | --- |
| Notes Analysis Agent | Low-cost; overnight batch or on demand | Summarise daily notes; find missing details; suggest next actions |
| Support Planning Agent | Low-cost; when plan opened | Draft personal action plans and follow-ups from agreed goals |
| Housing Application Agent | OCR + rules first; AI for gaps | Document checklists; flag missing evidence |
| Compliance Agent | Rules/scheduled jobs; AI to explain | Check records vs policies; flag overdue actions |
| Job Matching Agent | Search/embeddings; AI for CV/interview tips | Suggest jobs, training, and career resources that fit the tenant |
| Tenant Assistant | Low-cost with cached approved content | Answer from approved information; help raise requests |

### Also included smart features (mandatory)

- Voice-to-text notes (phone speech recognition first) and professional rewriting
- Duplicate case, complaint, and document detection (search-based, no AI call per record)
- Natural-language search (example: show open water complaints)
- Weekly and monthly report drafts and overdue reminders

### Responsible AI rules (mandatory)

- Important actions need human approval
- Every AI answer shows sources and confidence
- All AI activity is logged
- Staff can report wrong answers
- AI is not used for employee surveillance or automatic punishments
- If AI could affect housing or employment decisions, legal automated-decision risks are assessed separately

### Cost-control measures (mandatory)

- One shared AI service, shared prompts and tools, fixed workflows
- Right-sized models: low-cost default; premium only with human review
- Rules before AI for duplicates, expiry, overdue, compliance, and search
- Batch and scheduled jobs for overnight summaries, reports, and compliance
- Caching and short prompts; history summarised or retrieved, not fully resent
- Speech on device first
- Monthly AI budgets and usage limits per organisation, plus a cost dashboard and cost-per-feature tracking
- Pilot first: Notes Analysis and Smart Document Checker, then expand

---

## 5. Mobile apps (Proposal Section 6 — exact)

### Tenant App (mandatory)

- Login and profile
- Housing information
- Report repairs with photos
- Support plan and appointments
- Food banks and local services
- Job and training ideas
- Documents and notifications
- AI assistant, language, and accessibility settings

### Staff App — Support Workers, Maintenance & Contractors (mandatory)

- Assigned tenants and shifts
- Daily notes with voice dictation
- Visit records, tasks, and follow-ups
- Work orders and repair updates (contractors)
- Incident reporting
- Secure photo and document upload
- Room occupancy view (permitted staff)
- Supervisor review and push alerts
- Offline drafts that sync securely

### Surface rules

- Web dashboard is primary for Super Admins, Organisation Admins, and Landlords
- Mobile access for those roles can be added if the client needs it
- Mobile security: fingerprint or face unlock, device protection, remote sign-out if the phone is lost

---

## 6. Room occupancy (Proposal Section 7 — exact)

Authorised staff see estimated people counts only. No facial recognition. No identity tracking. Process counts on device. No video stored by default. No cameras in bedrooms, bathrooms, or changing rooms.

### Statuses

- Available
- Occupied
- Near Capacity
- At Capacity (alert)
- Offline (alert)

### 10 required features (all mandatory when occupancy is in scope)

1. Live occupancy: estimated people in each room
2. Room dashboard: building, floor, room, count, max capacity
3. Camera/sensor integration with people counting only
4. Status model as above
5. Automatic alerts for capacity reached or equipment stop
6. History and usage-pattern reports
7. Access limited to Organisation Admin and permitted Support Workers, with access logs
8. Accuracy: last update time, estimated label, manual correction with audit trail
9. Privacy/security: no private spaces; notices; data-protection check first
10. Web and mobile for permitted users

### Gate before build

Complete DPIA, signage, and retention rules first. Confirm room types, purpose, existing cameras, who may view, retention, and accuracy needs. Final design after compatibility, layout, and privacy confirmation.

---

## 7. Security, privacy, and compliance (Proposal Section 9 — exact)

- UK GDPR and Data Protection Act 2018; DPIA where required
- Each organisation sees only its own data
- Encryption in transit and at rest
- MFA, least-privilege six roles, secure sessions
- Audit logs: who saw or changed what, and when
- Backups, disaster recovery, and breach-response plan
- Retention, deletion, and access-request support
- Restricted AI data access; human review; usage caps
- WCAG 2.2 AA design target
- Camera data: counts only, no facial recognition, restricted and logged
- Vulnerability testing before launch
- Configurable rules by UK nation and council

---

## 8. Delivery phases (Proposal Section 10 — exact order)

Implement in this exact phase order. Each phase lists proposal deliverables expanded into complete build features with no omissions from core scope.

### PHASE 1 — Foundation

**Proposal deliverables:** Requirements sign-off; database design; login with MFA; six roles; organisations; tenants and properties; audit logs; CI/CD; site survey for camera/occupancy feasibility.

**Branch family:** `feature/phase1-*` / `chore/phase1-*`

**Build features**

- **F1.1** Monorepo + CI/CD (GitHub Actions, Pytest, Playwright baseline)
- **F1.2** PostgreSQL schema design for all Phase 1 entities + migrations
- **F1.3** Managed identity integration start (Auth0 or Entra External ID) + MFA
- **F1.4** Six roles + permission matrix + session control
- **F1.5** Organisation isolation model and membership
- **F1.6** Tenant and property/room baseline CRUD
- **F1.7** Audit log framework + emergency access logging
- **F1.8** Private file storage interface (S3-compatible)
- **F1.9** Web dashboard shell for Super Admin / Org Admin / Landlord login homes
- **F1.10** Occupancy site-survey checklist and feasibility pack (no camera build yet)
- **F1.11** Encryption, env secrets, AWS UK/EU target architecture baseline docs

**Phase 1 exit (must all pass)**

- MFA login works for staff/admin paths
- All six roles exist and are enforceable
- Org data separation proven by deny tests
- Tenant + property records creatable with audit entries
- CI pipeline green
- Occupancy feasibility survey template completed for client

### PHASE 2 — Core Operations

**Proposal deliverables:** Support notes; housing cases; complaints and repairs; tasks and reminders; dashboards and basic reports.

**Branch family:** `feature/phase2-*`

**Build features**

- **F2.1** Support worker caseloads, daily logs/notes, handovers
- **F2.2** Rota, visits, tasks, reminders (Celery + Redis)
- **F2.3** Training and safeguarding reminders
- **F2.4** Incident reports + follow-ups + workload dashboards
- **F2.5** Housing applications, waiting lists, approval tracking
- **F2.6** Evidence checklist + Evidence Pack Generator + council-ready exports
- **F2.7** Complaints workflow with priorities, deadlines, and escalation
- **F2.8** Maintenance/repairs with photos, contractor scheduling/approvals, emergency gas/fire instructions
- **F2.9** Tenant timeline, meetings/appointments/follow-ups, needs/goals fields
- **F2.10** Support plans: goals, milestones, weekly/monthly reviews, progress export
- **F2.11** Documents upload, version history, expiry reminders, retention, access requests, e-signatures
- **F2.12** Communication: in-app messages, email, SMS provider, reminders/alerts, emergency announcements + translation
- **F2.13** Organisations approvals inbox, custom forms/workflows, secure sharing, audit-log access UI
- **F2.14** Dashboards and basic reports (applications, complaints, caseloads) with CSV/PDF/Excel export baseline
- **F2.15** Ali end-to-end journey without AI automation (manual note → repair → admin → maintenance)

**Phase 2 exit (must all pass)**

- Ali scenario works fully without AI
- Every Phase 2 module bullet above is demoable
- Push can wait for Phase 4, but email + SMS + in-app channels exist
- No silent failures on authz or required writes

### PHASE 3 — AI

**Proposal deliverables:** AI gateway with model routing, caching, and usage caps; notes analysis; case summaries; Smart Document Checker; tenant assistant pilot; human approval and AI logs; AI cost dashboard.

**Branch family:** `feature/phase3-*`

**Build features**

- **F3.1** Shared AI service (LangGraph) + OpenAPI gateway + prompt versions
- **F3.2** Model routing (low-cost default, premium escalation) + caching + batch jobs
- **F3.3** Per-organisation usage caps, cost-per-feature meters, AI cost dashboard
- **F3.4** Notes Analysis Agent (summary, missing details, next actions) + human approval inbox
- **F3.5** Case summaries workflow
- **F3.6** Smart Document Checker (OCR + rules first, AI for gaps)
- **F3.7** Support Planning Agent drafts with human approval before apply
- **F3.8** Housing Application Agent checklist/gap narrative (no auto housing decision)
- **F3.9** Compliance Agent rules sweep + AI explanation
- **F3.10** Tenant Assistant pilot on approved/cached content only
- **F3.11** Duplicate detection via search (no AI call per record)
- **F3.12** Natural-language search over operational data
- **F3.13** Weekly/monthly report drafts + overdue reminders
- **F3.14** AI activity logs, confidence, sources, wrong-answer feedback
- **F3.15** Org AI feature flags and pilot enablement controls

**Phase 3 exit (must all pass)**

- Notes Analysis + Smart Document Checker live in pilot org
- Tenant Assistant pilot available
- Human approval required for important AI writes
- Hard cap rejects over-budget usage visibly
- AI cost dashboard usable by Org Admin / Super Admin

### PHASE 4 — Mobile

**Proposal deliverables:** Tenant and staff apps; push notifications; voice notes; offline drafts; biometric login.

**Branch family:** `feature/phase4-*`

**Build features (every Section 6 item)**

- **F4.1** Tenant app: login/profile, housing info, repairs + photos, support plan/appointments, food banks/local services, jobs/training ideas, documents/notifications, AI assistant, language + accessibility settings
- **F4.2** Staff app: assigned tenants/shifts, daily notes + voice dictation, visits/tasks/follow-ups, contractor work orders/updates, incident reporting, secure uploads, occupancy view for permitted staff, supervisor review + push alerts, offline drafts secure sync
- **F4.3** Push notifications end-to-end
- **F4.4** Device speech-first voice notes + optional rewrite via AI service
- **F4.5** Offline drafts with secure sync and visible failure states
- **F4.6** Biometric unlock + remote sign-out
- **F4.7** Store-ready EAS builds for internal testing tracks

**Phase 4 exit (must all pass)**

- All Tenant App bullets demoable on device
- All Staff App bullets demoable on device
- Push, offline drafts, and biometrics verified
- Web remains primary for Super Admin / Org Admin / Landlord

### PHASE 5 — Community

**Proposal deliverables:** Food and local services finder; jobs and training matching; wellbeing resources.

**Branch family:** `feature/phase5-*`

**Build features**

- **F5.1** Community directory: food banks, kitchens, clothing banks; hours; eligibility; verification
- **F5.2** Help Near Me postcode search + report outdated listings + moderation
- **F5.3** Skills assessment + CV builder + application tracker + interview prep + Career Roadmap
- **F5.4** Job Matching Agent fully wired to verified sources (embeddings/search first)
- **F5.5** Wellbeing: check-ins, routine planner, exercise/mindfulness resources, local wellbeing directory, Support Navigator with non-clinical disclaimer
- **F5.6** Tenant mobile/community surfaces fully connected to these modules

**Phase 5 exit (must all pass)**

- Tenant can find local help by postcode
- Tenant can build a CV, track applications, and receive job/training suggestions
- Wellbeing tools available with disclaimer
- Outdated listing report works

### PHASE 6 — Enterprise

**Proposal deliverables:** Landlord tools and integrations; analytics; finance (optional); automation; room occupancy module (after feasibility and DPIA). Council Portal only if selected as an add-on.

**Branch family:** `feature/phase6-*`

**Build features (complete core)**

- **F6.1** Landlord enterprise tools: portfolio analytics depth, rent records (records ledger), inspections at scale, repair status oversight
- **F6.2** Full reports and analytics: occupancy, applications, complaints, caseloads, plan completion; PDF/CSV/Excel; scheduled reports; early-warning alerts
- **F6.3** Automation rules for reminders, escalations, and compliance sweeps
- **F6.4** Integration stubs/hub foundation for council/HR/finance/service APIs (full partner connectors may continue as the add-on Integration Hub)
- **F6.5** Room occupancy full module only after feasibility + DPIA + signage/retention: all 10 required features, edge counting, alerts, history, access logs, estimated labels, manual correction audit, web + mobile permitted views
- **F6.6** Finance module only if the client selects the optional finance add-on; otherwise keep rent records only as landlord records (no payment gateway unless Section 11 is selected)
- **F6.7** Council Portal is not built unless the Section 11 add-on is selected

**Phase 6 exit (must all pass)**

- Analytics exports and scheduled reports live
- Landlord enterprise views complete for core scope
- Occupancy either fully delivered under DPIA Go, or formally deferred with written gate status (no partial unsafe camera features)
- No Council Portal unless explicitly contracted

### PHASE 7 — Go-Live

**Proposal deliverables:** Security testing; GDPR/DPIA review; backup tests; performance and accessibility tests; app-store release; staff training.

**Branch family:** `release/1.0*`

**Build / verify features**

- **F7.1** Vulnerability / security testing and remediation
- **F7.2** GDPR/DPIA review complete for live modules (including occupancy if live)
- **F7.3** Backup and restore drill proven
- **F7.4** Performance tests on critical journeys
- **F7.5** WCAG 2.2 AA accessibility verification on critical paths
- **F7.6** Production AWS UK/EU deploy: API, web, AI, Postgres, Redis, S3, monitoring (Sentry)
- **F7.7** iOS App Store and Google Play production release
- **F7.8** Staff training materials and launch support
- **F7.9** Breach-response plan and operational runbooks published
- **F7.10** Final coverage audit: every Section 4–9 mandatory item checked Done

**Phase 7 / product exit (must all pass)**

- Production HMore live
- Coverage matrix 100% for core proposal scope
- Security and privacy sign-off complete
- Stores released (or approved release package submitted as required)
- Training delivered

---

## 9. Proposal coverage matrix (must stay 100%)

| Proposal area | Plan location | Status target |
| --- | --- | --- |
| Section 3 six roles | Roles + Phases 1–2 | Full |
| Section 4 modules 01–14 | Feature inventory + Phases 1–6 | Full |
| Section 5 six AI agents + controls | AI section + Phase 3 | Full |
| Section 6 mobile tenant/staff | Mobile section + Phase 4 | Full |
| Section 7 occupancy 10 features | Occupancy section + Phase 6 gated | Full after DPIA |
| Section 8 stack | Technology section | Full |
| Section 9 security/compliance | Security section + Phase 7 | Full |
| Section 10 7 phases | Delivery phases | Full |
| Section 11 optional add-ons | Section 10 below | Optional only |

---

## 10. Optional add-ons (Proposal Section 11 — not core)

These are not required to claim core HMore complete. Build only if the client selects and signs a separate scope.

- AI Voice Calling
- Safeguarding Alerts (urgent escalation with human review), if treated as enhanced beyond core incident escalation
- Rent & Tenancy Payments
- Training & Certification LMS
- Contractor Marketplace
- Digital ID & E-Signatures (advanced identity product beyond Module 12 e-sign)
- Benefits Navigator
- Gamified Development
- Integration Hub (deep council/HR/finance connectors)
- AI Knowledge Base (expanded policy KB beyond Tenant Assistant approved content)
- Finance & Budgets
- Council Portal (adds a seventh role; outside core)

---

## 11. Definition of Done (feature-level)

- Matches the exact proposal bullet(s) it claims
- Implemented on the proposal stack layers that own it
- Role permissions correct for all six roles
- Org isolation enforced
- Audit where the proposal requires visibility or control
- AI outputs require human approval when the action is important
- Tests prove allow and deny paths
- No silent fake success

---

## 12. Start command

Implement **PHASE 1 (Foundation)** from this plan.

Follow proposal v1.3 exactly. No feature substitutions.

Use Python FastAPI backend, Next.js web, Expo mobile, Postgres, and an Auth0/Entra MFA path.

Complete every Phase 1 exit check before Phase 2.

---

## Document control

HMore Proposal-Exact Complete Implementation Plan v1.0. Aligned 1:1 to Smart Vite Project Proposal v1.3 core scope. Product delivery name: HMore. Completing Phases 1–7 fully equals complete core HMore per the proposal. Section 11 remains optional.

Original PDF kept beside this file: `docs/HMore_Proposal_Exact_Implementation_Plan_v1.0.pdf`.
