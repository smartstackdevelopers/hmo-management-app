const CASELOAD_ROLES = new Set(['support_worker', 'organisation_admin']);

export function assertCanUseCaseload(role: string | null | undefined): void {
  if (!role || !CASELOAD_ROLES.has(role)) {
    throw new Error('Caseload is only available to support workers and organisation admins.');
  }
}
