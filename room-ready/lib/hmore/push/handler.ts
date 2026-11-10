import { router, type Href } from 'expo-router';

import { markMessageRead } from '@/lib/hmore/services/communications';
import { handlePushOpen, parsePushData } from '@/lib/hmore/push/links';

/** Listens for a notification tap. Missing expo-notifications leaves the in-app inbox as the only path. */
export function installPushResponseListener(isStaff: boolean): () => void {
  let active = true;
  let subscription: { remove: () => void } | undefined;

  void import('expo-notifications')
    .then((Notifications) => {
      if (!active) return;
      Notifications.setNotificationHandler({
        handleNotification: async () => ({
          shouldPlaySound: false,
          shouldSetBadge: false,
          shouldShowBanner: true,
          shouldShowList: true,
        }),
      });
      subscription = Notifications.addNotificationResponseReceivedListener((response) => {
        const data = parsePushData(response.notification.request.content.data);
        void handlePushOpen(data, isStaff, {
          navigate: (href) => router.push(href as Href),
          markRead: (messageId) => markMessageRead(messageId),
        });
      });
    })
    .catch(() => undefined);

  return () => {
    active = false;
    subscription?.remove();
  };
}
