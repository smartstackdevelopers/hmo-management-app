import { Ionicons } from '@expo/vector-icons';

import { theme } from '@/constants/theme';

export type RepairFilter = 'all' | 'open' | 'urgent' | 'done';

export const OPEN_STATUSES = ['open', 'assigned', 'in_progress', 'awaiting_parts'] as const;
export const DONE_STATUSES = ['completed', 'closed', 'cancelled'] as const;
export const URGENT_PRIORITIES = ['high', 'emergency'] as const;

export const STATUS_VARIANT: Record<string, 'default' | 'warning' | 'success' | 'error' | 'info'> = {
  open: 'warning',
  assigned: 'info',
  in_progress: 'info',
  awaiting_parts: 'warning',
  completed: 'success',
  closed: 'default',
  cancelled: 'error',
};

export const PRIORITY_VARIANT: Record<string, 'default' | 'warning' | 'error'> = {
  low: 'default',
  medium: 'default',
  high: 'warning',
  emergency: 'error',
};

export const PRIORITY_COLOR: Record<string, string> = {
  low: theme.colors.textMuted,
  medium: theme.colors.info,
  high: theme.colors.warning,
  emergency: theme.colors.error,
};

export const PRIORITY_LABEL: Record<string, string> = {
  low: 'Low',
  medium: 'Normal',
  high: 'High',
  emergency: 'Emergency',
};

export const STATUS_LABEL: Record<string, string> = {
  open: 'Reported',
  assigned: 'Assigned',
  in_progress: 'In progress',
  awaiting_parts: 'Awaiting parts',
  completed: 'Completed',
  closed: 'Closed',
  cancelled: 'Cancelled',
};

export const CATEGORY_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  Plumbing: 'water-outline',
  Electrical: 'flash-outline',
  'Heating & Boiler': 'thermometer-outline',
  'Damp & Mould': 'rainy-outline',
  Structural: 'home-outline',
  Appliances: 'hardware-chip-outline',
  'Locks & Security': 'lock-closed-outline',
  'Pest Control': 'bug-outline',
  Other: 'construct-outline',
};

/** Simplified progress steps shown on repair detail. */
export const REPAIR_TRACK = [
  { key: 'open', label: 'Reported' },
  { key: 'assigned', label: 'Assigned' },
  { key: 'in_progress', label: 'Working' },
  { key: 'completed', label: 'Done' },
] as const;

export function isOpenStatus(status: string): boolean {
  return (OPEN_STATUSES as readonly string[]).includes(status);
}

export function isDoneStatus(status: string): boolean {
  return (DONE_STATUSES as readonly string[]).includes(status);
}

export function isUrgentPriority(priority: string): boolean {
  return (URGENT_PRIORITIES as readonly string[]).includes(priority);
}

export function categoryIcon(category: string): keyof typeof Ionicons.glyphMap {
  return CATEGORY_ICON[category] ?? 'construct-outline';
}

export function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status.replace(/_/g, ' ');
}

export function trackStepIndex(status: string): number {
  if (status === 'cancelled') return -1;
  if (status === 'closed' || status === 'completed') return 3;
  if (status === 'awaiting_parts' || status === 'in_progress') return 2;
  if (status === 'assigned') return 1;
  return 0;
}

export function nextStepHint(status: string, role: string): string | null {
  if (status === 'open') {
    return role === 'tenant'
      ? 'Your landlord has been notified and will assign a contractor.'
      : 'Assign a contractor to get this repair moving.';
  }
  if (status === 'assigned') {
    return role === 'tenant'
      ? 'A contractor has been assigned and will start soon.'
      : 'Waiting for the contractor to start work.';
  }
  if (status === 'in_progress' || status === 'awaiting_parts') {
    return role === 'tenant'
      ? 'Work is under way — you will see updates here.'
      : 'Contractor is working on this job.';
  }
  if (status === 'completed') {
    return role === 'tenant'
      ? 'Marked complete. Your landlord will close the job after checks.'
      : 'Review and close the job when you are happy.';
  }
  if (status === 'closed') return 'This repair is closed.';
  if (status === 'cancelled') return 'This request was cancelled.';
  return null;
}

export function relativeTime(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export function matchesRepairFilter(
  item: { status: string; priority: string },
  filter: RepairFilter
): boolean {
  if (filter === 'all') return true;
  if (filter === 'open') return isOpenStatus(item.status);
  if (filter === 'urgent') return isOpenStatus(item.status) && isUrgentPriority(item.priority);
  return isDoneStatus(item.status);
}
