import { Ionicons } from '@expo/vector-icons';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { theme } from '@/constants/theme';

interface CouncilStandardsBannerProps {
  variant?: 'full' | 'compact';
}

export function CouncilStandardsBanner({ variant = 'full' }: CouncilStandardsBannerProps) {
  return (
    <View style={[styles.banner, variant === 'compact' && styles.compact]}>
      <View style={styles.iconWrap}>
        <Ionicons name="business" size={18} color={theme.colors.textInverse} />
      </View>
      <View style={styles.copy}>
        <Text style={styles.title}>{BIRMINGHAM_COUNCIL.name}</Text>
        <Text style={styles.subtitle}>
          {variant === 'full'
            ? 'HMO licensing & housing standards compliant platform'
            : 'BCC HMO Standards'}
        </Text>
        {variant === 'full' && (
          <Text style={styles.threshold}>{BIRMINGHAM_COUNCIL.licensingThreshold.description}</Text>
        )}
      </View>
      {variant === 'full' && (
        <Pressable
          onPress={() => Linking.openURL(BIRMINGHAM_COUNCIL.housingStandardsUrl)}
          style={styles.link}
        >
          <Text style={styles.linkText}>Guidance</Text>
          <Ionicons name="open-outline" size={14} color={theme.colors.accentLight} />
        </Pressable>
      )}
    </View>
  );
}

export function CouncilContactCard() {
  return (
    <View style={styles.contactCard}>
      <Text style={styles.contactTitle}>Birmingham City Council — Private Sector Housing</Text>
      <Text style={styles.contactRow}>
        <Ionicons name="call-outline" size={14} color={theme.colors.secondary} /> {BIRMINGHAM_COUNCIL.licensingPhone}
      </Text>
      <Text style={styles.contactRow}>
        <Ionicons name="mail-outline" size={14} color={theme.colors.secondary} /> {BIRMINGHAM_COUNCIL.licensingEmail}
      </Text>
      <Pressable onPress={() => Linking.openURL(BIRMINGHAM_COUNCIL.housingStandardsUrl)}>
        <Text style={styles.contactLink}>{BIRMINGHAM_COUNCIL.housingStandardsUrl}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.primary,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md,
    gap: theme.spacing.md,
  },
  compact: { paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.md },
  iconWrap: {
    width: 36,
    height: 36,
    borderRadius: theme.radius.sm,
    backgroundColor: 'rgba(255,255,255,0.15)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: { flex: 1 },
  title: { color: theme.colors.textInverse, fontWeight: '700', fontSize: 14 },
  subtitle: { color: 'rgba(255,255,255,0.75)', fontSize: 12, marginTop: 2 },
  threshold: { color: 'rgba(255,255,255,0.6)', fontSize: 11, marginTop: 6, lineHeight: 15 },
  link: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  linkText: { color: theme.colors.accentLight, fontSize: 12, fontWeight: '600' },
  contactCard: {
    backgroundColor: theme.colors.surfaceSecondary,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
    marginTop: theme.spacing.md,
  },
  contactTitle: { fontWeight: '700', fontSize: 14, color: theme.colors.text, marginBottom: 8 },
  contactRow: { fontSize: 13, color: theme.colors.textSecondary, marginBottom: 6 },
  contactLink: { fontSize: 12, color: theme.colors.secondary, marginTop: 4, textDecorationLine: 'underline' },
});
