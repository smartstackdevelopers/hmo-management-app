# Smart Vite Prototype — agent build spec

Source: `docs/Smart-Vite-Prototype-Complete.pdf` (50 screens, Smart Stack Developers, October 2026). Screens are matched to Smart Vite Project Proposal v1.3.

This file is what an agent uses to build the prototype. The PDF is the visual source. If this text and a screen disagree, follow the screen.

## What to build

A clickable prototype of one product on three surfaces:

- Web dashboard for Super Admin, Organisation Admin, and Landlord
- Tenant app (iOS and Android layout)
- Staff apps for Support Worker and Maintenance & Contractors

Use the sample data in this document. Every important screen must be reachable. A **Switch role** control on web returns to the sign-in role picker. Mobile uses bottom tabs.

This is a prototype of the drawn product. Do not add screens, roles, or modules that are not in the pack. Council Portal stays an optional add-on and is not a seventh role.

Visual system from the screens:

- Forest-green sidebar and mobile headers, teal primary buttons, warm off-white page background, white cards
- Rounded “SV” mark and the name **Smart Vite**
- Status chips: green success, amber warning, red danger, blue info, purple AI draft
- AI blocks are tinted and always show confidence, source, and a human action (approve, edit, dismiss, or report wrong)

## Demo people

| Person | Role | Where they land |
| --- | --- | --- |
| Priya Nair | Super Admin, platform owner | Web platform dashboard |
| Tom Walsh | Super Admin, MFA on | Listed on roles page |
| Amina Khan | Organisation Admin, Riverside Housing | Org dashboard. Sign-in email `amina.khan@riverside-housing.example`, password masked, MFA code `482 913` |
| David Okafor | Landlord | Properties |
| Ali Hassan | Tenant, Elm Road House Room 14 | Tenant app. Email `ali.h@example.com` |
| Jade Reid | Support Worker, early shift | Staff today screen |
| SafeHome Plumbing (`SP`) | Maintenance & Contractors | Work orders |

Sign-in note on the web form: sessions end after inactivity, and every sign-in is logged. Prototype shortcut: six role cards open that role without a real identity provider.

## Shared web shell

Left sidebar, top bar with search and the page’s primary action, content cards, footer with the signed-in person and **Switch role**.

Organisation Admin sidebar groups:

- Overview: Dashboard, Reports and analytics
- People: Tenants, Staff and caseloads, Support plans
- Housing: Applications, Evidence packs, Documents, Room occupancy
- Support: Jobs and skills, Community services, Wellbeing
- Operations: Repairs and complaints, Approvals and workflows, Communication, AI agents

Super Admin sidebar: Dashboard, Organisations, New organisation, AI and costs, Roles and access, Audit and health, Settings.

Landlord sidebar: Properties, Rooms and tenancies, Repairs and inspections.

## Screen index

| PDF page | Screen | Role |
| --- | --- | --- |
| 1 | Sign in and role picker | All |
| 2 | Platform dashboard | Super Admin |
| 3 | Organisations | Super Admin |
| 4 | New organisation | Super Admin |
| 5 | AI service and cost caps | Super Admin |
| 6 | Roles and access | Super Admin |
| 7 | Audit logs and system health | Super Admin |
| 8 | Platform settings | Super Admin |
| 9 | Org dashboard | Organisation Admin |
| 10 | Tenants | Organisation Admin |
| 11 | Tenant profile, Ali Hassan | Organisation Admin |
| 12 | Housing applications | Organisation Admin |
| 13 | Evidence pack, Grace Mensah | Organisation Admin |
| 14 | Documents | Organisation Admin |
| 15 | Staff and caseloads | Organisation Admin |
| 16 | Support plans | Organisation Admin |
| 17 | Jobs and skills | Organisation Admin |
| 18 | Community services | Organisation Admin |
| 19 | Repairs and complaints | Organisation Admin |
| 20 | Wellbeing | Organisation Admin |
| 21 | Approvals and workflows | Organisation Admin |
| 22 | Communication | Organisation Admin |
| 23 | Reports and analytics | Organisation Admin |
| 24 | Room occupancy board | Organisation Admin |
| 25 | Room detail, Dining hall | Organisation Admin |
| 26 | AI agents inbox | Organisation Admin |
| 27 | Properties | Landlord |
| 28 | Rooms and tenancies, Elm Road House | Landlord |
| 29 | Repairs and inspections | Landlord |
| 30 | Tenant app cover | Tenant |
| 31 | Tenant login | Tenant |
| 32 | Tenant home | Tenant |
| 33 | Tenant repairs | Tenant |
| 34 | Report a repair | Tenant |
| 35 | My plan | Tenant |
| 36 | Help Near Me | Tenant |
| 37 | Jobs and training | Tenant |
| 38 | Ask the assistant | Tenant |
| 39 | Profile and more | Tenant |
| 40 | Support Worker app cover | Support Worker |
| 41 | Today | Support Worker |
| 42 | Caseload | Support Worker |
| 43 | New note | Support Worker |
| 44 | Tasks | Support Worker |
| 45 | Room occupancy | Support Worker |
| 46 | Maintenance app cover | Maintenance |
| 47 | Work orders | Maintenance |
| 48 | Job detail | Maintenance |
| 49 | Schedule | Maintenance |
| 50 | Close: web, laptop, and mobile, one product | — |

## 1. Sign in (page 1)

