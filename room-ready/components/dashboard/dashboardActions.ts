import { Ionicons } from '@expo/vector-icons';

import { UserRole } from '@/types';

export interface DashboardAction {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  route: string;
  primary?: boolean;
}

/** Keep to 3 short labels so they fit a phone-width row. */
export const DASHBOARD_ACTIONS: Record<UserRole, DashboardAction[]> = {
  landlord: [
    { label: 'Properties', icon: 'business', route: '/(app)/(tabs)/properties', primary: true },
    { label: 'Repairs', icon: 'construct-outline', route: '/(app)/(tabs)/maintenance' },
    { label: 'Listings', icon: 'list-outline', route: '/(app)/(tabs)/listings' },
  ],
  tenant: [
    { label: 'My home', icon: 'business', route: '/(app)/(tabs)/tenancy', primary: true },
    { label: 'Repairs', icon: 'construct-outline', route: '/(app)/(tabs)/maintenance' },
    { label: 'Find', icon: 'search', route: '/(app)/(tabs)/find' },
  ],
  property_manager: [
    { label: 'Properties', icon: 'business', route: '/(app)/(tabs)/properties', primary: true },
    { label: 'Repairs', icon: 'construct-outline', route: '/(app)/(tabs)/maintenance' },
    { label: 'Listings', icon: 'list-outline', route: '/(app)/(tabs)/listings' },
  ],
  contractor: [
    { label: 'Today', icon: 'today', route: '/(app)/(tabs)/schedule', primary: true },
    { label: 'Messages', icon: 'chatbubbles-outline', route: '/(app)/(tabs)/messages' },
    { label: 'Files', icon: 'folder-outline', route: '/(app)/documents' },
  ],
  admin: [
    { label: 'Users', icon: 'people', route: '/(app)/(tabs)/users', primary: true },
    { label: 'Listings', icon: 'list-outline', route: '/(app)/(tabs)/listings' },
    { label: 'Alerts', icon: 'notifications-outline', route: '/(app)/notifications' },
  ],
};
