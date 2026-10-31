import { Link, router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';

export default function ForgotPasswordScreen() {
  const insets = useSafeAreaInsets();
  const { isAuthenticated } = useAuth();
  const [email, setEmail] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  function handleSubmit() {
    if (!email.trim() || !email.includes('@')) {
      setError('Enter a valid email address');
      return;
    }
    setError('');
    setSubmitted(true);
  }

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <View style={[styles.container, { paddingTop: insets.top + theme.spacing.md, paddingBottom: insets.bottom + 24 }]}>
        <Pressable style={styles.back} onPress={() => router.back()} accessibilityLabel="Go back">
          <Ionicons name="chevron-back" size={22} color={theme.colors.secondary} />
          <Text style={styles.backText}>Back</Text>
        </Pressable>

        <RoomReadyLogo size="sm" />
        <Text style={styles.title}>Reset password</Text>
        <Text style={styles.subtitle}>
          Enter your email and we&apos;ll send reset instructions when email recovery is enabled for your account.
        </Text>

        {isAuthenticated && (
          <Card style={styles.tipCard}>
            <Text style={styles.tipTitle}>Already signed in?</Text>
            <Text style={styles.tipBody}>Change your password instantly from Account → Privacy & Security.</Text>
            <Button title="Change Password Now" variant="secondary" size="sm" onPress={() => router.push('/(app)/security')} />
          </Card>
        )}

        {!submitted ? (
          <Card style={styles.formCard}>
            <Input
              label="Email address"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholder="you@example.com"
              error={error || undefined}
            />
            <Button title="Send Reset Link" onPress={handleSubmit} fullWidth size="lg" />
          </Card>
        ) : (
          <Card style={styles.successCard}>
            <Ionicons name="mail-outline" size={32} color={theme.colors.secondary} />
            <Text style={styles.successTitle}>Check your inbox</Text>
            <Text style={styles.successBody}>
              If an account exists for {email}, you&apos;ll receive password reset instructions shortly.
            </Text>
            <Text style={styles.successNote}>
              Email reset is being rolled out. Demo accounts use password: Password123
            </Text>
          </Card>
        )}

        <Card style={styles.supportCard}>
          <Text style={styles.supportTitle}>Need help?</Text>
          <Text style={styles.supportBody}>
            Contact {BIRMINGHAM_COUNCIL.licensingEmail} or call {BIRMINGHAM_COUNCIL.licensingPhone}.
          </Text>
        </Card>

        <Link href="/(auth)/login" style={styles.link}>Return to sign in</Link>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: theme.colors.background },
  container: { flex: 1, paddingHorizontal: theme.spacing.lg },
  back: { flexDirection: 'row', alignItems: 'center', gap: 2, marginBottom: theme.spacing.lg },
  backText: { color: theme.colors.secondary, fontSize: 15, fontWeight: '600' },
  title: { ...theme.typography.h2, color: theme.colors.text, marginTop: theme.spacing.sm },
  subtitle: { color: theme.colors.textSecondary, marginTop: theme.spacing.sm, lineHeight: 22, marginBottom: theme.spacing.lg },
  tipCard: { marginBottom: theme.spacing.md, backgroundColor: theme.colors.infoLight, borderColor: theme.colors.info, gap: 8 },
  tipTitle: { fontWeight: '700', color: theme.colors.text },
  tipBody: { color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20 },
  formCard: { marginBottom: theme.spacing.md },
  successCard: { alignItems: 'center', marginBottom: theme.spacing.md, gap: 8, paddingVertical: theme.spacing.lg },
  successTitle: { fontWeight: '700', fontSize: 18, color: theme.colors.text, marginTop: 4 },
  successBody: { color: theme.colors.textSecondary, textAlign: 'center', lineHeight: 22, fontSize: 14 },
  successNote: { color: theme.colors.textMuted, fontSize: 12, textAlign: 'center', marginTop: 4 },
  supportCard: { marginBottom: theme.spacing.md },
  supportTitle: { fontWeight: '700', color: theme.colors.text, marginBottom: 6 },
  supportBody: { color: theme.colors.textSecondary, lineHeight: 22, fontSize: 14 },
  link: { textAlign: 'center', color: theme.colors.secondary, fontWeight: '600' },
});