Split layout. Left panel headline: “One secure place for housing, support and community.” Subcopy: tenant records, applications, repairs, room occupancy, and AI help for councils, housing associations, and supported-housing providers. Stats: 14 platform modules, 6 user roles, 3 platforms.

Right panel: Sign in with Work email, Password, Authentication code (MFA), and Sign in. Under it, “Prototype: open the app as a role.” The live product shows each person only their own role. The prototype can jump into any of the six:

- Super Admin — Platform and organisations (web)
- Organisation Admin — Approvals, reports, occupancy (web)
- Landlord — Properties and tenancies (web)
- Tenant — Mobile app
- Support Worker — Mobile app
- Maintenance & Contractors — Mobile app

## 2. Super Admin

### Platform dashboard (page 2)

Title “Platform dashboard”. Subtitle “All organisations · updated today 08:42”. Search organisations or users. Button **New organisation**.

Stats: Organisations 12 (2 onboarding). Active users this month 3,480 (+6%). Tenants on platform 5,912 (+112). AI spend this month US$41.60 (69% of US$60 combined cap).

Organisations table: Riverside Housing, housing association, 612 users, Active. Northbridge Council, council, 1,240, Near cap. Hearth Supported Living, supported housing, 388, Active. Elm Court Homes, housing association, 204, Active. Calder Valley Trust, supported housing, 36, Onboarding.

System health: API and web apps 99.98%. Database and backups, last backup 03:00. AI service healthy. Camera counters, 2 offline.

Needs attention: Northbridge Council has used 91% of its AI budget. 2 camera counters offline at Hearth Supported Living.

Chart: active users per week, W1–W8. AI cost by feature: Daily note summaries US$21.80, Tenant assistant US$12.30, Document checker US$5.10, Job matching and reports US$2.40.

### Organisations (page 3)

“12 organisations · each sees only its own data.” Filters: All 12, Councils 3, Housing associations 5, Supported housing 4, Onboarding 2.

| Organisation | Region | Admins | Staff | Tenants | Modules | AI cap | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Riverside Housing | North West England | 3 | 212 | 2,140 | 14 of 14 | US$10 | Active |
| Northbridge Council | Yorkshire | 6 | 480 | 1,860 | 12 of 14 | US$15 | Near AI cap |
| Hearth Supported Living | West Midlands | 2 | 96 | 292 | 14 of 14 | US$6 | Active |
| Elm Court Homes | London | 2 | 64 | 140 | 10 of 14 | US$5 | Active |
| Calder Valley Trust | Yorkshire | 1 | 12 | 24 | 8 of 14 | US$3 | Onboarding |
| St Mary’s Housing | South West England | 2 | 41 | 88 | 14 of 14 | US$4 | Suspended |

Note: rules differ by UK nation and council. Each organisation can configure its own forms, approval steps, and retention periods. Each row has Manage.

### New organisation (page 4)

1. Organisation details: Calder Valley Trust, Supported housing provider, UK nation England, local authority Calderdale.
2. First Organisation Admin: Hannah Briggs, `hannah.briggs@caldervalley.example`. Invitation with MFA is sent. This admin then invites all other users.
3. Modules switched on: Tenant management, Housing management, Staff management, Support plans, Jobs and skills, Community services, Maintenance and complaints, Approvals and workflows, Communication, Documents, Reports and analytics. Off: Wellbeing, Room occupancy, Optional Council Portal. Warning: room occupancy needs a site survey and a data-protection check (DPIA) before it can be switched on.
4. AI service: low-cost model environment, monthly budget US$3, when budget is reached pause AI features and keep rules. Pilot first: Notes Analysis and Smart Document Checker.

Summary card: organisation, housing region UK, modules 11 of 14, AI budget US$3 per month, data separation “own data only”, **Create organisation**. An audit log entry is written when the organisation is created.

### AI service and cost caps (page 5)

One shared service for all six agents. Low-cost model by default. October 2026. View AI logs.

Stats: AI spend US$41.60 (cap US$60 across all organisations). Model calls 186,420 (48% rules-first, no model). Cost per active user US$0.012, target under US$0.05. Premium model share 3.1%, review up from 2.4%.

Budgets: Northbridge Council US$15.05 cap, 15 used, Pause AI. Riverside Housing US$7.20 of 10. Hearth Supported Living US$2.28 of 6. Elm Court Homes US$1.05 of 5, healthy.

Agents toggles: Notes Analysis Live, Housing Application Live, Tenant Assistant Pilot, Support Planning Off, Compliance Off, Job Matching Off.

Model routing:

| Task | Runs on | Mode | Human review | Calls | Cost |
| --- | --- | --- | --- | --- | --- |
| Daily note summaries | Low-cost model | Overnight batch | Support worker confirms | 31,020 | US$21.80 |
| Tenant assistant chats | Low-cost model | On demand, cached policies | Approved content only | 9,800 | US$12.30 |
| Document gaps | OCR and rules, then low-cost model | On upload | Admin checks pack | 6,140 | US$5.10 |
| Hard cases and complaints review | Premium model | Escalation only | Always required | 410 | US$2.40 |
| Duplicates, overdue reminders, compliance checks | Database rules | Scheduled | Not needed | No AI call | US$0 |

### Roles and access (page 6)

Six roles only. Least-privilege access. Every change is logged. View access log.

Permission matrix. Values are Full, Own or assigned, or No access.

