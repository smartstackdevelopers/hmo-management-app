import { Link } from 'expo-router';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export default function WelcomeScreen() {
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[
        styles.content,
        { paddingTop: insets.top + 36, paddingBottom: insets.bottom + 24 },
      ]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      <FocusStatusBar style="dark" />
      <View style={styles.body}>
        <RoomReadyLogo size="md" centered />
        <Text style={styles.headline}>Property management,{'\n'}done properly</Text>
        <Text style={styles.sub}>
          Run HMOs with confidence — rooms, repairs, certificates and tenants in one calm place for {BIRMINGHAM_COUNCIL.shortName}.
        </Text>
        <View style={styles.trustRow}>
          <View style={styles.trustChip}>
            <Text style={styles.trustText}>Council-ready checks</Text>
          </View>
          <View style={styles.trustChip}>
            <Text style={styles.trustText}>Built for landlords & tenants</Text>
          </View>
        </View>
      </View>
      <View style={styles.footer}>
        <Link href="/(auth)/register" asChild>
          <Button title="Create account" variant="secondary" size="lg" fullWidth />
        </Link>
        <Link href="/(auth)/login" asChild>
          <Button title="Sign in" variant="outline" size="lg" fullWidth />
        </Link>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: theme.colors.background,
    minHeight: Platform.OS === 'web' ? ('100dvh' as unknown as number) : undefined,
  },
  content: {
    flexGrow: 1,
    paddingHorizontal: theme.spacing.lg,
    justifyContent: 'space-between',
    maxWidth: theme.layout.phoneMaxWidth,
    width: '100%',
    alignSelf: 'center',
  },
  body: {
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: theme.spacing.md,
    paddingVertical: theme.spacing.xl,
  },
  headline: {
    ...theme.typography.hero,
    fontFamily: FONT_BOLD,
    color: theme.colors.text,
    textAlign: 'center',
  },
  sub: {
    fontSize: 16,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
    maxWidth: 320,
    paddingHorizontal: theme.spacing.sm,
  },
  trustRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: theme.spacing.sm,
  },
  trustChip: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  trustText: {
    fontSize: 12,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
  },
  footer: { gap: theme.spacing.sm, width: '100%' },
});
