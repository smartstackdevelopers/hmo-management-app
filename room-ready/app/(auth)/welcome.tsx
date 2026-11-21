import { Link } from 'expo-router';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { RoomReadyLogo } from '@/components/RoomReadyLogo';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { FocusStatusBar } from '@/components/ui/FocusStatusBar';
import { IconTile } from '@/components/ui/IconTile';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export default function WelcomeScreen() {
  const insets = useSafeAreaInsets();

  return (
    <ScrollView
      style={styles.root}
      contentContainerStyle={[
        styles.content,
        { paddingTop: insets.top + 28, paddingBottom: insets.bottom + 20 },
      ]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      <FocusStatusBar style="dark" />
      <View style={styles.body}>
        <RoomReadyLogo size="md" centered layout="stack" shadow={false} />
        <Text style={styles.headline} accessibilityRole="header">
          Housing and support,{'\n'}done properly
        </Text>
        <Text style={styles.sub}>
          Homes, repairs, support plans and community services in one calm place.
        </Text>

        <View accessible accessibilityLabel="Example: a booked repair shown as all good" style={styles.previewWrap}>
          <Card style={styles.preview}>
            <View style={styles.previewRow}>
              <IconTile icon="home" tone="blue" size={44} />
              <View style={styles.previewCopy}>
                <Text style={styles.previewTitle} numberOfLines={1}>Room 4 · 12 High Street</Text>
                <Text style={styles.previewMeta} numberOfLines={1}>Repair booked · Tue 10:00</Text>
              </View>
            </View>
            <Chip label="All good" tone="green" style={styles.previewChip} />
          </Card>
        </View>

        <View style={styles.trustRow}>
          <Chip label="Council-ready" tone="gray" />
          <Chip label="Secure" tone="gray" />
          <Chip label="6 roles" tone="gray" />
        </View>
      </View>

      <View style={styles.footer}>
        <Link href="/(auth)/register" asChild>
          <Button title="Create account" size="lg" fullWidth />
        </Link>
        <Link href="/(auth)/login" asChild>
          <Button title="Sign in" variant="outlineLight" size="lg" fullWidth />
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
    paddingVertical: theme.spacing.lg,
  },
  headline: {
    ...theme.typography.hero,
    fontFamily: FONT_BOLD,
    color: theme.colors.text,
    textAlign: 'center',
    marginTop: theme.spacing.lg,
  },
  sub: {
    fontSize: 16,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 24,
    maxWidth: 320,
    marginTop: theme.spacing.sm,
  },
  previewWrap: { width: '100%', maxWidth: 340, marginTop: theme.spacing.lg },
  preview: {
    width: '100%',
    maxWidth: 340,
    padding: theme.spacing.md,
  },
  previewRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  previewCopy: { flex: 1, minWidth: 0 },
  previewTitle: {
    fontSize: 15,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
  },
  previewMeta: {
    fontSize: 13,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  previewChip: { marginTop: 12 },
  trustRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginTop: theme.spacing.md,
  },
  footer: { gap: theme.spacing.sm, width: '100%', paddingTop: theme.spacing.md },
});
