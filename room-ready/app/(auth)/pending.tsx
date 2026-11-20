import { Ionicons } from '@expo/vector-icons';
import { Link, router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

type StepState = 'done' | 'current' | 'next';

const STEPS: { title: string; body: string; state: StepState }[] = [
  { title: 'Request sent', body: 'We have your details and requested role.', state: 'done' },
  { title: 'Admin review', body: 'Your housing provider checks your request — usually within 1 working day.', state: 'current' },
  { title: 'Access granted', body: 'You will be able to sign in and see your home screen.', state: 'next' },
];

export default function PendingApprovalScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.flex, { paddingTop: insets.top + 32, paddingBottom: insets.bottom + 24 }]}>
      <RoomReadyLogo size="sm" />
      <View style={styles.heroIcon}>
        <Ionicons name="time-outline" size={34} color={theme.colors.secondaryDark} />
      </View>
      <Text style={styles.title}>You’re almost in</Text>
      <Text style={styles.lead}>Your account is waiting for approval. You don’t need to do anything else right now.</Text>
      <Card style={styles.card}>
        {STEPS.map((step, index) => (
          <View key={step.title} style={styles.stepRow}>
            <View style={styles.rail}>
              <View
                style={[
                  styles.dot,
                  step.state === 'done' && styles.dotDone,
                  step.state === 'current' && styles.dotCurrent,
                ]}
              >
                {step.state === 'done' ? <Ionicons name="checkmark" size={14} color={theme.colors.textInverse} /> : null}
              </View>
              {index < STEPS.length - 1 ? (
                <View style={[styles.line, step.state === 'done' && styles.lineDone]} />
              ) : null}
            </View>
            <View style={styles.stepText}>
              <Text style={[styles.stepTitle, step.state === 'next' && styles.stepTitleMuted]}>{step.title}</Text>
              <Text style={styles.stepBody}>{step.body}</Text>
            </View>
          </View>
        ))}
      </Card>
      <Button title="Go to sign in" onPress={() => router.replace('/(auth)/login')} fullWidth size="lg" />
      <Link href="/(auth)/welcome" asChild>
        <Pressable style={styles.secondary} accessibilityRole="link">
          <Text style={styles.link}>Back to welcome</Text>
        </Pressable>
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: theme.colors.background,
    paddingHorizontal: theme.spacing.lg,
  },
  heroIcon: {
    width: 68,
    height: 68,
    borderRadius: theme.radius.xl,
    backgroundColor: theme.colors.accentLight,
    borderWidth: 1,
    borderColor: theme.colors.accentSoft,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: theme.spacing.xl,
  },
  title: {
    ...theme.typography.h1,
    fontFamily: FONT_BOLD,
    color: theme.colors.text,
    marginTop: theme.spacing.md,
  },
  lead: {
    fontSize: 15,
    lineHeight: 22,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.sm,
    marginBottom: theme.spacing.lg,
  },
  card: { marginBottom: theme.spacing.lg },
  stepRow: { flexDirection: 'row', gap: theme.spacing.md },
  rail: { alignItems: 'center', width: 24 },
  dot: {
    width: 24,
    height: 24,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dotDone: { backgroundColor: theme.colors.secondaryDark, borderColor: theme.colors.secondaryDark },
  dotCurrent: { borderColor: theme.colors.secondaryDark, borderWidth: 6 },
  line: { flex: 1, width: 2, minHeight: 28, backgroundColor: theme.colors.border, marginVertical: 2 },
  lineDone: { backgroundColor: theme.colors.secondaryDark },
  stepText: { flex: 1, paddingBottom: theme.spacing.md },
  stepTitle: { fontSize: 15, fontFamily: FONT_SEMIBOLD, color: theme.colors.text },
  stepTitleMuted: { color: theme.colors.textMuted },
  stepBody: { fontSize: 13, lineHeight: 19, color: theme.colors.textSecondary, marginTop: 2 },
  secondary: { alignItems: 'center', marginTop: theme.spacing.lg, minHeight: 44, justifyContent: 'center' },
  link: { color: theme.colors.secondaryDark, fontFamily: FONT_SEMIBOLD, fontSize: 15 },
});
