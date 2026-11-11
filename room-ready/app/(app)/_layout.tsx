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
        <Stack.Screen name="community-hub" options={{ ...headerOptions, headerShown: true, title: tenant ? t('communityHub.title') : 'Community' }} />
        <Stack.Screen name="community" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.services') : 'Community directory' }} />
        <Stack.Screen name="community/[id]" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.services') : 'Service details' }} />
        <Stack.Screen name="help-near-me" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.helpNearMe') : 'Help near me' }} />
        <Stack.Screen name="help-near-me/[id]" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.helpNearMe') : 'Nearby service' }} />
        <Stack.Screen name="employment" options={{ ...headerOptions, headerShown: true, title: tenant ? t('nav.employment') : 'Employment prep' }} />
        <Stack.Screen name="employment-skills" options={{ ...headerOptions, headerShown: true, title: tenant ? t('employment.skills') : 'Skills' }} />
        <Stack.Screen name="employment-cvs" options={{ ...headerOptions, headerShown: true, title: tenant ? t('employment.cvs') : 'CVs' }} />
        <Stack.Screen name="employment-cv/[id]" options={{ ...headerOptions, headerShown: true, title: tenant ? t('employment.preview') : 'CV preview' }} />
        <Stack.Screen name="employment-applications" options={{ ...headerOptions, headerShown: true, title: tenant ? t('employment.applications') : 'Applications' }} />
        <Stack.Screen name="employment-interview" options={{ ...headerOptions, headerShown: true, title: tenant ? t('employment.interview') : 'Interview prep' }} />
        <Stack.Screen name="employment-roadmap" options={{ ...headerOptions, headerShown: true, title: tenant ? t('employment.roadmap') : 'Career roadmap' }} />
        <Stack.Screen name="job-matching" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.title') : 'Find jobs' }} />
        <Stack.Screen name="job-matching-search" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.search') : 'Job search' }} />
        <Stack.Screen name="job-matching-recommended" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.recommended') : 'Recommended jobs' }} />
        <Stack.Screen name="job-matching-saved" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.saved') : 'Saved jobs' }} />
        <Stack.Screen name="job-matching-training" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.training') : 'Training' }} />
        <Stack.Screen name="job-matching-preferences" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.preferences') : 'Preferences' }} />
        <Stack.Screen name="job-matching-detail/[id]" options={{ ...headerOptions, headerShown: true, title: tenant ? t('jobMatching.details') : 'Job details' }} />
        <Stack.Screen name="wellbeing" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.title') : 'My wellbeing' }} />
        <Stack.Screen name="wellbeing-checkin" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.checkin') : 'Daily check-in' }} />
        <Stack.Screen name="wellbeing-history" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.history') : 'Wellbeing history' }} />
        <Stack.Screen name="wellbeing-routines" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.routines') : 'Routines' }} />
        <Stack.Screen name="wellbeing-exercise" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.exercise') : 'Exercise' }} />
        <Stack.Screen name="wellbeing-mindfulness" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.mindfulness') : 'Mindfulness' }} />
        <Stack.Screen name="wellbeing-directory" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.directory') : 'Local support' }} />
        <Stack.Screen name="wellbeing-navigator" options={{ ...headerOptions, headerShown: true, title: tenant ? t('wellbeing.navigator') : 'Support navigator' }} />
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
