import { UserRole } from '@/types';

/** Maps FastAPI `active_role` onto the mobile shell. Support workers stay support workers. */
export function mapHmoreRole(role: string | null): UserRole {
  switch (role) {
    case 'landlord':
      return 'landlord';
    case 'tenant':
      return 'tenant';
    case 'maintenance_contractor':
      return 'contractor';
    case 'support_worker':
      return 'support_worker';
    case 'organisation_admin':
      return 'organisation_admin';
    case 'super_admin':
      return 'admin';
    default:
      return 'admin';
  }
}

export function isSupportShellRole(role: UserRole | string | null | undefined): boolean {
  return role === 'support_worker' || role === 'organisation_admin';
}

/** HMore staff shell. Legacy password users are not included unless the caller also checks `hmore`. */
export function isStaffShellRole(role: UserRole | string | null | undefined): boolean {
  return isSupportShellRole(role) || role === 'contractor';
}

export function hasPermission(permissions: string[] | undefined, permission: string): boolean {
  return !!permissions?.includes(permission);
}
