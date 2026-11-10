import { router } from 'expo-router';
import { Pressable, StyleSheet, Text } from 'react-native';

import { FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useOfflineDrafts, useOfflineReconnect } from '@/hooks/useStaffDrafts';
import type { Connectivity } from '@/lib/hmore/offline/network';

function label(connectivity: Connectivity | 'checking', count: number): string {
  const waiting = count === 1 ? '1 draft on this device' : `${count} drafts on this device`;
  if (connectivity === 'checking') return `Checking connection. ${waiting}.`;
  if (connectivity === 'online') return count ? `Online. ${waiting}.` : 'Online.';
  if (connectivity === 'unstable') return `Unstable. Sync is paused. ${waiting}.`;
  return `Offline. ${waiting}.`;
}

export function SyncStatusBanner() {
  const { hmore, isAuthenticated } = useAuth();
  const drafts = useOfflineDrafts();
  const connectivity = useOfflineReconnect(() => drafts.sync());
  if (!isAuthenticated || !hmore?.rbac.active_organisation_id) return null;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label(connectivity, drafts.count)}
      onPress={() => router.push('/(app)/offline-drafts')}
      style={styles.bar}
    >
      <Text style={styles.text}>{label(connectivity, drafts.count)}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: theme.colors.surfaceMuted,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  text: { fontFamily: FONT_SEMIBOLD, fontSize: 13, color: theme.colors.text },
});