| Module | Super Admin | Org Admin | Landlord | Tenant | Support Worker | Maintenance |
| --- | --- | --- | --- | --- | --- | --- |
| Organisations and platform settings | Full | Own org | None | None | None | None |
| Tenant records | None | Full | Own tenancies | Own | Caseload | None |
| Housing applications and approvals | None | Full | View | Own | Assist | None |
| Support plans and notes | None | Full | None | Own | Caseload | None |
| Repairs and complaints | None | Full | Own properties | Report | Raise | Assigned |
| Room occupancy | None | Full | None | None | Permitted | None |
| Reports, compliance and audit logs | Platform | Full | Own | None | Own work | None |

Platform users: Priya Nair and Tom Walsh, both Super Admin, MFA on, Active. Invite Super Admin.

Safeguards: emergency access is time-limited, needs a reason, and is logged. Six roles are fixed. A seventh role (Council Portal) is an optional add-on only.

### Audit logs and system health (page 7)

Who saw or changed what, and when. Search. Export CSV.

Stats: uptime 99.98% (target 99.9%). Last backup 03:00, restore test passed 14 Oct. Failed sign-ins today 17, 3 locked accounts. Emergency access events 1, review required.

Filters: All, Sign-ins, Record views, AI activity, Camera data.

| Time | User | Action | Record | Organisation |
| --- | --- | --- | --- | --- |
| 09:12 | A. Khan (Org Admin) | Approved application | APP-2291 | Riverside |
| 09:04 | J. Reid (Support Worker) | Viewed tenant record | Tenant 0412 | Hearth |
| 08:57 | AI Notes Analysis | Drafted summary | Note 88,120 | Riverside |
| 08:41 | A. Khan (Org Admin) | Viewed room occupancy | Block B, Floor 2 | Hearth |
| 08:30 | T. Walsh (Super Admin) | Changed AI cap to US$15 | Northbridge | Platform |
| 08:02 | M. Clarke (Org Admin) | Emergency access, reason logged | Tenant 0097 | Northbridge |
| 07:48 | Sensor BLK-B-02 | No valid reading, alert sent | Room B-014 | Hearth |

Services: web dashboard, mobile API, database, job queue (0 delayed), and AI service healthy. Counter BLK-B-02 offline. Counter BLK-C-01 stale 25 min.

Data protection: encryption in transit and at rest Done. Breach-response plan Done. DPIA for Hearth occupancy cameras Open.

### Platform settings (page 8)

Defaults for every organisation. Each organisation can tighten them. Tabs: Security, Hosting and data, Notifications, Integrations, Branding. Save changes.

Security: require MFA for every user. Allow fingerprint or face unlock on mobile. Allow remote sign-out of lost devices. Session timeout 30 minutes. Login provider: managed identity service.

Hosting: region UK / EU. Backups daily, 35-day retention. Default record retention set per organisation. Camera history retention 90 days, counts only. No video is stored by default. Only people counts leave the device.

Responsible AI: human approval for important actions. Show sources and a confidence level on every answer. Log all AI activity. Allow staff to report wrong answers. AI is not used for employee surveillance or automatic punishments.

Integrations: email and SMS connected. Push notifications connected. Council, HR and finance APIs not enabled (Integration Hub add-on). Camera and sensor gateway per organisation (ONVIF and MQTT, per site).

## 3. Organisation Admin — Riverside Housing

Signed in as Amina Khan. Date on the dashboard: Thursday 29 October.

### Dashboard (page 9)

“Good morning, Amina.” Search tenants, cases, rooms. **Review approvals**.

Stats: occupancy 87% (312 of 358 rooms). Applications awaiting decision 24 (5 older than 14 days). Open repairs and complaints 31 (average fix time 3.2 days). Overdue reviews and documents 6 (compliance check flagged).

Approval queue:

| Case | Tenant | Type | Evidence | Waiting |
| --- | --- | --- | --- | --- |
| APP-2291 | Ali Hassan | New placement | Complete | 2 days |
| APP-2287 | Grace Mensah | Room transfer | 2 missing | 6 days |
| APP-2279 | Daniel Price | New placement | Complete | 9 days |
| APP-2260 | Sana Iqbal | Extension | ID expired | 16 days |

AI draft, needs review: weekly report draft is ready. 3 repairs are close to their deadline and 2 support plans have no review date. Confidence high. **Open draft**.

Alerts: sensor BLK-B-02 offline since 07:48. Gas safety certificate expires in 9 days, 14 Elm Road. Hearth block A reached 90% of capacity.

Occupancy by building: Elm Road House 46/52. Canal Street Block A 58/60. Millgate Court 70/96. Park View 138/150.

Complaints and repairs per week, last 8 weeks. Week 7 is highlighted.

### Tenants (page 10)

2,140 tenants. Every view is logged. **Add tenant**. Filters: All, New this month 38, Plan review due 42, Open repair 31, No support worker 7.

| Tenant | Property and room | Support worker | Next review | Flag |
| --- | --- | --- | --- | --- |
| Ali Hassan | Elm Road · Room 14 | Jade Reid | 12 Nov | Water leak |
| Grace Mensah | Canal Street A · Room 8 | Owen Blake | 3 Nov | Transfer request |
| Daniel Price | Millgate Court · Room 31 | Jade Reid | 20 Nov | |
| Sana Iqbal | Park View · Room 102 | Maria Costa | Overdue | ID expired |
| Liam Walker | Elm Road · Room 3 | Owen Blake | 8 Nov | |
| Fatima Ahmed | Canal Street A · Room 21 | Maria Costa | 15 Nov | AI: missing note detail |

