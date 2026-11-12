/**
 * F7.7 route/feature matrix for release reporting (static inspection).
 * Both tenant and staff journeys live in the unified Expo app (`room-ready`).
 */

export const TENANT_RELEASE_FEATURES = [
  { id: 'login_profile', routes: ['/(auth)/login', '/(app)/(tabs)/settings'] },
  { id: 'housing', routes: ['/(app)/(tabs)/tenancy'] },
  { id: 'maintenance_photos', routes: ['/(app)/maintenance/new', '/(app)/(tabs)/maintenance'] },
  { id: 'support_plans', routes: ['/(app)/(tabs)/support'] },
  { id: 'community_services', routes: ['/(app)/help-near-me', '/(app)/community-hub'] },
  { id: 'employment_jobs', routes: ['/(app)/employment', '/(app)/job-matching'] },
  { id: 'documents', routes: ['/(app)/documents'] },
  { id: 'notifications', routes: ['/(app)/notifications'] },
  { id: 'assistant', routes: ['/(app)/assistant'] },
  { id: 'accessibility', routes: ['/(app)/accessibility'] },
] as const;

export const STAFF_RELEASE_FEATURES = [
  { id: 'caseload', routes: ['/(app)/(tabs)/caseload', '/(app)/staff/case/[tenantId]'] },
  { id: 'shifts', routes: ['/(app)/(tabs)/shifts'] },
  { id: 'daily_notes_voice', routes: ['/(app)/(tabs)/notes'] },
  { id: 'visits_tasks', routes: ['/(app)/staff/visits', '/(app)/staff/tasks'] },
  { id: 'work_orders', routes: ['/(app)/staff/work-order/[id]', '/(app)/(tabs)/work-orders'] },
  { id: 'incidents', routes: ['/(app)/staff/incidents'] },
  { id: 'approvals', routes: ['/(app)/staff/approvals'] },
  { id: 'occupancy_gated', routes: ['/(app)/staff/occupancy'] },
  { id: 'offline_drafts', routes: ['/(app)/offline-drafts'] },
  { id: 'device_security', routes: ['/(app)/security'] },
] as const;
