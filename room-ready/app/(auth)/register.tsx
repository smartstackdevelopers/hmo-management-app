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
import { ROLE_DESCRIPTIONS, ROLE_LABELS, UserRole } from '@/types';

const ROLES: UserRole[] = ['landlord', 'tenant', 'property_manager', 'contractor'];

const ROLE_ICONS: Record<UserRole, keyof typeof Ionicons.glyphMap> = {
  landlord: 'business-outline',
  tenant: 'person-outline',
  property_manager: 'clipboard-outline',
  contractor: 'construct-outline',
  admin: 'shield-outline',
};

export default function RegisterScreen() {
  const insets = useSafeAreaInsets();
  const { signUp } = useAuth();
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>('landlord');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleRegister() {
    if (!firstName.trim() || !lastName.trim() || !email.trim() || !password.trim()) {
      setError('Please complete all fields');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await signUp({ firstName, lastName, email, password, role });
      router.replace('/(app)/(tabs)');
    } catch {
      setError('Unable to create account. Please try again.');
    } finally {
      setLoading(false);
    }
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
        <Link href="/(auth)/welcome" asChild>
          <Pressable style={styles.back} accessibilityLabel="Go back">
            <Ionicons name="chevron-back" size={22} color={theme.colors.secondary} />
            <Text style={styles.backText}>Back</Text>
          </Pressable>
        </Link>

        <RoomReadyLogo size="sm" />
        <Text style={styles.title}>Create account</Text>
        <Text style={styles.subtitle}>Join Room Ready in under a minute</Text>

        <Card style={styles.formCard}>
          <View style={styles.nameRow}>
            <View style={styles.nameField}>
              <Input label="First name" value={firstName} onChangeText={setFirstName} autoComplete="given-name" placeholder="Jane" editable={!loading} />
            </View>
            <View style={styles.nameField}>
              <Input label="Last name" value={lastName} onChangeText={setLastName} autoComplete="family-name" placeholder="Smith" editable={!loading} />
            </View>
          </View>

          <Input label="Email" value={email} onChangeText={setEmail} keyboardType="email-address" autoCapitalize="none" autoComplete="email" placeholder="you@example.com" editable={!loading} />
          <Input label="Password" value={password} onChangeText={setPassword} secureTextEntry autoComplete="new-password" placeholder="Min. 8 characters" editable={!loading} />

          <Text style={styles.roleLabel}>I am a...</Text>
          <View style={styles.roleGrid}>
            {ROLES.map((r) => {
              const selected = role === r;
              return (
                <Pressable
                  key={r}
                  onPress={() => setRole(r)}
                  style={[styles.roleCard, selected && styles.roleCardSelected]}
                  accessibilityRole="radio"
                  accessibilityState={{ selected }}
                >
                  <View style={[styles.roleIcon, selected && styles.roleIconSelected]}>
                    <Ionicons name={ROLE_ICONS[r]} size={20} color={selected ? theme.colors.textInverse : theme.colors.secondary} />
                  </View>
                  <Text style={[styles.roleTitle, selected && styles.roleTitleSelected]}>{ROLE_LABELS[r]}</Text>
                  <Text style={[styles.roleDesc, selected && styles.roleDescSelected]} numberOfLines={2}>
                    {ROLE_DESCRIPTIONS[r]}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}
          <Button title="Create Account" onPress={handleRegister} loading={loading} fullWidth size="lg" />
        </Card>

        <Text style={styles.footer}>
          Already have an account?{' '}
          <Link href="/(auth)/login" style={styles.link}>Sign in</Link>
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: theme.colors.background },
  container: { flexGrow: 1, paddingHorizontal: theme.spacing.lg },
  back: { flexDirection: 'row', alignItems: 'center', gap: 2, marginBottom: theme.spacing.md },
  backText: { color: theme.colors.secondary, fontSize: 15, fontWeight: '600' },
  title: { ...theme.typography.h2, color: theme.colors.text, marginTop: theme.spacing.sm },
  subtitle: { fontSize: 14, color: theme.colors.textSecondary, marginTop: 4, marginBottom: theme.spacing.md },
  formCard: { marginBottom: theme.spacing.md },
  nameRow: { flexDirection: 'row', gap: theme.spacing.sm },
  nameField: { flex: 1 },
  roleLabel: { ...theme.typography.label, color: theme.colors.text, marginBottom: theme.spacing.sm },
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
  roleCardSelected: { borderColor: theme.colors.secondary, backgroundColor: theme.colors.infoLight },
  roleIcon: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  roleIconSelected: { backgroundColor: theme.colors.secondary },
  roleTitle: { fontWeight: '700', fontSize: 13, color: theme.colors.text, textAlign: 'center' },
  roleTitleSelected: { color: theme.colors.secondary },
  roleDesc: { fontSize: 11, color: theme.colors.textMuted, textAlign: 'center', lineHeight: 15 },
  roleDescSelected: { color: theme.colors.textSecondary },
  error: { color: theme.colors.error, marginBottom: theme.spacing.md, fontSize: 14 },
  footer: { textAlign: 'center', color: theme.colors.textSecondary, marginTop: theme.spacing.lg },
  link: { color: theme.colors.secondary, fontWeight: '600' },
});