Note: tenants only see their own record. Support workers see their caseload. Consent and contact preferences are stored on each profile.

### Ali Hassan profile (page 11)

Elm Road House · Room 14. Tenancy started 3 Sep 2026. Support worker Jade Reid. Badges: Active tenancy, Open repair: water leak, Goal: employment. Actions: Message, Open support plan.

Tabs: Overview and timeline, Support plan, Documents, Repairs, Messages.

Contact: phone 07700 900 412, email ali.h@example.com, preferred contact SMS then phone, language English and Arabic, data sharing consent given 3 Sep.

Needs and goals: employment support, independent living skills, ground floor room. Find a warehouse job 40%. Complete forklift training 10%.

Timeline, newest first:

- Today 08:10 repair ticket opened, water leak in Room 14. Suggested by AI, approved by A. Khan. Priority urgent.
- Yesterday 15:30 meeting notes by Jade Reid. AI summary reviewed: Ali wants warehouse work and has no CV yet. Reported a leak under the sink. Suggested actions: build CV, book forklift course, raise repair.
- Yesterday 15:45 employment goal added to support plan, J. Reid.
- 12 Sep document uploaded, proof of ID. Smart Document Checker: complete.
- 1 Sep application APP-2204 approved, A. Khan.

### Housing applications (page 12)

From application to move-in. Decisions are recorded with a reason. Tabs: Approval queue 24, Waiting list 63, Decision history, Vacancies 46.

Same queue as the dashboard, plus APP-2271 Rosa Delgado, new placement, 18 Oct, complete, sent to council. Stages include Ready to decide, Awaiting evidence, Sent to council.

Detail for APP-2291 Ali Hassan, new placement. AI checklist: all 6 documents received, no gaps, confidence high. Proof of ID valid to 2031. Referral letter received. Support needs assessment received. Decision note: meets criteria, ground floor room available at Elm Road. Actions: Approve, Request more, Decline. The software supports, but does not replace, the council’s statutory decision.

### Evidence pack (page 13)

APP-2287 Grace Mensah. Ask tenant for documents. Export pack for council is locked until all items are checked.

Checklist 4 of 6 ready:

- Proof of ID, passport valid to 2029, checked
- Proof of current address, tenancy agreement, checked
- Support needs assessment, completed by O. Blake, checked
- Reason for transfer statement, signed by tenant, checked
- Medical letter, not uploaded, missing
- Income evidence, payslip is 5 months old, out of date

Smart Document Checker: 2 documents need action before this pack is council-ready. Medical letter is absent. Income evidence should be from the last 3 months. Confidence high, based on OCR of 4 uploaded files.

Pack contents: cover sheet and case summary, checked documents (4), support worker statement. Include AI summary is optional and unchecked.

### Documents (page 14)

Private storage, version history, retention rules. Search documents or text inside them. Upload.

Stats: 18,240 stored. Expiring in 30 days: 37, reminders sent. Awaiting e-signature: 12. Access requests open: 2, due in 11 days.

| Document | Belongs to | Version | Expires | Checker |
| --- | --- | --- | --- | --- |
| Passport scan | Ali Hassan | v1 | 2031 | Valid |
| Tenancy agreement | Grace Mensah | v2 | Sep 2027 | Signed |
| Photo ID | Sana Iqbal | v1 | Expired 3 Oct | Replace |
| Gas safety certificate | 14 Elm Road | v4 | In 9 days | Renew |
| Payslip | Grace Mensah | v1 | n/a | Out of date |
| Support agreement | Liam Walker | v1 | Mar 2027 | Awaiting signature |

Filters: All, Expiring, Unsigned, AI flagged.

Retention: tenant records after tenancy ends 6 years. Rejected applications 12 months. Scheduled deletion this month 48.

Smart Document Checker found 1 possible duplicate upload, “Proof of address” for Daniel Price.

### Staff and caseloads (page 15)

Support workers and contractors. Workload is for fairness, not surveillance. Handover notes. Invite staff.

Stats: 38 support workers. Average caseload 11.4, target 12. Visits this week 412, 94% completed. Training due 9, 3 safeguarding.

| Support worker | Tenants | Notes this week | Overdue tasks | Training |
| --- | --- | --- | --- | --- |
| Jade Reid | 13 | 21 | 1 | Up to date |
| Owen Blake | 15 | 18 | 4 | Safeguarding |
| Maria Costa | 9 | 14 | 0 | Up to date |
| Kemal Pasha | 12 | 16 | 2 | Up to date |

Unassigned (7): Tariq Bashir, Elm Road, moved in 20 Oct. Nina Lewis, Park View, moved in 22 Oct. Peter Okoye, Millgate, moved in 25 Oct. Each has Assign.

Rota week of 26 October. E early, L late, N night, Off.

| Staff | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Jade Reid | E | E | L | L | E | Off | Off |
| Owen Blake | L | L | Off | E | E | E | Off |
| Maria Costa | Off | E | E | E | L | L | N |

### Support plans (page 16)

1,948 active plans. 42 reviews due. Progress report export. New plan.

Plans: Ali Hassan review 12 Nov, on track. Grace Mensah review 3 Nov, ahead. Sana Iqbal overdue, behind. Liam Walker review 8 Nov, on track.

Ali’s goals: Find a warehouse job (employment) — CV built, 2 applications sent, interview prep next. Complete forklift training — course found, funding form to complete. Learn to budget weekly (independent living) — 3 of 5 sessions done. Register with a GP (wellbeing) — completed 18 Oct.

