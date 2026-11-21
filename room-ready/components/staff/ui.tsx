import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { ReactNode } from 'react';
import { Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { InitialsTile } from '@/components/dashboard/mobileChrome';
import { Chip, type Tone } from '@/components/ui/Chip';
import { Card } from '@/components/ui/Card';
import { ListRow } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

export function staffLabel(value: string | null | undefined): string {
  if (!value) return '';
  return value.replace(/_/g, ' ');
}

export function statusTone(status: string | null | undefined): Tone {
  const tokens = (status ?? '').toLowerCase().split(/[^a-z]+/).filter(Boolean);
  const has = (...words: string[]) => words.some((word) => tokens.includes(word));
  if (has('urgent', 'critical', 'high', 'error', 'failed', 'fail', 'overdue', 'suspended', 'rejected', 'reject')) return 'red';
  if (has('medium', 'pending', 'review', 'blocked', 'block', 'hold', 'warn', 'conflict', 'attention')) return 'amber';
  if (has('done', 'complete', 'completed', 'approved', 'active', 'verified', 'success', 'resolved', 'low')) return 'green';
  if (has('new', 'progress', 'assigned', 'scheduled', 'open', 'info')) return 'blue';
  return 'gray';
}

export function StaffPage({
  title,
  subtitle,
  leading,
  children,
  refreshing,
  onRefresh,
}: {
  title: string;
  subtitle?: string;
  leading?: ReactNode;
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
      {leading}
      <Text accessibilityRole="header" style={styles.title}>
        {title}
      </Text>
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
  icon,
  tone,
}: {
  title: string;
  detail?: string | null;
  status?: string | null;
  onPress?: () => void;
  icon?: keyof typeof Ionicons.glyphMap;
  tone?: Tone;
}) {
  const label = status ? staffLabel(status) : '';
  return (
    <Card padded={false} style={styles.card}>
      <ListRow
        title={title}
        subtitle={detail ?? undefined}
        icon={icon}
        tone={tone ?? (status ? statusTone(status) : 'blue')}
        chipLabel={label || undefined}
        chipTone={statusTone(status)}
        onPress={onPress}
        chevron={!!onPress}
      />
    </Card>
  );
}

export function DraftBadge({ count }: { count: number }) {
  if (count < 1) return null;
  return (
    <View style={styles.badge}>
      <Chip
        label={`${count} draft${count === 1 ? '' : 's'} on this device`}
        tone="amber"
        icon="cloud-offline-outline"
      />
    </View>
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
      {options.map((option) => (
        <Chip
          key={option.id}
          label={option.label}
          selected={option.id === value}
          onPress={() => onChange(option.id)}
          accessibilityLabel={option.label}
        />
      ))}
    </View>
  );
}

export function BackLink({ label = 'Back' }: { label?: string }) {
  return (
    <Pressable
      onPress={() => router.back()}
      accessibilityRole="button"
      accessibilityLabel={label}
      hitSlop={8}
      style={styles.back}
    >
      <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
      <Text style={styles.backText}>{label}</Text>
    </Pressable>
  );
}

export function StatusRow({
  name,
  title,
  subtitle,
  chip,
  tone = 'gray',
  onPress,
}: {
  name: string;
  title: string;
  subtitle?: string | null;
  chip?: string | null;
  tone?: Tone;
  onPress?: () => void;
}) {
  return (
    <Card style={styles.statusCard} onPress={onPress}>
      <View style={styles.statusRow}>
        <InitialsTile name={name || title} size={42} />
        <View style={styles.statusCopy}>
          <Text style={styles.statusTitle} numberOfLines={1}>{title}</Text>
          {subtitle ? <Text style={styles.statusMeta} numberOfLines={2}>{subtitle}</Text> : null}
        </View>
        {chip ? <Chip label={chip} tone={tone} /> : null}
      </View>
    </Card>
  );
}

export function WeekStrip({
  days,
  selectedKey,
  onSelect,
}: {
  days: { key: string; weekday: string; day: string; marked?: boolean }[];
  selectedKey: string;
  onSelect: (key: string) => void;
}) {
  return (
    <View style={styles.week}>
      {days.map((day) => {
        const selected = day.key === selectedKey;
        return (
          <Pressable
            key={day.key}
            accessibilityRole="button"
            accessibilityLabel={`${day.weekday} ${day.day}`}
            accessibilityState={{ selected }}
            onPress={() => onSelect(day.key)}
            style={[styles.weekDay, selected && styles.weekDayOn]}
          >
            <Text style={[styles.weekLabel, selected && styles.weekOnText]}>{day.weekday}</Text>
            <Text style={[styles.weekNum, selected && styles.weekOnText]}>{day.day}</Text>
            <View style={[styles.weekDot, day.marked && (selected ? styles.weekDotOn : styles.weekDotMark)]} />
          </Pressable>
        );
      })}
    </View>
  );
}

export function Timeline({
  items,
}: {
  items: { key: string; title: string; meta?: string | null }[];
}) {
  if (items.length === 0) return null;
  return (
    <View style={styles.timeline}>
      <Text style={styles.timelineHeading}>Timeline</Text>
      {items.map((item, index) => (
        <View key={item.key} style={styles.timelineRow}>
          <View style={styles.timelineRail}>
            <View style={[styles.timelineDot, index === 0 && styles.timelineDotOn]} />
            {index < items.length - 1 ? <View style={styles.timelineLine} /> : null}
          </View>
          <View style={styles.timelineCopy}>
            <Text style={styles.statusTitle}>{item.title}</Text>
            {item.meta ? <Text style={styles.statusMeta}>{item.meta}</Text> : null}
          </View>
        </View>
      ))}
    </View>
  );
}

const AGENDA_ACCENT: Record<Tone, string> = {
  blue: theme.colors.secondary,
  indigo: theme.colors.info,
  amber: theme.colors.warning,
  green: theme.colors.success,
  red: theme.colors.error,
  gray: theme.colors.border,
  navy: theme.colors.brand,
};

export function AgendaRow({
  time,
  title,
  subtitle,
  tone = 'blue',
  onPress,
}: {
  time?: string | null;
  title: string;
  subtitle?: string | null;
  tone?: Tone;
  onPress?: () => void;
}) {
  return (
    <Card style={styles.statusCard} onPress={onPress}>
      <View style={styles.agenda}>
        <Text style={styles.agendaTime}>{time || '—'}</Text>
        <View style={[styles.agendaBar, { backgroundColor: AGENDA_ACCENT[tone] }]} />
        <View style={styles.statusCopy}>
          <Text style={styles.statusTitle} numberOfLines={1}>{title}</Text>
          {subtitle ? <Text style={styles.statusMeta} numberOfLines={2}>{subtitle}</Text> : null}
        </View>
      </View>
    </Card>
  );
}

export function TileGrid({
  tiles,
}: {
  tiles: { key: string; title: string; subtitle?: string | null; onPress: () => void }[];
}) {
  return (
    <View style={styles.tileGrid}>
      {tiles.map((tile) => (
        <Card
          key={tile.key}
          style={styles.tile}
          accessibilityLabel={tile.subtitle ? `${tile.title}. ${tile.subtitle}` : tile.title}
          onPress={tile.onPress}
        >
          <InitialsTile name={tile.title} size={40} />
          <Text style={styles.tileTitle} numberOfLines={2}>{tile.title}</Text>
          {tile.subtitle ? <Text style={styles.tileSub} numberOfLines={2}>{tile.subtitle}</Text> : null}
        </Card>
      ))}
    </View>
  );
}

export function Feedback({ text, tone }: { text: string; tone?: 'ok' | 'warn' }) {
  const ok = tone === 'ok';
  return (
    <View style={[styles.feedback, ok ? styles.feedbackOk : styles.feedbackWarn]}>
      <Text style={ok ? styles.ok : styles.warn}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  title: {
    fontFamily: FONT_BOLD,
    fontSize: 28,
    color: theme.colors.text,
    letterSpacing: -0.5,
    marginBottom: 4,
  },
  subtitle: {
    fontFamily: FONT_MEDIUM,
    fontSize: 14,
    lineHeight: 20,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
  },
  card: { marginBottom: 10 },
  badge: { marginBottom: theme.spacing.md },
  choices: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.md },
  feedback: {
    borderRadius: theme.radius.md,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginBottom: theme.spacing.sm,
    borderWidth: 1,
  },
  feedbackOk: { backgroundColor: theme.colors.successLight, borderColor: '#A7F3D0' },
  feedbackWarn: { backgroundColor: theme.colors.warningLight, borderColor: '#FDE68A' },
  ok: { fontFamily: FONT_SEMIBOLD, color: '#047857', lineHeight: 20 },
  warn: { fontFamily: FONT_MEDIUM, color: '#B45309', lineHeight: 20 },
  back: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', minHeight: 36, marginBottom: 8 },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  statusCard: { marginBottom: 10 },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  statusCopy: { flex: 1, minWidth: 0 },
  statusTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  statusMeta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 2 },
  week: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: theme.spacing.md },
  weekDay: { alignItems: 'center', flex: 1, paddingVertical: 6, borderRadius: 12 },
  weekDayOn: { backgroundColor: theme.colors.secondaryDark },
  weekLabel: { fontFamily: FONT_MEDIUM, fontSize: 11, color: theme.colors.textMuted, textTransform: 'uppercase' },
  weekNum: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, marginTop: 2 },
  weekOnText: { color: theme.colors.textInverse },
  weekDot: { width: 5, height: 5, borderRadius: 3, marginTop: 4, backgroundColor: 'transparent' },
  weekDotMark: { backgroundColor: theme.colors.secondary },
  weekDotOn: { backgroundColor: theme.colors.textInverse },
  timeline: { marginBottom: theme.spacing.md },
  timelineHeading: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, marginBottom: 10 },
  timelineRow: { flexDirection: 'row', gap: 12 },
  timelineRail: { width: 16, alignItems: 'center' },
  timelineDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: theme.colors.border, marginTop: 4 },
  timelineDotOn: { backgroundColor: theme.colors.secondary },
  timelineLine: { width: 2, flex: 1, backgroundColor: theme.colors.border, marginTop: 2 },
  timelineCopy: { flex: 1, paddingBottom: 14 },
  agenda: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  agendaTime: { width: 52, fontFamily: FONT_SEMIBOLD, fontSize: 13, color: theme.colors.textSecondary },
  agendaBar: { width: 3, alignSelf: 'stretch', borderRadius: 2, minHeight: 36 },
  tileGrid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: 10 },
  tile: { width: '48%', minHeight: 118 },
  tileTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text, marginTop: 10 },
  tileSub: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 4, lineHeight: 16 },
});
