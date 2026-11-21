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

import { BrandHeader } from '@/components/ui/BrandHeader';
import { Button } from '@/components/ui/Button';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { Input } from '@/components/ui/Input';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { type PublicRegisterRole, useAuth } from '@/contexts/AuthContext';
import { LegacyApiConfigurationError } from '@/lib/legacyApiConfig';

type RoleOption = {
  value: PublicRegisterRole;
  label: string;
  description: string;
  icon: keyof typeof Ionicons.glyphMap;
};

const ROLES: RoleOption[] = [
  {
    value: 'landlord',
    label: 'Landlord',
    description: 'Manage properties, tenants and repairs',
    icon: 'business-outline',
  },
  {
    value: 'tenant',
    label: 'Tenant',
    description: 'Your tenancy, repairs and documents',
    icon: 'person-outline',
  },
  {
    value: 'support_worker',
    label: 'Support Worker',
    description: 'Caseload, notes, visits and incidents',
    icon: 'people-outline',
  },
  {
    value: 'maintenance_contractor',
    label: 'Maintenance Contractor',
    description: 'Jobs, progress updates and invoices',
    icon: 'construct-outline',
  },
];

export default function RegisterScreen() {
  const insets = useSafeAreaInsets();
  const { signUp, authMode } = useAuth();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [role, setRole] = useState<PublicRegisterRole>('landlord');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleRegister() {
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password.trim()) {
      setError('Please complete all required fields');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (!termsAccepted || !privacyAccepted) {
      setError('Please accept Terms and Privacy to continue');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await signUp({
        firstName,
        lastName,
        email,
        password,
        confirmPassword,
        role,
        phone: phone.trim() || undefined,
        termsAccepted,
        privacyAccepted,
      });
      router.replace('/(auth)/pending');
    } catch (err) {
      if (err instanceof LegacyApiConfigurationError) {
        setError('Self-registration is not available in this build.');
      } else {
        setError(err instanceof Error ? err.message : 'Unable to create account. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }

  if (authMode === 'auth0') {
    return (
      <View style={[styles.flex, styles.gate, { paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 }]}>
        <FocusStatusBar style="dark" />
        <BrandHeader
          size="sm"
          title="Organisation sign-in"
          subtitle="New accounts are created by your organisation. Use the sign-in screen to continue with Auth0."
        />
        <Link href="/(auth)/login" asChild>
          <Button title="Go to sign in" size="lg" fullWidth />
        </Link>
      </View>
    );
  }

  if (authMode !== 'native' && authMode !== 'demo') {
    return (
      <View style={[styles.flex, styles.gate, { paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 }]}>
        <FocusStatusBar style="dark" />
        <BrandHeader
          size="sm"
          title="No self-registration"
          subtitle="Turn on native auth in room-ready/.env (EXPO_PUBLIC_NATIVE_AUTH=1, EXPO_PUBLIC_DEMO_AUTH=0), restart Expo, then create your account here."
        />
        <Link href="/(auth)/login" asChild>
          <Button title="Go to sign in" size="lg" fullWidth />
        </Link>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView
        contentContainerStyle={[
          styles.container,
          { paddingTop: insets.top + theme.spacing.md, paddingBottom: insets.bottom + 16 },
        ]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <FocusStatusBar style="dark" />
        <Link href="/(auth)/welcome" asChild>
          <Pressable style={styles.back} accessibilityRole="button" accessibilityLabel="Go back">
            <Text style={styles.backText}>Back</Text>
          </Pressable>
        </Link>

        <BrandHeader
          size="sm"
          title="Create your account"
          subtitle="Choose your role. An admin approves every new account."
        />

        <View>
          <View style={styles.nameRow}>
            <View style={styles.nameField}>
              <Input
                label="First name"
                value={firstName}
                onChangeText={setFirstName}
                autoComplete="given-name"
                placeholder="Jane"
                editable={!loading}
              />
            </View>
            <View style={styles.nameField}>
              <Input
                label="Last name"
                value={lastName}
                onChangeText={setLastName}
                autoComplete="family-name"
                placeholder="Smith"
                editable={!loading}
              />
            </View>
          </View>

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
            label="Phone (optional)"
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
            placeholder="+44..."
            editable={!loading}
          />
          <Input
            label="Password"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="new-password"
            placeholder="Min. 8 characters"
            editable={!loading}
          />
          <Input
            label="Confirm password"
            value={confirmPassword}
            onChangeText={setConfirmPassword}
            secureTextEntry
            autoComplete="new-password"
            placeholder="Re-enter password"
            editable={!loading}
          />

          <Text style={styles.roleLabel}>I am a…</Text>
          <View style={styles.roleGrid}>
            {ROLES.map((r) => {
              const selected = role === r.value;
              return (
                <Pressable
                  key={r.value}
                  onPress={() => setRole(r.value)}
                  style={[styles.roleCard, selected && styles.roleCardSelected]}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                >
                  <View style={[styles.roleIcon, selected && styles.roleIconSelected]}>
                    <Ionicons
                      name={r.icon}
                      size={20}
                      color={selected ? theme.colors.textInverse : theme.colors.secondaryDark}
                    />
                  </View>
                  <Text style={[styles.roleTitle, selected && styles.roleTitleSelected]}>{r.label}</Text>
                  <Text style={[styles.roleDesc, selected && styles.roleDescSelected]} numberOfLines={2}>
                    {r.description}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <Pressable
            style={styles.checkRow}
            onPress={() => setTermsAccepted((v) => !v)}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: termsAccepted }}
          >
            <Ionicons
              name={termsAccepted ? 'checkbox' : 'square-outline'}
              size={22}
              color={theme.colors.secondary}
            />
            <Text style={styles.checkText}>I accept the Terms of Use</Text>
          </Pressable>
          <Pressable
            style={styles.checkRow}
            onPress={() => setPrivacyAccepted((v) => !v)}
            accessibilityRole="checkbox"
            accessibilityState={{ checked: privacyAccepted }}
          >
            <Ionicons
              name={privacyAccepted ? 'checkbox' : 'square-outline'}
              size={22}
              color={theme.colors.secondary}
            />
            <Text style={styles.checkText}>I accept the Privacy Policy</Text>
          </Pressable>

          {error ? (
            <View style={styles.banner} accessibilityRole="alert">
              <Text style={styles.error}>{error}</Text>
            </View>
          ) : null}
          <Button title="Request access" onPress={handleRegister} loading={loading} fullWidth size="lg" />
        </View>

        <Text style={styles.footer}>
          Already registered?{' '}
          <Link href="/(auth)/login" style={styles.link}>
            Sign in
          </Link>
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: theme.colors.background },
  gate: { paddingHorizontal: theme.spacing.lg },
  container: {
    flexGrow: 1,
    paddingHorizontal: theme.spacing.lg,
    maxWidth: theme.layout.phoneMaxWidth,
    width: '100%',
    alignSelf: 'center',
  },
  back: { minHeight: 44, justifyContent: 'center', alignSelf: 'flex-start', marginBottom: theme.spacing.xs },
  backText: { color: theme.colors.secondaryDark, fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
  nameRow: { flexDirection: 'row', gap: theme.spacing.sm },
  nameField: { flex: 1 },
  roleLabel: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  roleGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  roleCard: {
    width: '48%',
    flexGrow: 1,
    padding: theme.spacing.sm,
    borderRadius: theme.radius.lg,
    borderWidth: 1.5,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    gap: 6,
    minHeight: 118,
  },
  roleCardSelected: { borderColor: theme.colors.secondaryDark, backgroundColor: theme.colors.accentLight },
  roleIcon: {
    width: 44,
    height: 44,
    borderRadius: 14,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  roleIconSelected: { backgroundColor: theme.colors.secondaryDark },
  roleTitle: { fontFamily: FONT_BOLD, fontWeight: '700', fontSize: 13, color: theme.colors.text, textAlign: 'center' },
  roleTitleSelected: { color: theme.colors.secondaryDark },
  roleDesc: { fontSize: 12, fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, textAlign: 'center', lineHeight: 16 },
  roleDescSelected: { color: theme.colors.textSecondary },
  checkRow: { flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 44, marginBottom: 4 },
  checkText: { flex: 1, fontSize: 15, fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 20 },
  banner: {
    backgroundColor: theme.colors.errorLight,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: '#FECACA',
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginBottom: theme.spacing.md,
  },
  error: { color: theme.colors.error, fontSize: 14, lineHeight: 20, fontFamily: FONT_MEDIUM, textAlign: 'center' },
  footer: {
    textAlign: 'center',
    color: theme.colors.textSecondary,
    fontFamily: FONT_MEDIUM,
    fontSize: 14,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.md,
  },
  link: { color: theme.colors.secondaryDark, fontFamily: FONT_SEMIBOLD, fontWeight: '600' },
});