Support Planning Agent draft: book a mock interview with Jade next week, add a weekly check-in on job applications, and review the budgeting goal at the November review. Accept, Edit, Dismiss.

Reviews: weekly review 26 Oct done. Monthly review 12 Nov booked.

### Jobs and skills (page 17)

Suggestions come from verified sources only. Manage sources. Export outcomes.

Stats: 612 tenants with an employment goal. 388 CVs built (+41 this month). 1,204 applications sent. 96 moved into work or training in the last 90 days.

Career Roadmap: 1 skills assessed 204, 2 CV ready 388, 3 applying 161, 4 in work or training 96.

Recent matches: Ali Hassan, warehouse operative at a local distribution centre, verified job board, strong, applied. Daniel Price, Level 2 Maths course, local college, strong, enrolled. Fatima Ahmed, care assistant trainee, NHS jobs, good, suggested.

Verified sources: national job service updated today. Local college courses updated 3 days ago. Employer partners check due.

Job Matching Agent: matches use search and embeddings first. AI is only used to write CV and interview tips.

### Community services (page 18)

Free local help shown to tenants in Help Near Me. Search services or postcode. Add service.

Stats: 214 verified listings. 58 food banks and kitchens. 24 clothing banks. 6 reported outdated, needs checking.

| Service | Type | Area | Opening hours | Eligibility | Checked |
| --- | --- | --- | --- | --- | --- |
| Riverside Food Bank | Food bank | M1 | Mon, Wed, Fri 10:00 to 14:00 | Referral | 12 Oct |
| Community Kitchen at St Anne’s | Kitchen | M4 | Daily 12:00 to 14:00 | Open to all | 20 Oct |
| Clothes Closet | Clothing bank | M2 | Tue and Thu 11:00 to 15:00 | Open to all | 3 Aug |
| Citizens Advice drop-in | Advice | M1 | Mon 09:30 to 12:30 | Open to all | 5 Oct |

Reported by tenants: Clothes Closet “Closed on Thursdays now”, 2 reports. Northside Pantry, phone number not working. Warm Space, Library, hours changed for winter. Each has Check.

Filters: All, Food, Clothing, Advice, Wellbeing.

### Repairs and complaints (page 19)

31 open. Search tickets, rooms, or tenants. New ticket.

Emergency banner: instructions are shown to tenants automatically for gas smell, fire, or flooding near electrics. The ticket is raised as urgent and contractors on call are alerted.

Columns: New 6, Assigned 9, In progress 7, Awaiting approval 9. Filters: Repairs 24, Complaints 7, Overdue 3, Escalated 2.

Cards:

- Water leak, Room 14, urgent. Ali Hassan, Elm Road. AI suggested, approved. Due today 17:00.
- Broken window lock, high. Grace Mensah, Canal St A. Due 31 Oct.
- Heating not working, high. Daniel Price, Millgate. Contractor Northern Heat, 30 Oct.
- Damp in bathroom, normal. Sana Iqbal, Park View. Contractor SafeHome, 3 Nov.
- Replace smoke alarm, high. Liam Walker, Elm Road. Started today.
- Noise complaint, Floor 2. Escalated to manager. Overdue 2 days.
- Kitchen tap replaced, done. Photos and proof uploaded. Approve job.
- Door repaired, done. Photos and proof uploaded. Approve job.

### Wellbeing (page 20)

Self-care resources and check-ins. A support tool, not a clinical tool. Add resource. Send wellbeing reminder.

Banner: check-in answers belong to the tenant. Staff only see them where the tenant has agreed, and urgent concerns are always reviewed by a person.

Stats: 1,126 check-ins this week. 540 tenants using the routine planner. 86 resources. 14 check-ins flagged for follow-up, support worker notified.

Library: 10-minute morning stretch, exercise video, English and Urdu, 412 views, published. Breathing for calm evenings, audio, English, 368, published. Sleep routine guide, article, English and Arabic, 201, published. Local mental health services, directory, English, 158, check listings.

Weekly mood chart shows totals only: Low, Fair, Okay, Good, Great. No individual answers on this page.

Support Navigator points tenants to approved services. It never diagnoses or gives medical advice.

### Approvals and workflows (page 21)

Custom forms, approval steps, and decision history. Tabs: Workflows, Forms, Decision history, Secure sharing. New form. New workflow.

New placement approval, active, five steps: application received, evidence check, Organisation Admin decision, council-ready export, move-in.

Other workflows: room transfer, 4 steps, 3 in progress, active. Complaint escalation, 3 steps, 2 in progress, active. Tenancy extension, 3 steps, draft.

Recent decisions: APP-2271 Rosa Delgado approved by A. Khan 27 Oct. APP-2265 Marcus Bell more evidence requested 24 Oct, on hold. APP-2259 Emeka Obi declined with reason 21 Oct.

### Communication (page 22)

In-app messages, push, email, and SMS. Tabs: Compose, Inbox 8, Scheduled reminders, Sent. Send.

New announcement to all tenants at Elm Road House (52). Type: routine notice. Subject: Water shut-off on Friday, 9:00 to 12:00. Message: the water supply to Elm Road House will be off on Friday between 9:00 and 12:00 while the leak on the ground floor is fixed. Please store water if you need it. Channels checked: in-app, push, SMS. Email unchecked.

Translation: also send in Arabic, Urdu, Polish. Tenants receive their preferred language.

