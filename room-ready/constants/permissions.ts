import { UserRole } from '@/types';

const ALL: UserRole[] = ['landlord', 'tenant', 'property_manager', 'contractor', 'admin'];

export const TAB_ROLES: Record<string, UserRole[]> = {
  index: ALL,
  find: ['tenant'],
  properties: ['landlord', 'property_manager'],
  compliance: ['landlord', 'property_manager'],
  tenancy: ['tenant'],
  maintenance: ['landlord', 'tenant', 'property_manager'],
  support: ['tenant'],
  inspections: ['property_manager'],
  schedule: ['contractor'],
  messages: ['landlord', 'tenant', 'property_manager', 'contractor'],
  users: ['admin'],
  listings: ['landlord', 'property_manager', 'admin'],
  settings: ['admin'],
  more: ALL,
};

export const ROUTE_ROLES = {
  propertyNew: ['landlord', 'admin'] as UserRole[],
  propertyAddRoom: ['landlord', 'property_manager', 'admin'] as UserRole[],
  propertyUploadDocument: ['landlord', 'property_manager', 'admin'] as UserRole[],
  listingNew: ['landlord', 'property_manager', 'admin'] as UserRole[],
  inspectionNew: ['property_manager', 'admin'] as UserRole[],
  inspectionDetail: ['landlord', 'property_manager', 'admin'] as UserRole[],
  maintenanceNew: ['tenant', 'landlord', 'property_manager', 'admin'] as UserRole[],
  browse: ['tenant'] as UserRole[],
  wishlist: ['tenant'] as UserRole[],
  documentsUpload: ['landlord', 'property_manager', 'admin'] as UserRole[],
  complianceMenu: ['landlord', 'property_manager', 'admin'] as UserRole[],
};

export function roleHasAccess(role: UserRole | undefined, allowed: UserRole[]): boolean {
  return !!role && allowed.includes(role);
}

export function getDefaultTabForRole(role: UserRole): string {
  return 'index';
}
