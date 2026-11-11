import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { PushPreferenceToggle } from '@/components/PushPreferenceToggle';
import { DeviceSecurityPanel } from '@/components/security/DeviceSecurityPanel';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Avatar, ListRow } from '@/components/ui/ListRow';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { useTabClearance } from '@/hooks/useLayout';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getOwnProfile, patchOwnTenant } from '@/lib/hmore/services/tenants';
import { ROLE_LABELS } from '@/types';

export function HmoreAccount() {
  const { user, hmore, signOut } = useAuth();
  const { t, fontScale, prefs } = useI18n();
  const bottomPad = useTabClearance();
  const client = useQueryClient();
  const isTenant = hmore?.rbac.active_role === 'tenant';
  const profileQuery = useQuery({
    queryKey: ['hmore', 'tenant-me'],
    queryFn: getOwnProfile,
    enabled: isTenant,
  });
  const profile = profileQuery.data;
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [readyFor, setReadyFor] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!profile || readyFor === profile.id) return;
    setName(profile.preferred_name);
    setPhone(profile.phone ?? '');
    setReadyFor(profile.id);
  }, [profile, readyFor]);

  const save = useMutation({
    mutationFn: () =>
      patchOwnTenant({
        preferred_name: name.trim(),
        phone: phone.trim() ? phone.trim() : null,
      }),
    onSuccess: async (updated) => {
      setSaved(true);
      setName(updated.preferred_name);
      setPhone(updated.phone ?? '');
      await client.invalidateQueries({ queryKey: ['hmore', 'tenant-me'] });
    },
    onError: () => setSaved(false),
  });

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  const displayName = profile?.preferred_name || name || `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim();
  const contrast = prefs.highContrast;

  return (
    <ScrollView
      style={[styles.container, contrast && styles.contrast]}
      contentContainerStyle={[styles.content, { paddingBottom: bottomPad }]}
    >
      <Text style={[styles.pageTitle, contrast && styles.contrastText, { fontSize: 28 * fontScale }]}>{t('profile.title')}</Text>
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <Avatar name={displayName || t('profile.title')} />
          <View style={styles.profileCopy}>
            <Text style={[styles.name, contrast && styles.contrastText]} numberOfLines={1}>
              {displayName || t('profile.title')}
            </Text>
            <Text style={styles.email} numberOfLines={1}>
              {profile?.email || user?.email}
            </Text>
            {user?.role ? <Text style={styles.role}>{ROLE_LABELS[user.role]}</Text> : null}
          </View>
        </View>
        {isTenant ? (
          <View style={styles.form}>
            <Text style={[styles.note, { fontSize: 13 * fontScale }]}>{t('profile.note')}</Text>
            <Input
              label={t('profile.preferredName')}
              value={name}
              onChangeText={(value) => {
                setSaved(false);
                setName(value);
              }}
              accessibilityLabel={t('profile.preferredName')}
            />
            <Input
              label={t('profile.phone')}
              value={phone}
              onChangeText={(value) => {
                setSaved(false);
                setPhone(value);
              }}
              keyboardType="phone-pad"
              accessibilityLabel={t('profile.phone')}
            />
            {save.error ? <Text style={styles.error}>{hmoreErrorMessage(save.error)}</Text> : null}
            {saved ? <Text style={styles.saved}>{t('profile.saved')}</Text> : null}
            <Button
              title={t('profile.save')}
              accessibilityLabel={t('profile.save')}
              onPress={() => save.mutate()}
              loading={save.isPending}
              disabled={!name.trim()}
              fullWidth
            />
          </View>
        ) : (
          <Text style={styles.note}>{t('profile.signedIn')}</Text>
        )}
      </Card>

      <Card padded={false}>
        <ListRow title={t('profile.offlineDrafts')} icon="cloud-offline-outline" onPress={() => router.push('/(app)/offline-drafts')} />
        <View style={styles.divider} />
        <ListRow title={t('profile.alerts')} icon="notifications-outline" onPress={() => router.push('/(app)/notifications')} />
        <View style={styles.divider} />
        <ListRow title={t('profile.files')} icon="folder-outline" onPress={() => router.push('/(app)/documents')} />
        {isTenant ? (
          <>
            <View style={styles.divider} />
            <ListRow title={t('profile.home')} icon="business-outline" onPress={() => router.push('/(app)/(tabs)/tenancy')} />
            <View style={styles.divider} />
            <ListRow title={t('profile.support')} icon="people-outline" onPress={() => router.push('/(app)/(tabs)/support')} />
            <View style={styles.divider} />
            <ListRow title={t('profile.assistant')} icon="chatbubble-ellipses-outline" onPress={() => router.push('/(app)/assistant')} />
            <View style={styles.divider} />
            <ListRow title={t('profile.services')} icon="location-outline" onPress={() => router.push('/(app)/community')} />
            <ListRow title={t('profile.helpNearMe')} icon="navigate-outline" onPress={() => router.push('/(app)/help-near-me')} />
            <ListRow title={t('profile.employment')} icon="briefcase-outline" onPress={() => router.push('/(app)/employment')} />
            <ListRow title={t('jobMatching.title')} icon="search-outline" onPress={() => router.push('/(app)/job-matching')} />
            <View style={styles.divider} />
            <ListRow title={t('profile.jobs')} icon="briefcase-outline" onPress={() => router.push('/(app)/jobs')} />
          </>
        ) : null}
        <View style={styles.divider} />
        <ListRow title={t('profile.accessibility')} icon="accessibility-outline" onPress={() => router.push('/(app)/accessibility')} />
      </Card>

      <DeviceSecurityPanel onSignedOut={() => router.replace('/(auth)/welcome')} />
      <PushPreferenceToggle />
      <Text style={styles.version}>{t('profile.version')}</Text>
      <Button title={t('profile.signOut')} accessibilityLabel={t('profile.signOut')} variant="outline" onPress={handleSignOut} fullWidth />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  content: { padding: theme.spacing.md },
  pageTitle: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.md, letterSpacing: -0.5 },
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  profileCopy: { flex: 1, minWidth: 0 },
  name: { fontSize: 18, fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
  email: { fontSize: 14, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  role: {
    fontSize: 12,
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.secondaryDark,
    marginTop: 6,
    alignSelf: 'flex-start',
    backgroundColor: theme.colors.accentLight,
    overflow: 'hidden',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
  },
  form: { marginTop: theme.spacing.md },
  note: { fontFamily: FONT_MEDIUM, fontSize: 13, lineHeight: 18, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: theme.spacing.sm },
  saved: { color: theme.colors.success, fontFamily: FONT_SEMIBOLD, marginBottom: theme.spacing.sm },
  divider: { height: 1, backgroundColor: theme.colors.borderLight, marginLeft: 60 },
  version: { textAlign: 'center', color: theme.colors.textMuted, fontSize: 12, fontFamily: FONT_MEDIUM, marginVertical: theme.spacing.lg },
});