Inbox: Ali Hassan, “Is the plumber coming today?”, new. Grace Mensah, “I have uploaded my payslip.” Jade Reid, handover note for Monday.

Scheduled reminders: plan review reminders daily 06:00. Document expiry notices 30 days before. Weekly report draft Monday 07:00.

### Reports and analytics (page 23)

Clear numbers for managers. Export as PDF, CSV, or Excel. Schedule report. Export.

Plain-language search example: “show open water complaints this month”.

Stats: occupancy 87% (+2 points). Average complaint response 1.4 days, target 2 days. Applications sent complete first time 78% (+9 points). Support plan goals completed 64%.

Applications per month, May to October 2026, rising.

Early-warning alerts: complaints about heating up 40% in Millgate Court. Owen Blake’s caseload is 96% of target. 6 plan reviews are overdue.

Report library:

| Report | Covers | Schedule | Recipients | Format |
| --- | --- | --- | --- | --- |
| Weekly management summary | Occupancy, applications, complaints | Mondays 07:00 | 3 admins | AI draft, PDF |
| Caseload and workload | Support workers | Monthly | 2 admins | Excel |
| Plan completion and outcomes | Goals, jobs, training | Monthly | Council | PDF |
| Compliance and overdue items | Reviews, documents, inspections | Weekly | 1 admin | CSV |

### Room occupancy (page 24)

Estimated people counts in communal areas. Counts only, no faces, no video stored. Usage history. Export.

Building Canal Street Block A, floor Ground floor. Legend: Available, Occupied, Near capacity, At capacity, Offline.

Stats: 47 people counted now, estimated, updated 09:14. 12 rooms monitored. 2 at or near capacity, alerts sent. 1 sensor offline, alert sent 07:48.

| Room | Count | Status | Updated |
| --- | --- | --- | --- |
| Common room | 12 / 20 | Occupied | 09:14 |
| Dining hall | 17 / 20 | Near capacity | 09:14 |
| Activity room | 10 / 10 | At capacity | 09:13 |
| Quiet lounge | 0 / 8 | Available | 09:14 |
| Laundry | 1 / 6 | Available | 09:12 |
| Main entrance | No reading | Offline | 07:48 |
| Corridor G1 | 4 / 12 | Occupied | 09:14 |
| Training room | 0 / 14 | Available | 09:14 |

Communal areas only. Bedrooms, bathrooms, and changing rooms are never monitored by camera. Everyone who views this page is logged.

### Dining hall detail (page 25)

17 people estimated, of 20 maximum, last update 09:14. Capacity bar 85% full. Alert sent at 80% and again at 100%. Device Counter BLK-A-03. Counts on the device. Only the number is sent, never video.

Today by hour chart, hours 7 to 17, with 12 highlighted. Toggles: Today, 7 days, 30 days.

Correct the count: actual people 15, reason “Counted at door”, Save correction. Use only if the estimate is clearly wrong. The change is saved with name and reason.

Alert settings: near capacity at 80%. Notify Org Admin and notify on-shift Support Worker.

Access log: 09:14 Amina Khan viewed room count. 08:52 Jade Reid viewed room count. Yesterday 18:30 Owen Blake corrected count 22 to 19, reason counted at door.

### AI agents (page 26)

Drafts and suggestions waiting for a person. Nothing important happens without approval. Low-cost model badge. AI activity log.

Stats: 11 waiting for review. 86% accepted this week. 2 wrong answers reported, under review. AI spend this month US$7.20, 72% of the US$10 cap.

Notes Analysis summary, confidence high: Ali Hassan meeting on 28 Oct. Wants warehouse work, no CV yet, reported a leak under the sink. Missing detail: how long the leak has been present. Source: note 88,120 by Jade Reid. Approve, Edit, Report wrong answer.

Housing Application gaps, confidence high: APP-2287 Grace Mensah. Medical letter missing. Payslip is over 3 months old. Open evidence pack. Ask tenant.

Compliance overdue: 6 overdue plan reviews and 1 gas certificate expiring in 9 days. No AI call was needed to find these. Open reviews. Label: rules check.

Agent states: Notes Analysis live, overnight batch. Housing Application live. Tenant Assistant pilot, approved content only. Support Planning off, when a plan is opened. Compliance live, scheduled rules. Job Matching off, search and embeddings.

Warning: AI is not used for staff surveillance or automatic punishments. If AI could affect housing or employment decisions, legal risks are assessed separately.

## 4. Landlord — David Okafor

Landlords see their own properties, rooms, tenancies, and repair status. Tenant support notes are not visible to landlords.

### Properties (page 27)

4 properties, 118 rooms. Search. Add property.

Stats: 118 rooms. Occupied 104 (88%). Vacant now 14. Inspections due in 30 days: 3, 1 gas certificate.

| Property | Address | Rooms | Vacant | Open repairs | Next inspection |
| --- | --- | --- | --- | --- | --- |
| Elm Road House | 14 Elm Road | 52 | 6 | 4 | Gas cert. in 9 days |
| Canal Street Block A | 2 Canal Street | 30 | 2 | 2 | 12 Dec |
| Millgate Court | 8 Millgate | 24 | 5 | 1 | 20 Jan |
| Park View annexe | Park View Road | 12 | 1 | 0 | 4 Feb |

### Elm Road rooms (page 28)

52 rooms, 46 occupied, 6 vacant, rent collected this month 96%. Tabs: Rooms and tenancies, Rent records, Inspections, Documents. Repairs. Add room.

