# Phase 5 | F5.6 Tenant Mobile and Community Integration

## Purpose

Provide one organised Community entry point in the HMore Tenant Mobile App for:

- F5.1 Community Directory
- F5.2 Help Near Me
- F5.3 Skills / CV / applications
- F5.4 Job Matching
- F5.5 Wellbeing

## Architecture

- Route catalogue: `room-ready/lib/hmore/phase5Navigation.ts`
- Live summary formatters: `room-ready/lib/hmore/communityHubSummary.ts`
- Hub screen: `room-ready/app/(app)/community-hub.tsx`
- Entry points: Tenant Home card + Account → Community and career
- Existing module screens and FastAPI endpoints are reused (no duplicate Community backends)

## Privacy

- Wellbeing mood/notes appear only inside tenant-private wellbeing flows / hub summaries for the signed-in tenant.
- Tenant Home does not display mood or check-in details.
- Wellbeing data must not drive job ranking or tenancy decisions.

## Offline and notifications

- Reuses F4.5 offline drafts for permitted repair/staff drafts.
- Community hub shows connectivity status and links to Offline drafts.
- Routine reminders and other tenant notifications continue via F4.3.

## Non-goals

- No Phase 6 / Phase 7 work
- No second notification or sync engine
- No invented directory, job or wellbeing records
