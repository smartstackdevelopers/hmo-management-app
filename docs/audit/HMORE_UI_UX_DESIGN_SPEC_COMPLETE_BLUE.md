# HMore — UI/UX Design Specification (Mobile + Web, all roles) — Blue & White edition

PDF: `docs/audit/HMORE_UI_UX_DESIGN_SPEC_COMPLETE_BLUE.pdf` · 60 mobile + 44 web screens.
Images: `docs/audit/_pdf_export/ui_spec_images_blue/` · Generator: `docs/audit/_pdf_export/build_ui_ux_design_spec_pdf.py` (run with `HMORE_THEME=blue`)

## Screen index

| ID | Screen | Platform | Role / module | Primary action / route |
| --- | --- | --- | --- | --- |
| M-AU-01 | Welcome | Mobile | Authentication & onboarding | Create account |
| M-AU-02 | Create account | Mobile | Authentication & onboarding | Request access |
| M-AU-03 | Pending approval | Mobile | Authentication & onboarding | Back to sign in |
| M-AU-04 | Sign in | Mobile | Authentication & onboarding | Sign in |
| M-AU-05 | Sign in · error | Mobile | Authentication & onboarding | Retry sign in |
| M-AU-06 | Reset password | Mobile | Authentication & onboarding | Send reset link |
| M-TN-01 | Home | Mobile | Tenant | Report repair |
| M-TN-02 | My home | Mobile | Tenant | Contact landlord |
| M-TN-03 | Repairs | Mobile | Tenant | Report repair |
| M-TN-04 | Report a repair | Mobile | Tenant | Continue / Submit |
| M-TN-05 | Support | Mobile | Tenant | Open appointment |
| M-TN-06 | Account | Mobile | Tenant | Open section |
| M-LL-01 | Portfolio home | Mobile | Landlord | Add property |
| M-LL-02 | Properties | Mobile | Landlord | Open property |
| M-LL-03 | Property detail | Mobile | Landlord | Manage rooms |
| M-LL-04 | Add property | Mobile | Landlord | Continue |
| M-LL-05 | Compliance | Mobile | Landlord | Upload certificate |
| M-LL-06 | Messages | Mobile | Landlord | Send message |
| M-SW-01 | Today | Mobile | Support Worker | Start visit |
| M-SW-02 | My tenants | Mobile | Support Worker | Open tenant |
| M-SW-03 | Tenant case | Mobile | Support Worker | Add daily log |
| M-SW-04 | Shifts | Mobile | Support Worker | Open visit |
| M-SW-05 | Daily log | Mobile | Support Worker | Save log |
| M-SW-06 | Incident report | Mobile | Support Worker | Submit incident |
| M-CT-01 | Today | Mobile | Maintenance Contractor | Start route |
| M-CT-02 | Work orders | Mobile | Maintenance Contractor | Open job |
| M-CT-03 | Job detail | Mobile | Maintenance Contractor | Start job |
| M-CT-04 | Schedule | Mobile | Maintenance Contractor | Open job |
| M-CT-05 | Photo evidence | Mobile | Maintenance Contractor | Submit for sign-off |
| M-CT-06 | Account | Mobile | Maintenance Contractor | Open section |
| M-OA-01 | Overview | Mobile | Organisation Admin | Review approvals |
| M-OA-02 | Approvals | Mobile | Organisation Admin | Approve |
| M-OA-03 | Alerts | Mobile | Organisation Admin | Acknowledge |
| M-SA-01 | Platform dashboard | Mobile | Super Admin | View status |
| M-SA-02 | Users | Mobile | Super Admin | Open user |
| M-SA-03 | Platform | Mobile | Super Admin | Open section |
| M-MS-01 | Inbox | Mobile | Shared modules | Open thread |
| M-MS-02 | Conversation | Mobile | Shared modules | Send |
| M-MS-03 | Notifications | Mobile | Shared modules | Open item |
| M-DC-01 | My files | Mobile | Shared modules | Upload |
| M-DC-02 | Upload document | Mobile | Shared modules | Upload |
| M-DC-03 | Document detail | Mobile | Shared modules | Open PDF |
| M-CM-01 | Community hub | Mobile | Shared modules | Open map |
| M-CM-02 | Help near me | Mobile | Shared modules | Open service |
| M-CM-03 | Service detail | Mobile | Shared modules | Get directions |
| M-EM-01 | Employment home | Mobile | Shared modules | Continue CV |
| M-EM-02 | Job search | Mobile | Shared modules | Open job |
| M-EM-03 | Job detail | Mobile | Shared modules | Apply |
| M-WB-01 | Wellbeing home | Mobile | Shared modules | Check in |
| M-WB-02 | Daily check-in | Mobile | Shared modules | Save check-in |
| M-WB-03 | History | Mobile | Shared modules | Open day |
| M-IN-01 | Inspections | Mobile | Shared modules | Open inspection |
| M-IN-02 | Schedule inspection | Mobile | Shared modules | Schedule |
| M-IN-03 | Room listing | Mobile | Shared modules | Manage listing |
| M-ST-01 | Accessibility | Mobile | Shared modules | Save automatically |
| M-ST-02 | Privacy & security | Mobile | Shared modules | Open section |
| M-ST-03 | Assistant | Mobile | Shared modules | Ask |
| M-GS-01 | Empty state | Mobile | Global states | Primary next step |
| M-GS-02 | Error state | Mobile | Global states | Try again |
| M-GS-03 | Offline state | Mobile | Global states | View drafts |
| W-AU-01 | Sign in | Web | Authentication | /login |
| W-AU-02 | Request access | Web | Authentication | /register |
| W-AU-03 | Request pending | Web | Authentication | /register/pending |
| W-SA-01 | Platform dashboard | Web | Super Admin | /dashboard/super-admin |
| W-SA-02 | Organisations | Web | Super Admin | /dashboard/super-admin/organisations |
| W-SA-03 | Registration approvals | Web | Super Admin | /dashboard/approvals/registrations |
| W-SA-04 | Audit logs | Web | Super Admin | /dashboard/audit |
| W-SA-05 | Platform settings | Web | Super Admin | /dashboard/platform-admin |
| W-SA-06 | AI feature flags | Web | Super Admin | /dashboard/ai-feature-flags |
| W-OA-01 | Organisation dashboard | Web | Organisation Admin | /dashboard/organisation-admin |
| W-OA-02 | Approvals & workflows | Web | Organisation Admin | /dashboard/org-workflows |
| W-OA-03 | Case assignments | Web | Organisation Admin | /dashboard/case-assignments |
| W-OA-04 | Rota | Web | Organisation Admin | /dashboard/rota |
| W-OA-05 | Reports | Web | Organisation Admin | /dashboard/reports |
| W-LL-01 | Landlord dashboard | Web | Landlord | /dashboard/landlord |
| W-LL-02 | Properties | Web | Landlord | /properties |
| W-LL-03 | Property detail | Web | Landlord | /properties/48-park-road |
| W-LL-04 | Rent payments | Web | Landlord | /dashboard/rent-payments |
| W-LL-05 | Maintenance board | Web | Landlord | /dashboard/maintenance |
| W-SW-01 | Caseload dashboard | Web | Support Worker | /dashboard/support-worker |
| W-SW-02 | Tenant case | Web | Support Worker | /dashboard/caseload/sara-ahmed |
| W-SW-03 | New daily log | Web | Support Worker | /dashboard/daily-logs/new |
| W-SW-04 | Visits calendar | Web | Support Worker | /dashboard/visits |
| W-SW-05 | Safeguarding alerts | Web | Support Worker | /dashboard/safeguarding-alerts |
| W-SW-06 | Handovers | Web | Support Worker | /dashboard/handovers |
| W-CT-01 | Job marketplace | Web | Maintenance Contractor | /dashboard/contractor-marketplace |
| W-CT-02 | Job detail | Web | Maintenance Contractor | /dashboard/maintenance/wo-482 |
| W-CT-03 | Schedule | Web | Maintenance Contractor | /dashboard/contractor-schedule |
| W-TN-01 | Tenant overview | Web | Tenant (web access) | /account |
| W-TN-02 | My repairs | Web | Tenant (web access) | /dashboard/maintenance |
| W-TN-03 | Rent payments | Web | Tenant (web access) | /dashboard/rent-payments |
| W-MD-01 | Communications inbox | Web | Shared modules | /dashboard/communications/inbox |
| W-MD-02 | Documents | Web | Shared modules | /dashboard/documents |
| W-MD-03 | Community directory | Web | Shared modules | /dashboard/community-directory |
| W-MD-04 | Add community service | Web | Shared modules | /dashboard/community-directory/new |
| W-MD-05 | Housing applications | Web | Shared modules | /dashboard/housing-applications |
| W-MD-06 | Complaint detail | Web | Shared modules | /dashboard/complaints/c-104 |
| W-MD-07 | Incidents | Web | Shared modules | /dashboard/incidents |
| W-MD-08 | Finance | Web | Shared modules | /dashboard/finance |
| W-MD-09 | Automation | Web | Shared modules | /dashboard/automation |
| W-MD-10 | Integrations | Web | Shared modules | /dashboard/integrations |
| W-MD-11 | Learning (LMS) | Web | Shared modules | /dashboard/lms |
| W-MD-12 | AI activity | Web | Shared modules | /dashboard/ai-activity |
| W-MD-13 | Global states | Web | Shared modules | /properties |