| Room | Floor | Status | Tenant | Start | Rent | Rent status |
| --- | --- | --- | --- | --- | --- | --- |
| Room 3 | Ground | Occupied | Liam Walker | 14 Jun 2026 | £118 / week | Paid |
| Room 8 | Ground | Vacant | None | n/a | £118 / week | n/a |
| Room 14 | First | Occupied | Ali Hassan | 3 Sep 2026 | £118 / week | Paid |
| Room 15 | First | Occupied | Tariq Bashir | 20 Oct 2026 | £118 / week | Due Friday |
| Room 22 | Second | Under repair | None | n/a | £118 / week | n/a |
| Room 27 | Second | Occupied | Nina Lewis | 22 Oct 2026 | £118 / week | 1 week late |

Rent and tenancy records are an optional add-on in the full product. Tenant names are shown only for tenancies at this landlord’s properties.

### Repairs and inspections (page 29)

Open repairs 7. Urgent 1, water leak Elm Road. Completed this month 22. Average fix time 3.2 days. Schedule inspection.

| Issue | Place | Priority | Contractor | Due | Status |
| --- | --- | --- | --- | --- | --- |
| Water leak under sink | Elm Road · Room 14 | Urgent | SafeHome Plumbing | Today | Assigned |
| Broken window lock | Canal St A · Room 8 | High | To be assigned | 31 Oct | New |
| Heating not working | Millgate · Room 31 | High | Northern Heat | 30 Oct | Assigned |
| Replace smoke alarm | Elm Road · Room 3 | High | Spark Electrical | Today | In progress |
| Kitchen tap replaced | Elm Road · Kitchen | Normal | SafeHome Plumbing | Done | Awaiting approval |

Inspections: gas safety, 14 Elm Road, due in 9 days, book. Fire alarm test, Canal St A, 12 Dec, booked. Electrical check, Millgate, 20 Jan, planned.

Repair approvals are made by the Organisation Admin. The landlord can see progress and photos of finished work.

## 5. Tenant app — Ali Hassan

Cover (page 30): home, repairs with photos, support plan, Help Near Me, jobs and training, documents, notifications, and the tenant AI assistant. Biometric unlock and remote sign-out. React Native, one codebase. Offline-ready drafts sync when the phone is back online. Privacy first: own records only, every view logged.

Tabs: Home, Repairs, My plan, Help, More.

### Login (page 31)

“Your home, your plan, your support.” Email, password, Sign in, Use fingerprint or face, Forgot password, Language and accessibility.

### Home (page 32)

Hello, Ali. Elm Road House · Room 14. Next appointment Tue 3 Nov, mock interview with Jade, 10:30, support office, ground floor.

Shortcuts: Report a repair, My plan (2 goals this week), Help Near Me, Jobs and training (3 new for you).

Water leak, Room 14. Plumber booked today between 12:00 and 16:00, progress bar.

Ask the assistant: questions about tenancy, repairs, or support. Answers come from approved information.

### Repairs (page 33)

Report a new repair. Emergency strip: gas smell, fire, or flooding near electrics — leave the room, call 999 or the gas emergency line, then report it here.

Open 2, Done 5.

- Water leak, Room 14, urgent, reported today 08:05. Timeline: plumber booked today 12:00 to 16:00, approved by housing team today 08:10, reported by you today 08:05.
- Loose cupboard door, normal, reported 22 Oct, due 5 Nov.
- Kitchen tap dripping, done, fixed 14 Oct, photo proof added. Rate this repair.

### Report a repair (page 34)

Categories: Plumbing (selected), Heating, Electrics, Doors and windows, Damp, Other. Where: My room (Room 14). Description: water leaking under the sink, started this morning. Take photo or choose photo. Send report. The housing team checks this and a contractor is booked. A notification is sent at each step.

### My plan (page 35)

On track. Review 12 Nov. Goals match the web support plan: warehouse job 40%, forklift training 10%, budget weekly 60% (3 of 5 sessions with Jade), GP registration completed 18 Oct.

Support Planning Agent draft: book mock interview with Jade, then add a weekly job-application check-in. The tenant sees the draft. They do not apply it themselves.

### Help Near Me (page 36)

Free local services near M1. Search postcode or service. Filters All, Food, Clothes, Advice.

- Riverside Food Bank, 0.4 mi, Mon Wed Fri 10:00–14:00, referral needed
- Community Kitchen, 0.7 mi, daily 12:00–14:00, open to all, St Anne’s
- Clothes Closet, check hours, Tue and Thu 11:00–15:00, 2 outdated reports
- Citizens Advice drop-in, 1.1 mi, Mon 09:30–12:30, open to all

Report outdated listing.

### Jobs and training (page 37)

Career roadmap step 3, Applying, 2 live apps. Warehouse operative, local distribution centre, applied yesterday, strong match. Forklift Level 2 course, local college, form ready to complete, funding open. Interview prep tips, AI draft, approved content, Jade can review with you.

Job Matching Agent: search and embeddings first. AI only writes CV and interview tips.

### Ask the assistant (page 38)

Answers from approved information only.

User: When is the plumber coming for my water leak? Assistant, confidence high: SafeHome Plumbing is booked today between 12:00 and 16:00 for Room 14. You will get a push when they are on the way. Source: repair ticket REP-4412.

