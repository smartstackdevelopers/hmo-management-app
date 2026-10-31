import { router } from 'expo-router';

import { NotificationItem } from '@/lib/api';

export function navigateFromNotification(n: NotificationItem) {
  const { maintenanceId, propertyId, listingId, conversationId } = n.data ?? {};
  if (maintenanceId) router.push(`/(app)/maintenance/${maintenanceId}`);
  else if (conversationId) router.push(`/(app)/conversation/${conversationId}`);
  else if (listingId) router.push(`/(app)/listing/${listingId}`);
  else if (n.data?.applicationId) router.push('/(app)/(tabs)/listings');
  else if (propertyId) router.push(`/(app)/property/${propertyId}`);
  else if (n.type === 'message') router.push('/(app)/(tabs)/messages');
  else if (n.type === 'application') router.push('/(app)/(tabs)/listings');
  else router.push('/(app)/notifications');
}
