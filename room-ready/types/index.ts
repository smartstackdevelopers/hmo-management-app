export type UserRole =
  | 'landlord'
  | 'tenant'
  | 'property_manager'
  | 'contractor'
  | 'admin';

export interface User {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
  phone?: string;
  verified?: boolean;
  active?: boolean;
  createdAt: string;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  landlord: 'Landlord',
  tenant: 'Tenant',
  property_manager: 'Property Manager',
  contractor: 'Contractor',
  admin: 'Administrator',
};

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  landlord: 'Manage properties, tenants, compliance and maintenance',
  tenant: 'Manage your tenancy, report repairs and stay informed',
  property_manager: 'Manage properties on behalf of landlords',
  contractor: 'Receive jobs, update progress and submit invoices',
  admin: 'Oversee platform users, listings and settings',
};
