import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { theme } from '@/constants/theme';
import { ComplianceCheck, ComplianceStatus } from '@/lib/compliance';

const STATUS_ICON: Record<ComplianceStatus, { name: keyof typeof Ionicons.glyphMap; color: string }> = {
  compliant: { name: 'checkmark-circle', color: theme.colors.success },
  warning: { name: 'alert-circle', color: theme.colors.warning },
  non_compliant: { name: 'close-circle', color: theme.colors.error },
  unknown: { name: 'help-circle', color: theme.colors.textMuted },
};

interface ComplianceChecklistProps {
  checks: ComplianceCheck[];
  title?: string;
}

export function ComplianceChecklist({ checks, title = 'Standards Checklist' }: ComplianceChecklistProps) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
      {checks.map((check) => {
        const icon = STATUS_ICON[check.status];
        return (
          <Card key={check.id} style={styles.item} variant="outlined">
            <View style={styles.row}>
              <Ionicons name={icon.name} size={22} color={icon.color} />
              <View style={styles.copy}>
                <Text style={styles.checkTitle}>{check.title}</Text>
                <Text style={styles.checkDesc}>{check.description}</Text>
                {check.detail && <Text style={styles.checkDetail}>{check.detail}</Text>}
                <Text style={styles.regulation}>{check.regulation}</Text>
              </View>
            </View>
          </Card>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginTop: theme.spacing.md },
  title: { ...theme.typography.h3, color: theme.colors.text, marginBottom: theme.spacing.sm },
  item: { marginBottom: theme.spacing.sm, paddingVertical: theme.spacing.sm },
  row: { flexDirection: 'row', gap: theme.spacing.md, alignItems: 'flex-start' },
  copy: { flex: 1 },
  checkTitle: { fontWeight: '700', fontSize: 15, color: theme.colors.text },
  checkDesc: { fontSize: 13, color: theme.colors.textSecondary, marginTop: 3, lineHeight: 18 },
  checkDetail: { fontSize: 13, color: theme.colors.secondary, fontWeight: '600', marginTop: 6 },
  regulation: { fontSize: 11, color: theme.colors.textMuted, marginTop: 6, fontStyle: 'italic' },
});
