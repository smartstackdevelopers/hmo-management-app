import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { InitialsTile } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Input } from '@/components/ui/Input';
import { ListRow } from '@/components/ui/ListRow';
import { DeviceSecurityPanel } from '@/components/security/DeviceSecurityPanel';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useChangePassword } from '@/hooks/useApi';
import { ROLE_LABELS } from '@/types';

export default function SecurityScreen() {
  const { user, signOut } = useAuth();
  const changePassword = useChangePassword();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [success, setSuccess] = useState(false);

  async function handleSubmit() {
    const nextErrors: Record<string, string> = {};
    if (!currentPassword) nextErrors.currentPassword = 'Enter your current password';
    if (!newPassword) nextErrors.newPassword = 'Enter a new password';
    else if (newPassword.length < 8) nextErrors.newPassword = 'Use at least 8 characters';
    if (newPassword !== confirmPassword) nextErrors.confirmPassword = 'Passwords do not match';
    setErrors(nextErrors);
    setSuccess(false);
    if (Object.keys(nextErrors).length > 0) return;

    try {
      await changePassword.mutateAsync({ currentPassword, newPassword });
      setSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => router.back(), 1200);
    } catch (err) {
      setErrors({ form: err instanceof Error ? err.message : 'Could not change password' });
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Text style={styles.title} accessibilityRole="header">Privacy and security</Text>
      <Card style={styles.profile}>
        <View style={styles.profileRow}>
          <InitialsTile name={`${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || 'Account'} size={48} />
          <View style={styles.profileCopy}>
            <Text style={styles.name} numberOfLines={1}>{`${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || 'Account'}</Text>
            <Text style={styles.email} numberOfLines={1}>{user?.email}</Text>
            {user?.role ? <Chip label={ROLE_LABELS[user.role]} tone="blue" /> : null}
          </View>
        </View>
      </Card>
      <Text style={styles.section}>Security</Text>
      <DeviceSecurityPanel onSignedOut={() => router.replace('/(auth)/welcome')} />
      <Text style={styles.hint}>Update your account password. Use at least 8 characters. This password form is separate from fingerprint or face unlock.</Text>
      {success && (
        <View style={styles.successBanner}>
          <Text style={styles.successText}>Password updated successfully</Text>
        </View>
      )}
      {errors.form && <Text style={styles.formError}>{errors.form}</Text>}
      <Input
        label="Current password"
        value={currentPassword}
        onChangeText={setCurrentPassword}
        secureTextEntry
        error={errors.currentPassword}
      />
      <Input
        label="New password"
        value={newPassword}
        onChangeText={setNewPassword}
        secureTextEntry
        error={errors.newPassword}
      />
      <Input
        label="Confirm new password"
        value={confirmPassword}
        onChangeText={setConfirmPassword}
        secureTextEntry
        error={errors.confirmPassword}
      />
      <Button title="Update password" onPress={handleSubmit} loading={changePassword.isPending} fullWidth size="lg" />
      <Text style={styles.section}>Account</Text>
      <Card padded={false} style={styles.signOut}>
        <ListRow
          title="Sign out"
          icon="log-out-outline"
          tone="red"
          onPress={async () => {
            await signOut();
            router.replace('/(auth)/welcome');
          }}
        />
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md },
  title: { fontFamily: FONT_BOLD, fontSize: 28, color: theme.colors.text, letterSpacing: -0.4, marginBottom: 12 },
  profile: { marginBottom: theme.spacing.md },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  profileCopy: { flex: 1, minWidth: 0, gap: 4 },
  name: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text },
  email: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  section: { fontFamily: FONT_SEMIBOLD, fontSize: 13, letterSpacing: 0.4, textTransform: 'uppercase', color: theme.colors.textMuted, marginBottom: 8, marginTop: 8 },
  signOut: { marginTop: 4, marginBottom: 24 },
  hint: { color: theme.colors.textSecondary, marginBottom: theme.spacing.lg, lineHeight: 20, fontFamily: FONT_MEDIUM },
  successBanner: {
    backgroundColor: theme.colors.successLight,
    borderRadius: theme.radius.md,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.success,
  },
  successText: { color: theme.colors.success, fontWeight: '600' },
  formError: { color: theme.colors.error, marginBottom: theme.spacing.md },
});
