import { UserRole } from '@/types';

export interface PowerFeature {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  route?: string;
  badge?: string;
  comingSoon?: boolean;
}

export const ROLE_POWER_FEATURES: Record<UserRole, PowerFeature[]> = {
  landlord: [
    { id: 'portfolio', title: 'Portfolio command', subtitle: 'Properties, rooms, occupancy', icon: 'business-outline', route: '/(app)/(tabs)/properties' },
    { id: 'compliance', title: 'Council readiness', subtitle: 'BCC compliance + AI copilot', icon: 'shield-checkmark-outline', route: '/(app)/(tabs)/compliance', badge: 'AI' },
    { id: 'listings', title: 'Room marketplace', subtitle: 'List vacancies and manage applications', icon: 'bed-outline', route: '/(app)/(tabs)/listings' },
    { id: 'repairs', title: 'Repair operations', subtitle: 'Assign contractors, close jobs', icon: 'construct-outline', route: '/(app)/(tabs)/maintenance' },
    { id: 'evidence', title: 'Evidence packs', subtitle: 'One-tap council audit export', icon: 'document-text-outline', route: '/(app)/documents', badge: 'New' },
    { id: 'payments', title: 'Rent & payouts', subtitle: 'Automated rent collection', icon: 'card-outline', comingSoon: true },
    { id: 'screening', title: 'Tenant screening', subtitle: 'Credit + right-to-rent checks', icon: 'id-card-outline', comingSoon: true },
  ],
  tenant: [
    { id: 'browse', title: 'Find rooms', subtitle: 'Search and filter available HMO rooms', icon: 'search-outline', route: '/(app)/(tabs)/find', badge: 'Live' },
    { id: 'wishlist', title: 'Wishlist & alerts', subtitle: 'Saved rooms + search alerts', icon: 'heart-outline', route: '/(app)/wishlist' },
    { id: 'tenancy', title: 'My tenancy', subtitle: 'Rent, documents, rights', icon: 'home-outline', route: '/(app)/(tabs)/tenancy' },
    { id: 'repairs', title: 'Report repairs', subtitle: 'AI triage + photo evidence', icon: 'build-outline', route: '/(app)/maintenance/new', badge: 'AI' },
    { id: 'messages', title: 'Landlord chat', subtitle: 'In-app messaging', icon: 'chatbubbles-outline', route: '/(app)/(tabs)/messages' },
    { id: 'split', title: 'Bill splitting', subtitle: 'Shared house utilities', icon: 'receipt-outline', comingSoon: true },
    { id: 'deposit', title: 'Deposit protection', subtitle: 'Track deposit status', icon: 'lock-closed-outline', comingSoon: true },
  ],
  property_manager: [
    { id: 'portfolio', title: 'Managed portfolio', subtitle: 'Multi-property oversight', icon: 'business-outline', route: '/(app)/(tabs)/properties' },
    { id: 'compliance', title: 'Compliance HQ', subtitle: 'Portfolio score + alerts', icon: 'shield-checkmark-outline', route: '/(app)/(tabs)/compliance', badge: 'AI' },
    { id: 'inspections', title: 'Inspections', subtitle: 'Schedule + complete checks', icon: 'clipboard-outline', route: '/(app)/(tabs)/inspections' },
    { id: 'listings', title: 'Vacancy engine', subtitle: 'Listings + applications', icon: 'list-outline', route: '/(app)/(tabs)/listings' },
    { id: 'repairs', title: 'Maintenance ops', subtitle: 'SLA tracking + contractors', icon: 'construct-outline', route: '/(app)/(tabs)/maintenance' },
    { id: 'analytics', title: 'Portfolio analytics', subtitle: 'Yield + void analysis', icon: 'analytics-outline', comingSoon: true },
  ],
  contractor: [
    { id: 'jobs', title: 'Job board', subtitle: 'Assigned repairs', icon: 'briefcase-outline', route: '/(app)/(tabs)/schedule' },
    { id: 'updates', title: 'Job updates', subtitle: 'Notes, photos, completion', icon: 'camera-outline', route: '/(app)/(tabs)/maintenance' },
    { id: 'invoices', title: 'Invoices', subtitle: 'Upload work invoices', icon: 'document-outline', route: '/(app)/documents' },
    { id: 'routing', title: 'Smart routing', subtitle: 'Optimised daily schedule', icon: 'navigate-outline', comingSoon: true },
  ],
  admin: [
    { id: 'users', title: 'User management', subtitle: 'Verify landlords & tenants', icon: 'people-outline', route: '/(app)/(tabs)/users' },
    { id: 'analytics', title: 'Platform analytics', subtitle: 'Growth + compliance metrics', icon: 'stats-chart-outline', route: '/(app)/(tabs)/settings' },
    { id: 'council', title: 'Council dashboard', subtitle: 'City-wide HMO oversight', icon: 'earth-outline', comingSoon: true },
    { id: 'mandate', title: 'Mandatory licensing', subtitle: 'Council integration API', icon: 'link-outline', comingSoon: true },
  ],
};
