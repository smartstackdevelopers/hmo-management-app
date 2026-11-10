import { ReactNode } from 'react';
import { Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function staffLabel(value: string | null | undefined): string {
  if (!value) return '';
  return value.replace(/_/g, ' ');
}

export function StaffPage({
  title,
  subtitle,
  children,
  refreshing,
  onRefresh,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  refreshing?: boolean;
  onRefresh?: () => void;
}) {
  return (
    <Screen
      refreshControl={
        onRefresh ? (
          <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={theme.colors.secondary} />
        ) : undefined
      }
    >
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
      {children}
    </Screen>
  );
}

export function RecordCard({
  title,
  detail,
  status,
  onPress,
}: {
  title: string;
  detail?: string | null;
  status?: string | null;
  onPress?: () => void;
}) {
  return (
    <Card onPress={onPress} style={styles.card}>
      <View style={styles.row}>
        <Text style={styles.cardTitle}>{title}</Text>
        {status ? <Text style={styles.status}>{staffLabel(status)}</Text> : null}
      </View>
      {detail ? <Text style={styles.detail}>{detail}</Text> : null}
    </Card>
  );
}

export function DraftBadge({ count }: { count: number }) {
  if (count < 1) return null;
  return (
    <Text style={styles.draft}>
      {count} draft{count === 1 ? '' : 's'} on this device
    </Text>
  );
}

export function ChoiceRow({
  options,
  value,
  onChange,
}: {
  options: { id: string; label: string }[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <View style={styles.choices}>
      {options.map((option) => {
        const selected = option.id === value;
        return (
          <Pressable
            key={option.id}
            accessibilityRole="button"
            onPress={() => onChange(option.id)}
            style={[styles.choice, selected && styles.choiceOn]}
          >
            <Text style={[styles.choiceText, selected && styles.choiceTextOn]}>{option.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Feedback({ text, tone }: { text: string; tone?: 'ok' | 'warn' }) {
  return <Text style={tone === 'ok' ? styles.ok : styles.warn}>{text}</Text>;
}

const styles = StyleSheet.create({
  title: {
    fontFamily: FONT_BOLD,
    fontSize: 28,
    color: theme.colors.text,
    letterSpacing: -0.4,
    marginBottom: theme.spacing.sm,
  },
  subtitle: {
    fontFamily: FONT_MEDIUM,
    fontSize: 15,
    lineHeight: 22,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
  },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8 },
  cardTitle: { flex: 1, fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text },
  status: { fontFamily: FONT_SEMIBOLD, fontSize: 12, color: theme.colors.secondaryDark, textTransform: 'capitalize' },
  detail: { marginTop: 6, fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary },
  draft: {
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.warning,
    backgroundColor: theme.colors.warningLight,
    overflow: 'hidden',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: theme.radius.full,
    marginBottom: theme.spacing.md,
  },
  choices: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.md },
  choice: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: theme.radius.full,
    backgroundColor: theme.colors.surfaceMuted,
  },
  choiceOn: { backgroundColor: theme.colors.secondary },
  choiceText: { fontFamily: FONT_MEDIUM, color: theme.colors.text, fontSize: 13 },
  choiceTextOn: { color: theme.colors.textInverse },
  ok: { fontFamily: FONT_SEMIBOLD, color: theme.colors.success, marginBottom: theme.spacing.sm },
  warn: { fontFamily: FONT_MEDIUM, color: theme.colors.error, marginBottom: theme.spacing.sm },
});
