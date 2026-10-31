import { router } from 'expo-router';
import { useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { theme } from '@/constants/theme';
import { useChangePassword } from '@/hooks/useApi';

export default function SecurityScreen() {
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
      <Text style={styles.hint}>Update your account password. Use at least 8 characters.</Text>
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
      <Button title="Update Password" onPress={handleSubmit} loading={changePassword.isPending} fullWidth size="lg" />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md },
  hint: { color: theme.colors.textSecondary, marginBottom: theme.spacing.lg, lineHeight: 20 },
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
