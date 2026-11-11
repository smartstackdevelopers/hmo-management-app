import { Redirect, Stack } from 'expo-router';
import { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';

import { SyncStatusBanner } from '@/components/offline/SyncStatusBanner';
import { BiometricLockGate } from '@/components/security/BiometricLockGate';
import { DeviceSessionRevokedNotice } from '@/components/security/DeviceSessionRevokedNotice';
import { LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { installPushResponseListener } from '@/lib/hmore/push/handler';
import { isStaffShellRole } from '@/lib/hmore/roles';

const headerOptions = {
  headerStyle: { backgroundColor: theme.colors.background },
  headerTintColor: theme.colors.text,
  headerTitleStyle: { fontWeight: '700' as const, fontSize: 17, letterSpacing: -0.3 },
  headerShadowVisible: false,
  headerBackTitle: 'Back',
  contentStyle: { backgroundColor: theme.colors.background, flex: 1 },
};

export default function AppLayout() {
  const { isAuthenticated, isLoading, hmore, user } = useAuth();
  const { t } = useI18n();
  const tenant = !!hmore && user?.role === 'tenant';

  useEffect(() => {
    if (!isAuthenticated) return;
    return installPushResponseListener(isStaffShellRole(user?.role));
  }, [isAuthenticated, user?.role]);

  if (isLoading) return <LoadingScreen message="Loading your account..." />;

  if (!isAuthenticated) {
    return <Redirect href="/(auth)/welcome" />;
  }

  return (
    <BiometricLockGate>
      <View style={styles.root}>
        <DeviceSessionRevokedNotice />
        <SyncStatusBanner />
      <Stack screenOptions={{ headerShown: false, contentStyle: { flex: 1, backgroundColor: theme.colors.background } }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="property/[id]" options={{ ...headerOptions, headerShown: true, title: 'Property Details' }} />
        <Stack.Screen name="property/new" options={{ ...headerOptions, headerShown: true, title: 'Add Property' }} />
        <Stack.Screen name="property/add-room" options={{ ...headerOptions, headerShown: true, title: 'Add Room' }} />
        <Stack.Screen name="property/upload-document" options={{ ...headerOptions, headerShown: true, title: 'Upload Document' }} />
        <Stack.Screen name="maintenance/[id]" options={{ ...headerOptions, headerShown: true, title: 'Repair Details' }} />
        <Stack.Screen name="maintenance/new" options={{ ...headerOptions, headerShown: true, title: tenant ? t('repairs.newTitle') : 'Report Repair' }} />
        <Stack.Screen name="conversation/[id]" options={{ ...headerOptions, headerShown: true, title: 'Conversation' }} />
        <Stack.Screen name="conversation/new" options={{ ...headerOptions, headerShown: true, title: 'New Message' }} />
        <Stack.Screen name="listing/[id]" options={{ ...headerOptions, headerShown: true, title: 'Room Listing' }} />
        <Stack.Screen name="listing/new" options={{ ...headerOptions, headerShown: true, title: 'Create Listing' }} />
        <Stack.Screen name="inspection/[id]" options={{ ...headerOptions, headerShown: true, title: 'Inspection' }} />
        <Stack.Screen name="inspection/new" options={{ ...headerOptions, headerShown: true, title: 'Schedule Inspection' }} />
        <Stack.Screen name="documents" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.files') : 'My files' }} />
        <Stack.Screen name="notifications" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.alerts') : 'Notifications' }} />
        <Stack.Screen name="staff/visits" options={{ ...headerOptions, headerShown: true, title: 'Visits' }} />
        <Stack.Screen name="staff/tasks" options={{ ...headerOptions, headerShown: true, title: 'Tasks' }} />
        <Stack.Screen name="staff/incidents" options={{ ...headerOptions, headerShown: true, title: 'Incidents' }} />
        <Stack.Screen name="staff/occupancy" options={{ ...headerOptions, headerShown: true, title: 'Occupancy surveys' }} />
        <Stack.Screen name="staff/approvals" options={{ ...headerOptions, headerShown: true, title: 'Approvals' }} />
        <Stack.Screen name="staff/case/[tenantId]" options={{ ...headerOptions, headerShown: true, title: 'Tenant' }} />
        <Stack.Screen name="staff/incident/[id]" options={{ ...headerOptions, headerShown: true, title: 'Incident' }} />
        <Stack.Screen name="staff/work-order/[id]" options={{ ...headerOptions, headerShown: true, title: 'Work order' }} />
        <Stack.Screen name="community" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.services') : 'Community directory' }} />
        <Stack.Screen name="community/[id]" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.services') : 'Service details' }} />
        <Stack.Screen name="jobs" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.jobs') : 'Jobs and training' }} />
        <Stack.Screen name="assistant" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.assistant') : 'Assistant' }} />
        <Stack.Screen name="accessibility" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.settings') : 'Accessibility' }} />
        <Stack.Screen name="security" options={{ ...headerOptions, headerShown: true, title: 'Privacy & Security' }} />
        <Stack.Screen name="offline-drafts" options={{ ...headerOptions, headerShown: true, title: 'Offline drafts' }} />
        <Stack.Screen name="browse" options={{ ...headerOptions, headerShown: true, title: 'Find a Room' }} />
        <Stack.Screen name="wishlist" options={{ ...headerOptions, headerShown: true, title: 'Wishlist' }} />
      </Stack>
      </View>
    </BiometricLockGate>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.colors.background },
});
