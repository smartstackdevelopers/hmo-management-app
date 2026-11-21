import { Link, router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Linking, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { BrandHeader } from '@/components/ui/BrandHeader';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { Input } from '@/components/ui/Input';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
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
      <ScrollView
        contentContainerStyle={[
          styles.container,
          { paddingTop: insets.top + 12, paddingBottom: insets.bottom + 24 },
        ]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <FocusStatusBar style="dark" />
        <Pressable style={styles.back} onPress={() => router.back()} accessibilityRole="button" accessibilityLabel="Go back">
          <Text style={styles.backText}>Back</Text>
        </Pressable>

        <BrandHeader
          size="sm"
          title="Reset password"
          subtitle="Enter your email and we'll send you a secure reset link."
        />

        {isAuthenticated && (
          <Card style={styles.tipCard} variant="tinted">
            <Text style={styles.tipTitle}>Already signed in?</Text>
            <Text style={styles.tipBody}>Change your password from Account → Privacy & Security.</Text>
            <Button title="Change password" variant="secondary" size="sm" onPress={() => router.push('/(app)/security')} />
          </Card>
        )}

        {!submitted ? (
          <View>
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholder="you@example.com"
              error={error || undefined}
            />
            <Button title="Send reset link" onPress={handleSubmit} fullWidth size="lg" />
            <Link href="/(auth)/login" asChild>
              <Pressable style={styles.linkBtn} accessibilityRole="link">
                <Text style={styles.link}>Back to sign in</Text>
              </Pressable>
            </Link>
          </View>
        ) : (
          <View style={styles.success}>
            <View style={styles.successIcon}>
              <Ionicons name="mail-outline" size={32} color={theme.colors.secondaryDark} />
            </View>
            <Text style={styles.successTitle}>Check your inbox</Text>
            <Text style={styles.successBody}>
              If an account exists for {email}, you'll receive password reset instructions shortly.
            </Text>
            <Text style={styles.successNote}>Demo accounts use the password Password123.</Text>
            <Link href="/(auth)/login" asChild>
              <Button title="Back to sign in" size="lg" fullWidth style={styles.successAction} />
            </Link>
          </View>
        )}

        <Pressable
          style={styles.support}
          onPress={() => Linking.openURL(`mailto:${BIRMINGHAM_COUNCIL.licensingEmail}`)}
          accessibilityRole="link"
        >
          <Text style={styles.supportBody}>
            Need help? Email {BIRMINGHAM_COUNCIL.licensingEmail} or call {BIRMINGHAM_COUNCIL.licensingPhone}.
          </Text>
        </Pressable>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: theme.colors.background },
  container: {
    flexGrow: 1,
    paddingHorizontal: theme.spacing.lg,
    maxWidth: theme.layout.phoneMaxWidth,
    width: '100%',
    alignSelf: 'center',
  },
  back: { minHeight: 44, justifyContent: 'center', alignSelf: 'flex-start', marginBottom: theme.spacing.sm },
  backText: { color: theme.colors.secondaryDark, fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
  tipCard: { marginBottom: theme.spacing.md, gap: 8 },
  tipTitle: { fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text },
  tipBody: { color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20, fontFamily: FONT_MEDIUM },
  linkBtn: { minHeight: 44, alignItems: 'center', justifyContent: 'center', marginTop: 4 },
  link: { color: theme.colors.secondaryDark, fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15 },
  success: { alignItems: 'center' },
  successIcon: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
  },
  successTitle: {
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    fontSize: 20,
    color: theme.colors.text,
    textAlign: 'center',
  },
  successBody: {
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    fontSize: 15,
    fontFamily: FONT_MEDIUM,
    marginTop: 8,
  },
  successNote: {
    color: theme.colors.textMuted,
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    textAlign: 'center',
    marginTop: 8,
  },
  successAction: { marginTop: theme.spacing.lg },
  support: { minHeight: 44, justifyContent: 'center', marginTop: theme.spacing.lg },
  supportBody: {
    color: theme.colors.textMuted,
    lineHeight: 20,
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    textAlign: 'center',
  },
});
