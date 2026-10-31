import { Link, router } from 'expo-router';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';

const DEMO_ACCOUNTS = [
  { label: 'Landlord', email: 'landlord@roomready.co.uk' },
  { label: 'Tenant', email: 'tenant@roomready.co.uk' },
];

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSignIn(loginEmail?: string, passwordOverride?: string) {
    const targetEmail = loginEmail ?? email;
    const targetPassword = passwordOverride ?? password;
    if (!targetEmail.trim() || !targetPassword.trim()) {
      setError('Please enter your email and password');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await signIn(targetEmail, targetPassword);
      router.replace('/(app)/(tabs)');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView
        contentContainerStyle={[styles.page, { paddingTop: insets.top + 16, paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Link href="/(auth)/welcome" asChild>
          <Pressable style={styles.back}>
            <Ionicons name="arrow-back" size={20} color={theme.colors.text} />
            <Text style={styles.backText}>Back</Text>
          </Pressable>
        </Link>

        <RoomReadyLogo size="sm" />
        <Text style={styles.title}>Sign in</Text>
        <Text style={styles.subtitle}>Welcome back to Room Ready</Text>

        <Card style={styles.formCard}>
          <Input
            label="Email"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
            placeholder="you@example.com"
            editable={!loading}
          />
          <Input
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="password"
            placeholder="Your password"
            editable={!loading}
            error={error || undefined}
          />
          <Link href="/(auth)/forgot-password" asChild>
            <Pressable style={styles.forgot}>
              <Text style={styles.forgotText}>Forgot password?</Text>
            </Pressable>
          </Link>
          <Button title="Sign in" onPress={() => handleSignIn()} loading={loading} fullWidth size="lg" variant="secondary" />
        </Card>

        <Text style={styles.demoLabel}>Try demo</Text>
        <View style={styles.demoRow}>
          {DEMO_ACCOUNTS.map((demo) => (
            <Pressable
              key={demo.email}
              style={styles.demoChip}
              onPress={() => {
                setEmail(demo.email);
                setPassword('Password123');
                handleSignIn(demo.email, 'Password123');
              }}
            >
              <Text style={styles.demoChipText}>{demo.label}</Text>
            </Pressable>
          ))}
        </View>

        <Text style={styles.footer}>
          No account? <Link href="/(auth)/register" style={styles.link}>Sign up</Link>
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: theme.colors.background,
    minHeight: Platform.OS === 'web' ? ('100dvh' as unknown as number) : undefined,
  },
  page: {
    flexGrow: 1,
    paddingHorizontal: theme.spacing.lg,
    maxWidth: theme.layout.phoneMaxWidth,
    width: '100%',
    alignSelf: 'center',
  },
  back: { flexDirection: 'row', alignItems: 'center', gap: 4, marginBottom: theme.spacing.lg },
  backText: { fontSize: 15, fontWeight: '500', color: theme.colors.text },
  title: { ...theme.typography.h1, color: theme.colors.text, marginTop: theme.spacing.md },
  subtitle: { fontSize: 15, color: theme.colors.textSecondary, marginTop: 4, marginBottom: theme.spacing.lg },
  formCard: { marginBottom: theme.spacing.lg },
  forgot: { alignSelf: 'flex-end', marginBottom: theme.spacing.md, marginTop: -4 },
  forgotText: { color: theme.colors.secondary, fontSize: 14, fontWeight: '600' },
  demoLabel: { fontSize: 13, color: theme.colors.textMuted, marginBottom: theme.spacing.sm },
  demoRow: { flexDirection: 'row', gap: theme.spacing.sm },
  demoChip: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    paddingVertical: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  demoChipText: { fontWeight: '600', color: theme.colors.text, fontSize: 14 },
  footer: {
    textAlign: 'center',
    color: theme.colors.textSecondary,
    fontSize: 14,
    marginTop: theme.spacing.xl,
    paddingTop: theme.spacing.lg,
  },
  link: { color: theme.colors.secondary, fontWeight: '600' },
});
