import { isStaffShellRole, isSupportShellRole } from '@/lib/hmore/roles';
import { UserRole } from '@/types';

export type IconName = string;

export interface TabConfig {
  name: string;
  title: string;
  icon: IconName;
  iconFocused: IconName;
}

const SUPPORT_TABS: TabConfig[] = [
  { name: 'index', title: 'Home', icon: 'home-outline', iconFocused: 'home' },
  { name: 'caseload', title: 'My Tenants', icon: 'people-outline', iconFocused: 'people' },
  { name: 'shifts', title: 'Shifts', icon: 'time-outline', iconFocused: 'time' },
  { name: 'notes', title: 'Notes', icon: 'document-text-outline', iconFocused: 'document-text' },
  { name: 'more', title: 'More', icon: 'person-circle-outline', iconFocused: 'person-circle' },
];

const STAFF_CONTRACTOR_TABS: TabConfig[] = [
  { name: 'index', title: 'Home', icon: 'briefcase-outline', iconFocused: 'briefcase' },
  { name: 'work-orders', title: 'Work orders', icon: 'construct-outline', iconFocused: 'construct' },
  { name: 'schedule', title: 'Schedule', icon: 'calendar-outline', iconFocused: 'calendar' },
  { name: 'evidence', title: 'Photos', icon: 'camera-outline', iconFocused: 'camera' },
  { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
];

export const ROLE_TABS: Record<UserRole, TabConfig[]> = {
  landlord: [
    { name: 'index', title: 'Home', icon: 'grid-outline', iconFocused: 'grid' },
    { name: 'properties', title: 'Properties', icon: 'business-outline', iconFocused: 'business' },
    { name: 'maintenance', title: 'Repairs', icon: 'construct-outline', iconFocused: 'construct' },
    { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  tenant: [
    { name: 'index', title: 'Home', icon: 'home-outline', iconFocused: 'home' },
    { name: 'tenancy', title: 'My home', icon: 'business-outline', iconFocused: 'business' },
    { name: 'maintenance', title: 'Repairs', icon: 'construct-outline', iconFocused: 'construct' },
    { name: 'support', title: 'Support', icon: 'people-outline', iconFocused: 'people' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  property_manager: [
    { name: 'index', title: 'Home', icon: 'grid-outline', iconFocused: 'grid' },
    { name: 'properties', title: 'Properties', icon: 'business-outline', iconFocused: 'business' },
    { name: 'maintenance', title: 'Repairs', icon: 'construct-outline', iconFocused: 'construct' },
    { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  contractor: STAFF_CONTRACTOR_TABS,
  admin: [
    { name: 'index', title: 'Dashboard', icon: 'stats-chart-outline', iconFocused: 'stats-chart' },
    { name: 'users', title: 'Users', icon: 'people-outline', iconFocused: 'people' },
    { name: 'listings', title: 'Listings', icon: 'list-outline', iconFocused: 'list' },
    { name: 'settings', title: 'Platform', icon: 'settings-outline', iconFocused: 'settings' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  support_worker: SUPPORT_TABS,
  organisation_admin: SUPPORT_TABS,
};

/** Password-login tenants keep the previous Room Ready tabs. HMore tenants use ROLE_TABS.tenant. */
export const LEGACY_TENANT_TABS: TabConfig[] = [
  { name: 'index', title: 'Home', icon: 'home-outline', iconFocused: 'home' },
  { name: 'tenancy', title: 'My home', icon: 'business-outline', iconFocused: 'business' },
  { name: 'maintenance', title: 'Repairs', icon: 'construct-outline', iconFocused: 'construct' },
  { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
  { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
];

/** Password-login contractors keep the previous job list. HMore contractors use work orders. */
export const LEGACY_CONTRACTOR_TABS: TabConfig[] = [
  { name: 'index', title: 'Jobs', icon: 'briefcase-outline', iconFocused: 'briefcase' },
  { name: 'schedule', title: 'Schedule', icon: 'calendar-outline', iconFocused: 'calendar' },
  { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
  { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
];

export function tabsForRole(role: UserRole | undefined, options?: { hmore?: boolean }): TabConfig[] {
  if (!role) return [];
  if (role === 'tenant' && !options?.hmore) return LEGACY_TENANT_TABS;
  if (role === 'contractor' && !options?.hmore) return LEGACY_CONTRACTOR_TABS;
  if (options?.hmore && isSupportShellRole(role)) return SUPPORT_TABS;
  if (options?.hmore && role === 'contractor') return STAFF_CONTRACTOR_TABS;
  return ROLE_TABS[role];
}

export function staffShellActive(role: UserRole | undefined, hmore: boolean): boolean {
  return hmore && isStaffShellRole(role);
}

export const TAB_SCREEN_TITLES: Record<string, string> = {
  index: 'Home',
  find: 'Find a room',
  properties: 'Properties',
  compliance: 'Property checks',
  tenancy: 'My home',
  maintenance: 'Repairs',
  support: 'Support',
  inspections: 'Inspections',
  schedule: 'Schedule',
  messages: 'Messages',
  users: 'Users',
  listings: 'Listings',
  settings: 'Platform',
  more: 'Account',
  caseload: 'My Tenants',
  shifts: 'Shifts',
  notes: 'Notes',
  'work-orders': 'Work orders',
  evidence: 'Photos',
};
