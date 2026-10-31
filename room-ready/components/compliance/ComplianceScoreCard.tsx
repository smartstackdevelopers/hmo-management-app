import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { BIRMINGHAM_COUNCIL } from '@/constants/birmingham';
import { theme } from '@/constants/theme';
import {
  ComplianceStatus,
  getComplianceLabel,
  getComplianceVariant,
  PropertyComplianceReport,
} from '@/lib/compliance';

interface ComplianceScoreCardProps {
  report: PropertyComplianceReport;
  propertyName?: string;
  compact?: boolean;
}

const STATUS_COLORS: Record<ComplianceStatus, string> = {
  compliant: theme.colors.success,
  warning: theme.colors.warning,
  non_compliant: theme.colors.error,
  unknown: theme.colors.textMuted,
};

export function ComplianceScoreCard({ report, propertyName, compact }: ComplianceScoreCardProps) {
  const color = STATUS_COLORS[report.status];

  return (
    <Card style={[styles.card, compact ? styles.compact : undefined]}>
      <View style={styles.header}>
        <View style={styles.councilMark}>
          <Ionicons name="shield-checkmark" size={20} color={theme.colors.secondary} />
        </View>
        <View style={styles.headerText}>
          <Text style={styles.councilLabel}>{BIRMINGHAM_COUNCIL.shortName} HMO Standards</Text>
          {propertyName && <Text style={styles.propertyName}>{propertyName}</Text>}
        </View>
        <Badge label={getComplianceLabel(report.status)} variant={getComplianceVariant(report.status)} />
      </View>

      <View style={styles.scoreRow}>
        <View style={[styles.scoreRing, { borderColor: color }]}>
          <Text style={[styles.scoreValue, { color }]}>{report.score}</Text>
          <Text style={styles.scorePercent}>%</Text>
        </View>
        <View style={styles.scoreMeta}>
          <Text style={styles.scoreTitle}>Compliance Score</Text>
          <Text style={styles.scoreDesc}>
            Assessed against {BIRMINGHAM_COUNCIL.name} HMO licensing and management standards
          </Text>
          <View style={styles.legend}>
            <LegendDot color={theme.colors.success} label={`${report.checks.filter((c) => c.status === 'compliant').length} met`} />
            <LegendDot color={theme.colors.warning} label={`${report.checks.filter((c) => c.status === 'warning').length} attention`} />
            <LegendDot color={theme.colors.error} label={`${report.checks.filter((c) => c.status === 'non_compliant').length} failed`} />
          </View>
        </View>
      </View>
    </Card>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.md },
  compact: { padding: theme.spacing.sm },
  header: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.sm, marginBottom: theme.spacing.md },
  councilMark: {
    width: 40,
    height: 40,
    borderRadius: theme.radius.md,
    backgroundColor: theme.colors.infoLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerText: { flex: 1 },
  councilLabel: { fontSize: 11, fontWeight: '700', color: theme.colors.secondary, letterSpacing: 0.5, textTransform: 'uppercase' },
  propertyName: { fontSize: 15, fontWeight: '600', color: theme.colors.text, marginTop: 2 },
  scoreRow: { flexDirection: 'row', alignItems: 'center', gap: theme.spacing.lg },
  scoreRing: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 4,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  scoreValue: { fontSize: 28, fontWeight: '800' },
  scorePercent: { fontSize: 14, fontWeight: '600', color: theme.colors.textMuted, marginTop: 6 },
  scoreMeta: { flex: 1 },
  scoreTitle: { fontSize: 16, fontWeight: '700', color: theme.colors.text },
  scoreDesc: { fontSize: 12, color: theme.colors.textSecondary, marginTop: 4, lineHeight: 17 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 11, color: theme.colors.textMuted, fontWeight: '500' },
});
