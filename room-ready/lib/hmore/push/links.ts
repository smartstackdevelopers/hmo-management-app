import { staffAlertHref } from '@/lib/hmore/staff/alerts';
import { protectedNavigationBlocked } from '@/lib/hmore/security/accessGate';

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export interface PushData {
  message_id?: string;
  related_resource_type?: string;
  related_resource_id?: string;
}

function textField(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const trimmed = value.trim();
  return trimmed || undefined;
}

/** Keeps only routing ids. Notification copy and case narrative are ignored. */
export function parsePushData(data: unknown): PushData {
  if (!data || typeof data !== 'object') return {};
  const record = data as Record<string, unknown>;
  return {
    message_id: textField(record.message_id),
    related_resource_type: textField(record.related_resource_type),
    related_resource_id: textField(record.related_resource_id),
  };
}

/** Staff taps use the same record links as StaffAlertList. Everyone else opens the inbox, or a known repair. */
export function pushOpenHref(data: PushData, isStaff: boolean): string {
  if (isStaff) {
    return (
      staffAlertHref({
        related_resource_type: data.related_resource_type,
        related_resource_id: data.related_resource_id,
      }) ?? '/(app)/notifications'
    );
  }
  if (data.related_resource_type === 'maintenance_request' && data.related_resource_id && UUID.test(data.related_resource_id)) {
    return `/(app)/maintenance/${data.related_resource_id}`;
  }
  return '/(app)/notifications';
}

export async function handlePushOpen(
  data: PushData,
  isStaff: boolean,
  deps: {
    navigate: (href: string) => void;
    markRead: (messageId: string) => Promise<unknown>;
    allowProtectedNavigation?: () => Promise<boolean>;
  },
): Promise<string> {
  const allowed = deps.allowProtectedNavigation
    ? await deps.allowProtectedNavigation()
    : !(await protectedNavigationBlocked());
  if (!allowed) return '';
  const href = pushOpenHref(data, isStaff);
  deps.navigate(href);
  if (data.message_id && UUID.test(data.message_id)) {
    try {
      await deps.markRead(data.message_id);
    } catch {
      // The inbox remains the source of truth when the read request fails.
    }
  }
  return href;
}
