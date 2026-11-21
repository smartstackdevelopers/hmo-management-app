import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Alert, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { PushPreferenceToggle } from '@/components/PushPreferenceToggle';
import { AccountRow } from '@/components/tenant/AccountRow';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Input } from '@/components/ui/Input';
import { Avatar } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getOwnProfile, patchOwnTenant } from '@/lib/hmore/services/tenants';
import { ROLE_LABELS } from '@/types';

export function HmoreAccount() {
  const { user, hmore, signOut } = useAuth();
  const { t, fontScale, prefs } = useI18n();
  const client = useQueryClient();
  const isTenant = hmore?.rbac.active_role === 'tenant';
  const [detailsOpen, setDetailsOpen] = useState(false);
  const profileQuery = useQuery({
    queryKey: ['hmore', 'tenant-me'],
    queryFn: getOwnProfile,
    enabled: isTenant,
  });
  const profile = profileQuery.data;
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [needsGoals, setNeedsGoals] = useState('');
  const [readyFor, setReadyFor] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!profile || readyFor === profile.id) return;
    setName(profile.preferred_name);
    setPhone(profile.phone ?? '');
    setNeedsGoals(profile.needs_goals ?? '');
    setReadyFor(profile.id);
  }, [profile, readyFor]);

  const save = useMutation({
    mutationFn: () =>
      patchOwnTenant({
        preferred_name: name.trim(),
        phone: phone.trim() ? phone.trim() : null,
        needs_goals: needsGoals.trim() ? needsGoals.trim() : null,
      }),
    onSuccess: async (updated) => {
      setSaved(true);
      setName(updated.preferred_name);
      setPhone(updated.phone ?? '');
      setNeedsGoals(updated.needs_goals ?? '');
      await client.invalidateQueries({ queryKey: ['hmore', 'tenant-me'] });
    },
    onError: () => setSaved(false),
  });

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  function confirmSignOut() {
    Alert.alert(t('profile.signOut'), t('profile.signOutConfirm'), [
      { text: t('profile.cancel'), style: 'cancel' },
      { text: t('profile.signOut'), style: 'destructive', onPress: () => void handleSignOut() },
    ]);
  }

  const displayName = (profile?.preferred_name || name || `${user?.firstName ?? ''} ${user?.lastName ?? ''}`).trim();
  const contrast = prefs.highContrast;
  const email = (profile?.email || user?.email || '').trim();

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={profileQuery.isRefetching}
          onRefresh={() => profileQuery.refetch()}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={[styles.pageTitle, contrast && styles.contrastText, { fontSize: 28 * fontScale }]}>{t('profile.title')}</Text>
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <Avatar name={displayName || '•'} />
          <View style={styles.profileCopy}>
            {displayName ? (
              <Text style={[styles.name, contrast && styles.contrastText, { fontSize: 18 * fontScale }]} numberOfLines={1}>
                {displayName}
              </Text>
            ) : null}
            {email ? (
              <Text style={[styles.email, { fontSize: 14 * fontScale }]} numberOfLines={1}>
                {email}
              </Text>
            ) : null}
            {user?.role ? <Chip label={ROLE_LABELS[user.role]} tone="blue" size="md" /> : null}
          </View>
        </View>
      </Card>

      {isTenant ? (
        <Section title={t('profile.groupAccount')}>
          <Card padded={false} style={contrast ? styles.contrastCard : undefined}>
            <AccountRow
              title={t('profile.personal')}
              tone="amber"
              onPress={() => setDetailsOpen((open) => !open)}
              divider
            />
            {detailsOpen ? (
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
                <Input
                  label={t('profile.needsGoals')}
                  value={needsGoals}
                  onChangeText={(value) => {
                    setSaved(false);
                    setNeedsGoals(value);
                  }}
                  multiline
                  numberOfLines={4}
                  accessibilityLabel={t('profile.needsGoals')}
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
            ) : null}
            <AccountRow
              title={t('profile.documents')}
              tone="green"
              onPress={() => router.push('/(app)/documents')}
              divider
            />
            <AccountRow title={t('nav.alerts')} tone="blue" onPress={() => router.push('/(app)/notifications')} />
          </Card>
          <PushPreferenceToggle />
        </Section>
      ) : (
        <>
          <Text style={styles.note}>{t('profile.signedIn')}</Text>
          <PushPreferenceToggle />
        </>
      )}

      {isTenant ? (
        <Section title={t('profile.groupHelp')}>
          <Card padded={false} style={contrast ? styles.contrastCard : undefined}>
            <AccountRow
              title={t('communityHub.wellbeing')}
              tone="green"
              onPress={() => router.push('/(app)/wellbeing')}
              divider
            />
            <AccountRow title={t('profile.jobs')} tone="indigo" onPress={() => router.push('/(app)/jobs')} divider />
            <AccountRow
              title={t('profile.community')}
              tone="amber"
              onPress={() => router.push('/(app)/community-hub')}
              divider
            />
            <AccountRow title={t('profile.assistant')} tone="indigo" onPress={() => router.push('/(app)/assistant')} />
          </Card>
        </Section>
      ) : null}

      <Section title={t('profile.groupSettings')}>
        <Card padded={false} style={contrast ? styles.contrastCard : undefined}>
          {!isTenant ? (
            <>
              <AccountRow title={t('nav.alerts')} tone="blue" onPress={() => router.push('/(app)/notifications')} divider />
              <AccountRow
                title={t('profile.documents')}
                tone="green"
                onPress={() => router.push('/(app)/documents')}
                divider
              />
            </>
          ) : null}
          <AccountRow
            title={t('profile.accessibility')}
            tone="indigo"
            onPress={() => router.push('/(app)/accessibility')}
            divider
          />
          <AccountRow
            title={t('profile.offlineDrafts')}
            tone="gray"
            onPress={() => router.push('/(app)/offline-drafts')}
            divider
          />
          <AccountRow title={t('profile.security')} tone="indigo" onPress={() => router.push('/(app)/security')} divider />
          <AccountRow title={t('profile.signOut')} tone="red" danger onPress={confirmSignOut} />
        </Card>
      </Section>
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
  pageTitle: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.md, letterSpacing: -0.5 },
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.md },
  profileCopy: { flex: 1, minWidth: 0, gap: 4 },
  name: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
  email: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  form: { paddingHorizontal: theme.spacing.md, paddingBottom: theme.spacing.md },
  note: { fontFamily: FONT_MEDIUM, fontSize: 13, lineHeight: 18, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  error: { color: theme.colors.error, fontFamily: FONT_MEDIUM, marginBottom: theme.spacing.sm },
  saved: { color: theme.colors.success, fontFamily: FONT_SEMIBOLD, marginBottom: theme.spacing.sm },
});
