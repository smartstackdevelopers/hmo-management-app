export interface AuthMe {
  id: string;
  external_subject: string;
  email: string | null;
  display_name: string | null;
  authorization_version: number;
  token_sub?: string | null;
}

export interface RbacMembership {
  id: string;
  role: string;
  organisation_id: string | null;
  status: string;
}

export interface RbacMe {
  user_id: string;
  external_subject: string;
  authorization_version: number;
  active_role: string | null;
  active_organisation_id: string | null;
  memberships: RbacMembership[];
  permissions: string[];
  session?: Record<string, unknown>;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface Tenant {
  id: string;
  organisation_id: string;
  user_id: string | null;
  preferred_name: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  tenancy_reference: string | null;
  consent_notes: string | null;
  consent_given_at: string | null;
  preferences: string | null;
  needs_goals: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

/** GET/PATCH /tenant/me. Notes, consent notes, and needs/goals are not returned. */
export interface TenantSelf {
  id: string;
  organisation_id: string;
  user_id: string | null;
  preferred_name: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  tenancy_reference: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AssignedProperty {
  id: string;
  name: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  postcode: string;
}

export interface AssignedRoom {
  id: string;
  label: string;
  floor_label: string | null;
}

export interface TenantHousing {
  tenancy_reference: string | null;
  status: string;
  property: AssignedProperty | null;
  room: AssignedRoom | null;
}

export interface CommunityServiceItem {
  id: string;
  category: string;
  name: string;
  description: string | null;
  address_line: string | null;
  opening_days?: string | null;
  opening_hours: string | null;
  eligibility: string | null;
  referral_requirements?: string | null;
  contact: string | null;
  service_instructions?: string | null;
  clothing_service_type?: string | null;
  verification_status?: string;
  information_source?: string | null;
  verified_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  is_published?: boolean;
}

export interface OpportunityItem {
  id: string;
  kind: string;
  title: string;
  description: string | null;
  eligibility: string | null;
  source_name: string | null;
  source_url: string | null;
  is_published?: boolean;
}

export interface MaintenanceRequest {
  id: string;
  reference_number: string;
  title: string;
  description: string;
  category_code: string;
  priority: string;
  status: string;
  property_id: string;
  room_id: string | null;
  tenant_id: string | null;
  reported_by_user_id: string | null;
  assigned_user_id: string | null;
  requires_approval: boolean;
  approval_status: string | null;
  scheduled_visit_at: string | null;
  visit_timezone?: string;
  reported_at: string;
  acknowledged_at: string | null;
  completed_at: string | null;
  closed_at: string | null;
  work_notes: string | null;
  completion_summary: string | null;
  is_emergency_priority: boolean;
  show_emergency_panel?: boolean;
  emergency_kind_hint?: string | null;
  file_ids: string[];
  created_at: string;
  updated_at?: string;
}

export interface MaintenanceCategory {
  code: string;
  title: string;
}

export interface MaintenanceCreateInput {
  title: string;
  description: string;
  category_code: string;
  priority: 'low' | 'normal' | 'high' | 'urgent';
  property_id: string;
  room_id?: string | null;
  tenant_id?: string | null;
}

export interface SupportPlan {
  id: string;
  organisation_id: string;
  reference_number: string;
  tenant_id: string;
  title: string;
  description: string | null;
  support_objectives: string | null;
  responsible_worker_user_id: string | null;
  start_date: string | null;
  planned_review_date: string | null;
  status: string;
  completed_at: string | null;
  closed_at: string | null;
  hold_reason: string | null;
  tenant_summary: string | null;
  version_number: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface Appointment {
  id: string;
  organisation_id: string;
  tenant_id: string;
  reference_number: string;
  appointment_kind: string;
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string | null;
  timezone: string;
  location: string | null;
  method: string | null;
  assigned_user_id: string | null;
  status: string;
  attendance_status: string | null;
  outcome: string | null;
  cancel_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface TimelineItem {
  dedupe_key: string;
  activity_type: string;
  occurred_at: string;
  sort_at: string;
  title: string;
  summary: string | null;
  status: string | null;
  reference: string | null;
  resource_type: string;
  resource_id: string;
  detail_api_path: string;
  can_view: boolean;
}

export interface ManagedDocument {
  id: string;
  reference_number?: string;
  title: string;
  description: string | null;
  category_code: string | null;
  status: string;
  expiry_date: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface InboxMessage {
  recipient_id: string;
  message_id: string;
  conversation_id: string;
  subject: string;
  body_preview: string;
  created_at: string;
  read_at: string | null;
  sender_user_id: string | null;
  related_resource_type?: string | null;
  related_resource_id?: string | null;
}

export interface MessageDetail {
  id: string;
  conversation_id?: string;
  subject: string;
  body: string;
  created_at: string;
  sender_user_id?: string | null;
}

export interface AnnouncementSummary {
  id: string;
  reference_number: string;
  title: string;
  priority: string;
  published_at: string | null;
}

export interface AnnouncementDetail extends AnnouncementSummary {
  body: string;
  status: string;
}

export interface AssistantSourceRef {
  title?: string;
  source_type?: string;
  source_id?: string;
}

export interface AssistantMessage {
  id: string;
  conversation_id: string;
  role: string;
  body: string;
  source_refs: AssistantSourceRef[];
  ai_status: string | null;
  escalation: boolean | string | null;
  cache_status: string | null;
  created_at: string | null;
}

export interface AssistantAvailability {
  available: boolean;
  pilot_configured: boolean;
  notice: string;
  makes_official_decisions: boolean;
}

export interface AssistantAskResult {
  conversation_id: string;
  question_message_id: string;
  message: AssistantMessage;
  notice: string;
  makes_official_decisions: boolean;
  approved_content_count: number;
  activity_id?: string | null;
}

export interface AssistantConversationSummary {
  id: string;
  status: string;
  last_message_at: string | null;
}

export interface AssistantConversation {
  id: string;
  status: string;
  messages: AssistantMessage[];
  notice: string;
  makes_official_decisions: boolean;
}

export interface HousingApplication {
  id: string;
  organisation_id: string;
  reference_number: string;
  tenant_id: string;
  preferred_property_id: string | null;
  accommodation_type: string | null;
  housing_requirements: string;
  household_summary: string | null;
  supporting_information: string | null;
  priority: string;
  status: string;
  information_required_notes: string | null;
  submitted_at: string | null;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
  on_waiting_list: boolean;
  waiting_list_position: number | null;
}

export const PHASE5_PENDING = 'phase5_pending' as const;

export interface Phase5PendingResult {
  status: typeof PHASE5_PENDING;
  feature: 'community' | 'jobs';
  message: string;
}
