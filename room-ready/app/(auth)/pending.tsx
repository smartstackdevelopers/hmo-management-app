import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Button } from '@/components/ui/Button';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

const STEPS = [
  { title: 'Account created', done: true },
  { title: 'Admin review', done: false },
  { title: 'Access granted', done: false },
];

export default function PendingApprovalScreen() {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.flex, { paddingTop: insets.top + 36, paddingBottom: insets.bottom + 16 }]}>
      <FocusStatusBar style="dark" />
      <View style={styles.body}>
        <View style={styles.heroIcon}>
          <Ionicons name="time-outline" size={36} color={theme.colors.warning} />
        </View>
        <Text style={styles.title} accessibilityRole="header">Request sent</Text>
        <Text style={styles.lead}>
          An administrator will review your request. We’ll notify you as soon as you’re approved.
        </Text>
        <View style={styles.steps}>
          {STEPS.map((step) => (
            <View key={step.title} style={styles.stepRow}>
              <View style={[styles.dot, step.done && styles.dotDone]}>
                {step.done ? <Ionicons name="checkmark" size={16} color={theme.colors.textInverse} /> : null}
              </View>
              <Text style={[styles.stepTitle, !step.done && styles.stepTitleMuted]}>{step.title}</Text>
            </View>
          ))}
        </View>
      </View>
      <Button title="Back to sign in" onPress={() => router.replace('/(auth)/login')} size="lg" fullWidth />
      <Pressable
        style={styles.secondary}
        accessibilityRole="link"
        accessibilityLabel="Contact support"
        onPress={() => Linking.openURL(`mailto:${BIRMINGHAM_COUNCIL.licensingEmail}`)}
      >
        <Text style={styles.link}>Contact support</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  flex: {
    flex: 1,
    backgroundColor: theme.colors.background,
    paddingHorizontal: theme.spacing.lg,
  },
  body: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  heroIcon: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: theme.colors.warningLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    ...theme.typography.h1,
    fontFamily: FONT_BOLD,
    color: theme.colors.text,
    marginTop: theme.spacing.lg,
    textAlign: 'center',
  },
  lead: {
    fontSize: 15,
    lineHeight: 22,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.sm,
    textAlign: 'center',
    maxWidth: 320,
  },
  steps: { alignSelf: 'stretch', maxWidth: 280, marginTop: theme.spacing.xl, gap: 4 },
  stepRow: { flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 44 },
  dot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: theme.colors.border,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dotDone: { backgroundColor: theme.colors.secondaryDark, borderColor: theme.colors.secondaryDark },
  stepTitle: { fontSize: 16, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  stepTitleMuted: { color: theme.colors.textSecondary, fontFamily: FONT_MEDIUM, fontWeight: '500' },
  secondary: { alignItems: 'center', minHeight: 44, justifyContent: 'center', marginTop: 4 },
  link: { color: theme.colors.secondaryDark, fontFamily: FONT_SEMIBOLD, fontWeight: '600', fontSize: 15 },
});
