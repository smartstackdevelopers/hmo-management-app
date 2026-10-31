import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { SIMPLE } from '@/constants/simpleCopy';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { getComplianceLabel } from '@/lib/compliance';

interface ComplianceOverviewCardProps {
  score: number;
  readinessTier?: string | null;
  criticalGaps?: number;
  onPress: () => void;
}

export function ComplianceOverviewCard({ score, readinessTier, criticalGaps = 0, onPress }: ComplianceOverviewCardProps) {
  const status = score >= 85 ? 'compliant' : score >= 60 ? 'warning' : 'non_compliant';
  const color = score >= 85 ? theme.colors.success : score >= 60 ? theme.colors.warning : theme.colors.error;
  const detail =
    criticalGaps > 0
      ? `${criticalGaps} certificate${criticalGaps === 1 ? '' : 's'} missing or expired`
      : readinessTier ?? getComplianceLabel(status);

  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.wrap, pressed && styles.pressed]}>
      <View style={styles.card}>
        <View style={[styles.iconWrap, { backgroundColor: `${color}18` }]}>
          <Ionicons name="shield-checkmark" size={22} color={color} />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>{SIMPLE.compliance.title}</Text>
          <Text style={styles.sub}>{detail}</Text>
          <View style={styles.track}>
            <View style={[styles.fill, { width: `${Math.min(score, 100)}%`, backgroundColor: color }]} />
          </View>
        </View>
        <View style={styles.scoreCol}>
          <Text style={[styles.score, { color }]}>{score}%</Text>
          <Ionicons name="chevron-forward" size={16} color={theme.colors.textMuted} />
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.lg },
  pressed: { opacity: 0.94 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: theme.spacing.md,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: theme.radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  copy: { flex: 1, gap: 4 },
  title: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  sub: { fontSize: 13, color: theme.colors.textSecondary, lineHeight: 18, fontFamily: FONT_MEDIUM },
  track: {
    height: 5,
    borderRadius: 3,
    backgroundColor: theme.colors.borderLight,
    marginTop: 6,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: 3 },
  scoreCol: { alignItems: 'flex-end', gap: 4 },
  score: { fontSize: 20, fontFamily: FONT_BOLD, fontWeight: '700' },
});