User: Can you find a food bank near me? Riverside Food Bank is 0.4 miles away, open Mon/Wed/Fri 10:00–14:00. Referral needed. Open Help Near Me for directions.

Footer: not used for housing decisions without a person.

### Profile and more (page 39)

Documents, 4 files (ID, tenancy, certificates). Notifications, 3 new. Appointments, mock interview Tue 3 Nov. Language and accessibility, English, large text available. Security, fingerprint / face unlock on, MFA. Sign out this device. Lost phone? Ask housing staff for remote sign-out.

## 6. Support Worker app — Jade Reid

Cover (page 40): caseload, visits, voice notes, AI summaries with human approval, tasks, incidents, and permitted room-occupancy counts. Built for shifts, not surveillance. Voice notes use on-device speech first, then optional rewrite. AI review: nothing important without a person. Rooms: estimated counts only, access logged.

Tabs: Today, Tenants, New note, Tasks, Rooms.

### Today (page 41)

Jade Reid, early shift. Visits 5, 2 done. Tasks due 3, 1 overdue. Next visit 10:30, Ali Hassan mock interview, support office, ground floor.

Handover from night, unread: Room 14 leak booked. Grace Mensah waiting on medical letter.

Offline drafts, 1 ready: note for Liam Walker will sync on Wi-Fi.

Notes Analysis overnight: 2 summaries waiting for review before they go on the record.

### Caseload (page 42)

13 tenants. Every view is logged. Search name or room.

Ali Hassan, Elm Road Room 14, repair. Daniel Price, Millgate Room 31, visit today. Liam Walker, Elm Road Room 3, plan ok. Fatima Ahmed, Canal Street A Room 21, missing detail. Tariq Bashir, Elm Road Room 15, new.

### New note (page 43)

Voice ready. Tenant Ali Hassan, Room 14. Visit type: Support meeting, Home visit, or Incident. Notes: Ali wants warehouse work. No CV yet. Reported water leak under the sink this morning. Follow up on forklift funding form.

Hold to dictate (on-device speech).

Notes Analysis draft: employment goal plus urgent repair. Missing: how long the leak has been present. Approve, Edit, Report wrong.

Save offline, or Save and sync.

### Tasks (page 44)

Book mock interview with Ali, today, suggested by AI, you confirmed. Chase medical letter for Grace, due Friday, evidence pack APP-2287 incomplete. Safeguarding refresher, overdue, also due for Owen Blake. Weekly plan reviews, 2 left, Ali Hassan and Liam Walker. Report an incident.

### Room occupancy (page 45)

Canal Street Block A now: 47 people estimated, updated 09:14. Dining hall 17/20 near capacity. Activity room 10/10 at capacity. Quiet lounge 0/8 available. Main entrance no valid reading, offline.

No facial recognition. Bedrooms and bathrooms are never monitored by camera.

## 7. Maintenance & Contractors — SafeHome Plumbing

Cover (page 46): assigned work orders, schedules, photo proof, and status updates. Organisation Admin approves finished jobs. Work orders, photo proof in private versioned storage, and emergency gas / fire / flood instructions.

Tabs: Orders, Schedule, Photos, Profile, More.

### Work orders (page 47)

SafeHome Plumbing, today. Filters: Assigned, In progress, Done.

- Water leak under sink, urgent, due 17:00, Elm Road House Room 14, Ali Hassan
- Kitchen tap replaced, awaiting approval, Elm Road, photos uploaded
- Damp in bathroom, Park View Room 102, 3 Nov

Emergency protocol: gas smell, fire, or flood near electrics — leave the room, call 999 / gas emergency, then update the ticket.

### Job detail (page 48)

Water leak, Room 14, urgent. Location Elm Road House Room 14. Tenant on site, access 12:00–16:00. Issue: water leaking under kitchen sink. Priority raised by AI suggestion, approved by A. Khan.

Add proof: take photo or choose photo. Notes for admin: replaced trap and washer. Tested, no drip. Area dried. **Mark complete · send for approval**. Photos stay in private storage. The tenant sees status updates.

### Schedule (page 49)

Thursday 29 October.

- 12:00–16:00 water leak, Elm Road Room 14, urgent
- Tomorrow AM heating check, Millgate Room 31, assigned
- 3 Nov damp survey, Park View Room 102, planned

Same emergency protocol as the work-order list.

## 8. Close (page 50)

Web, laptop, and mobile are one product. This pack covers Super Admin, Organisation Admin, and Landlord on the web dashboard, plus Tenant, Support Worker, and Maintenance apps for iOS and Android, aligned to proposal v1.3. 6 roles, 14 modules, 3 platforms.

## Agent rules

- Reproduce these screens and this sample data. Do not invent a different dashboard, extra roles, or a Council Portal.
- Keep Smart Vite as the name on the prototype UI.
- AI output is always a draft until a person approves, edits, or dismisses it. Show source and confidence.
- Rules and search run before a model call. Duplicates, expiry, and overdue items are rules, not model calls.
- Room occupancy shows estimated counts in communal rooms only. No faces, no identity, no stored video, and every view is logged.
- Each organisation’s data stays separate. Landlords do not see support notes. Tenants see only their own record. Support workers see their caseload.
- Emergency gas, fire, and flood-near-electrics copy appears for tenants and contractors exactly as written on the screens.
- Wellbeing and Support Navigator are not clinical tools and do not diagnose.
- The web app is the primary surface for Super Admin, Organisation Admin, and Landlord. Tenant, Support Worker, and Maintenance use the mobile layouts.
