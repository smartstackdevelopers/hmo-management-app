import { UserRole } from '@/types';

export type IconName = string;

export interface TabConfig {
  name: string;
  title: string;
  icon: IconName;
  iconFocused: IconName;
}

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
    { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  property_manager: [
    { name: 'index', title: 'Home', icon: 'grid-outline', iconFocused: 'grid' },
    { name: 'properties', title: 'Properties', icon: 'business-outline', iconFocused: 'business' },
    { name: 'maintenance', title: 'Repairs', icon: 'construct-outline', iconFocused: 'construct' },
    { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  contractor: [
    { name: 'index', title: 'Jobs', icon: 'briefcase-outline', iconFocused: 'briefcase' },
    { name: 'schedule', title: 'Schedule', icon: 'calendar-outline', iconFocused: 'calendar' },
    { name: 'messages', title: 'Messages', icon: 'chatbubbles-outline', iconFocused: 'chatbubbles' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
  admin: [
    { name: 'index', title: 'Dashboard', icon: 'stats-chart-outline', iconFocused: 'stats-chart' },
    { name: 'users', title: 'Users', icon: 'people-outline', iconFocused: 'people' },
    { name: 'listings', title: 'Listings', icon: 'list-outline', iconFocused: 'list' },
    { name: 'settings', title: 'Platform', icon: 'settings-outline', iconFocused: 'settings' },
    { name: 'more', title: 'Account', icon: 'person-circle-outline', iconFocused: 'person-circle' },
  ],
};

export const TAB_SCREEN_TITLES: Record<string, string> = {
  index: 'Home',
  find: 'Find a room',
  properties: 'Properties',
  compliance: 'Property checks',
  tenancy: 'My home',
  maintenance: 'Repairs',
  inspections: 'Inspections',
  schedule: 'Schedule',
  messages: 'Messages',
  users: 'Users',
  listings: 'Listings',
  settings: 'Platform',
  more: 'Account',
};
