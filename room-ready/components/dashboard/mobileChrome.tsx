import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from 'expo-router';
import { useLayoutEffect } from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';

import { Chip, toneColors, type Tone } from '@/components/ui/Chip';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

const TILE_TONES: Tone[] = ['blue', 'indigo', 'amber', 'green'];

export function useHideTabHeader() {
  const navigation = useNavigation();
  useLayoutEffect(() => {
    navigation.setOptions({ headerShown: false });
  }, [navigation]);
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '•';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] ?? ''}${parts[1][0] ?? ''}`.toUpperCase();
}

export function toneFor(name: string): Tone {
  let n = 0;
  for (let i = 0; i < name.length; i += 1) n = (n + name.charCodeAt(i)) % TILE_TONES.length;
  return TILE_TONES[n] ?? 'blue';
}

export function titleCase(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function shortWeekday(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('en-GB', { weekday: 'short' });
}

export function compactGBP(amount: number): string {
  if (amount >= 1000) {
    const thousands = amount / 1000;
    const text = thousands >= 10 ? thousands.toFixed(0) : thousands.toFixed(1).replace(/\.0$/, '');
    return `£${text}k`;
  }
  return new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP', maximumFractionDigits: 0 }).format(amount);
}

export function InitialsTile({ name, size = 44 }: { name: string; size?: number }) {
  const colors = toneColors[toneFor(name || '•')];
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: colors.bg,
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Text style={{ color: colors.text, fontFamily: FONT_BOLD, fontWeight: '700', fontSize: Math.round(size * 0.32) }}>
        {initials(name || '•')}
      </Text>
    </View>
  );
}

export function StatTiles({
  items,
  highContrast = false,
}: {
  items: { value: string; label: string }[];
  highContrast?: boolean;
}) {
  return (
    <View style={styles.stats}>
      {items.map((item) => (
        <View key={item.label} style={[styles.stat, highContrast && styles.contrast]}>
          <Text style={[styles.statValue, highContrast && styles.contrastText]} numberOfLines={1} adjustsFontSizeToFit>
            {item.value}
          </Text>
          <Text style={[styles.statLabel, highContrast && styles.contrastText]} numberOfLines={2}>
            {item.label}
          </Text>
        </View>
      ))}
    </View>
  );
}

export function SearchField({
  value,
  onChangeText,
  placeholder,
}: {
  value: string;
  onChangeText: (value: string) => void;
  placeholder: string;
}) {
  return (
    <View style={styles.search}>
      <Ionicons name="search-outline" size={18} color={theme.colors.textMuted} />
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={theme.colors.textMuted}
        style={styles.searchInput}
        accessibilityLabel={placeholder}
        autoCorrect={false}
        autoCapitalize="none"
      />
    </View>
  );
}

export function FilterChips({
  options,
  value,
  onChange,
}: {
  options: { id: string; label: string }[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <View style={styles.filters}>
      {options.map((option) => (
        <Chip
          key={option.id}
          label={option.label}
          selected={value === option.id}
          onPress={() => onChange(option.id)}
        />
      ))}
    </View>
  );
}

export function HouseBanner() {
  return (
    <View style={styles.banner}>
      <View style={styles.house}>
        <Ionicons name="home" size={34} color={theme.colors.textInverse} />
      </View>
    </View>
  );
}

export function FactGrid({ items }: { items: { label: string; value: string }[] }) {
  return (
    <View style={styles.grid}>
      {items.map((item) => (
        <View key={item.label} style={styles.fact}>
          <Text style={styles.factLabel}>{item.label}</Text>
          <Text style={styles.factValue} numberOfLines={2}>
            {item.value}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  stats: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  stat: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    paddingVertical: 14,
    paddingHorizontal: 8,
    alignItems: 'center',
    minHeight: 76,
    justifyContent: 'center',
  },
  contrast: { borderWidth: 2, borderColor: '#000000' },
  contrastText: { color: '#000000' },
  statValue: {
    fontSize: 20,
    fontFamily: FONT_BOLD,
    fontWeight: '700',
    color: theme.colors.text,
    letterSpacing: -0.4,
  },
  statLabel: {
    fontSize: 12,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginTop: 4,
    textAlign: 'center',
  },
  search: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.full,
    borderWidth: 1,
    borderColor: theme.colors.border,
    paddingHorizontal: 14,
    minHeight: 44,
    marginBottom: theme.spacing.sm,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.text,
    paddingVertical: 8,
  },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.md },
  banner: {
    height: 132,
    borderRadius: theme.radius.xl,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: theme.spacing.md,
  },
  house: {
    width: 72,
    height: 72,
    borderRadius: 24,
    backgroundColor: theme.colors.secondaryDark,
    alignItems: 'center',
    justifyContent: 'center',
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  fact: {
    width: '48%',
    flexGrow: 1,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
    padding: 14,
    minHeight: 72,
  },
  factLabel: { fontSize: 12, fontFamily: FONT_MEDIUM, color: theme.colors.textMuted },
  factValue: {
    fontSize: 15,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginTop: 4,
  },
});
