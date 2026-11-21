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

import { BrandHeader } from '@/components/ui/BrandHeader';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { Input } from '@/components/ui/Input';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import {
  getAuth0RedirectUriHint,
  isAuth0MobileConfigured,
  readAuth0ConfigFromEnv,
} from '@/lib/hmoreAuth0';
import { DEMO_ROLES } from '@/lib/hmoreDemoAuth';

const DEMO_ACCOUNTS = [
  { label: 'Landlord', email: 'landlord@roomready.co.uk' },
  { label: 'Tenant', email: 'tenant@roomready.co.uk' },
];

function legacyPasswordApiConfigured(): boolean {
  return Boolean(process.env.EXPO_PUBLIC_API_URL?.trim());
}

export default function LoginScreen() {
  const insets = useSafeAreaInsets();
  const { signIn, signInWithAuth0, signInWithDemoRole, authMode } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const subtitle =
    authMode === 'demo'
      ? 'Local demo — choose a role to continue.'
      : authMode === 'native'
        ? 'Sign in with your approved HMore account.'
        : authMode === 'auth0'
          ? 'Use your organisation account.'
          : 'Sign in with your approved HMore account.';

  async function handleDemo(role: (typeof DEMO_ROLES)[number]['role']) {
    setError('');
    setLoading(true);
    try {
      await signInWithDemoRole(role);
      router.replace('/(app)/(tabs)');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Demo login failed.');
    } finally {
      setLoading(false);
    }
  }

  async function handleAuth0() {
    setError('');
    setLoading(true);
    try {
      await signInWithAuth0();
      router.replace('/(app)/(tabs)');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unable to sign in.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

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
        contentContainerStyle={[styles.page, { paddingTop: insets.top + 8, paddingBottom: insets.bottom + 24 }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <FocusStatusBar style="dark" />
        <Link href="/(auth)/welcome" asChild>
          <Pressable style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
            <Text style={styles.backText}>Back</Text>
          </Pressable>
        </Link>

        <BrandHeader size="sm" title="Welcome back" subtitle={subtitle} />

        {error ? (
          <View style={styles.banner} accessibilityRole="alert" accessibilityLiveRegion="polite">
            <Text style={styles.bannerText}>{error}</Text>
          </View>
        ) : null}

        {authMode === 'native' ? (
          <View>
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholder="sara@example.co.uk"
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
              error={error ? 'Please check this field' : undefined}
            />
            <Button title="Sign in" onPress={() => handleSignIn()} loading={loading} fullWidth size="lg" />
            <Link href="/(auth)/forgot-password" asChild>
              <Pressable style={styles.linkBtn} accessibilityRole="link">
                <Text style={styles.link}>Forgot password?</Text>
              </Pressable>
            </Link>
          </View>
        ) : authMode === 'demo' ? (
          <Card style={styles.formCard} variant="outlined">
            <Text style={styles.copy}>
              Dummy authentication for local demos only. Each button signs in as that HMore role against FastAPI and
              PostgreSQL, not Auth0.
            </Text>
            <View style={styles.stack}>
              {DEMO_ROLES.map((item) => (
                <Button
                  key={item.role}
                  title={item.label}
                  onPress={() => handleDemo(item.role)}
                  loading={loading}
                  fullWidth
                  size="lg"
                />
              ))}
            </View>
          </Card>
        ) : authMode === 'auth0' ? (
          <Card style={styles.formCard} variant="outlined">
            <Text style={styles.copy}>
              Sign in with Auth0. The app stores the session on this device and talks to the HMore API. Password sign-in
              is turned off while organisation login is configured.
            </Text>
            {isAuth0MobileConfigured() ? (
              <Text style={styles.callbackHint} selectable>
                Auth0 → Allowed Callback URLs must include:{'\n'}
                {getAuth0RedirectUriHint(readAuth0ConfigFromEnv()?.scheme)}
                {'\n'}Also add: roomready://auth/callback
              </Text>
            ) : null}
            <Button title="Continue with organisation login" onPress={handleAuth0} loading={loading} fullWidth size="lg" />
          </Card>
        ) : !legacyPasswordApiConfigured() ? (
          <Card style={styles.formCard} variant="outlined">
            <Text style={styles.copy}>
              HMore uses Auth0 (port 8000), not email and password on this build. Run scripts\sync-mobile-env-from-web.py,
              set EXPO_PUBLIC_AUTH0_CLIENT_ID (Native app in Auth0), restart Expo, then use organisation login.
            </Text>
            <Text style={styles.copy}>
              Do not use Try demo (Password123) — that needs the old EXPO_PUBLIC_API_URL on port 3001.
            </Text>
          </Card>
        ) : (
          <View>
            <Input
              label="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              placeholder="sara@example.co.uk"
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
              error={error ? 'Please check this field' : undefined}
            />
            <Button title="Sign in" onPress={() => handleSignIn()} loading={loading} fullWidth size="lg" />
            <Link href="/(auth)/forgot-password" asChild>
              <Pressable style={styles.linkBtn} accessibilityRole="link">
                <Text style={styles.link}>Forgot password?</Text>
              </Pressable>
            </Link>
            <Text style={styles.demoLabel}>Try demo</Text>
            <View style={styles.demoRow}>
              {DEMO_ACCOUNTS.map((demo) => (
                <Pressable
                  key={demo.email}
                  style={styles.demoChip}
                  accessibilityRole="button"
                  accessibilityLabel={`Try demo as ${demo.label}`}
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
          </View>
        )}

        <Text style={styles.footer}>
          New here?{' '}
          <Link href="/(auth)/register" style={styles.link}>
            Create account
          </Link>
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
  back: { minHeight: 44, justifyContent: 'center', alignSelf: 'flex-start', marginBottom: theme.spacing.xs },
  backText: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.secondaryDark },
  banner: {
    backgroundColor: theme.colors.errorLight,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: '#FECACA',
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: theme.spacing.md,
  },
  bannerText: {
    color: theme.colors.error,
    fontSize: 14,
    lineHeight: 20,
    fontFamily: FONT_MEDIUM,
    textAlign: 'center',
  },
  formCard: { marginBottom: theme.spacing.md },
  copy: {
    fontSize: 15,
    lineHeight: 22,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
  },
  stack: { gap: 8 },
  linkBtn: { minHeight: 44, alignItems: 'center', justifyContent: 'center' },
  link: { color: theme.colors.secondaryDark, fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15 },
  demoLabel: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.sm,
  },
  demoRow: { flexDirection: 'row', gap: theme.spacing.sm },
  demoChip: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.md,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
    paddingHorizontal: 8,
  },
  demoChipText: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text, fontSize: 14 },
  footer: {
    textAlign: 'center',
    color: theme.colors.textSecondary,
    fontSize: 14,
    fontFamily: FONT_MEDIUM,
    marginTop: 'auto',
    paddingTop: theme.spacing.xl,
  },
  callbackHint: {
    fontSize: 12,
    lineHeight: 18,
    color: theme.colors.textMuted,
    marginBottom: theme.spacing.md,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
});
