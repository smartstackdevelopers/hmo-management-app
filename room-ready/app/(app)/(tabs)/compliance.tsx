import { router } from 'expo-router';
import { useState } from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

import { ComplianceScoreCard } from '@/components/compliance/ComplianceScoreCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ListScreen } from '@/components/ui/ListScreen';
import { Section } from '@/components/ui/Section';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { BIRMINGHAM_REQUIRED_DOCUMENTS } from '@/constants/birmingham';
import { SIMPLE } from '@/constants/simpleCopy';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useProperties } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';
import {
  assessPropertyCompliance,
  getComplianceCopilotActions,
  getComplianceLabel,
  getComplianceVariant,
} from '@/lib/compliance';

export default function ComplianceScreen() {
  const guard = useRoleGuard(TAB_ROLES.compliance);
  if (guard) return guard;

  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useProperties();
  const canAdd = ['landlord', 'admin'].includes(user?.role ?? '');
  const [showChecklist, setShowChecklist] = useState(false);

  if (isLoading) return <LoadingScreen message="Loading..." />;
  if (error) return <ErrorState message="Could not load property checks" onRetry={refetch} />;

  const properties = data?.properties ?? [];
  const reports = properties.map((p) => ({ property: p, report: assessPropertyCompliance(p) }));
  const fixActions = reports
    .flatMap((item) =>
      getComplianceCopilotActions(item.property, item.report).map((action) => ({
        ...action,
        propertyName: item.property.name,
        propertyId: item.property.id,
      }))
    )
    .slice(0, 5);
  const portfolioScore =
    reports.length > 0
      ? Math.round(reports.reduce((s, r) => s + r.report.score, 0) / reports.length)
      : 0;

  if (properties.length === 0) {
    return (
      <View style={styles.container}>
        <EmptyState
          title="Add a property first"
          message="Once you add an HMO, we'll show you what certificates you need."
          icon="shield-checkmark-outline"
          actionLabel={canAdd ? 'Add property' : undefined}
          onAction={canAdd ? () => router.push('/(app)/property/new') : undefined}
        />
      </View>
    );
  }

  const scoreColor =
    portfolioScore >= 85 ? theme.colors.success : portfolioScore >= 60 ? theme.colors.warning : theme.colors.error;

  return (
    <ListScreen
      data={reports}
      keyExtractor={(item) => item.property.id}
      refreshing={isRefetching}
      onRefresh={refetch}
      ListHeaderComponent={
        <View>
          <Text style={styles.pageTitle}>{SIMPLE.compliance.title}</Text>
          <Text style={styles.pageSub}>{SIMPLE.compliance.subtitle}</Text>

          <Card style={styles.scoreCard}>
            <Text style={styles.scoreLabel}>{SIMPLE.compliance.score}</Text>
            <Text style={[styles.scoreValue, { color: scoreColor }]}>{portfolioScore}%</Text>
            <Text style={styles.scoreHint}>
              {portfolioScore >= 85
                ? 'Your properties are in good shape'
                : 'Upload missing certificates in My files'}
            </Text>
            <Button
              title="Go to My files"
              variant="outline"
              size="sm"
              onPress={() => router.push('/(app)/documents')}
              style={styles.filesBtn}
            />
          </Card>

          <Section title={SIMPLE.compliance.whatToFix}>
            {fixActions.length === 0 ? (
              <Card variant="filled">
                <Text style={styles.allGood}>{SIMPLE.compliance.allGood}</Text>
              </Card>
            ) : (
              <Card padded={false}>
                {fixActions.map((action, i) => (
                  <Pressable
                    key={action.id}
                    onPress={() => router.push(`/(app)/property/${action.propertyId}`)}
                    style={({ pressed }) => [styles.fixRow, pressed && styles.pressed, i > 0 && styles.fixBorder]}
                  >
                    <Text style={styles.fixTitle}>{action.title}</Text>
                    <Text style={styles.fixMeta}>{action.propertyName}</Text>
                    <Text style={styles.fixReason}>{action.reason}</Text>
                  </Pressable>
                ))}
              </Card>
            )}
          </Section>

          {showChecklist ? (
            <Section title="Certificate checklist">
              <Card padded={false}>
                {BIRMINGHAM_REQUIRED_DOCUMENTS.map((doc, i) => (
                  <View key={doc.id} style={[styles.checkRow, i > 0 && styles.fixBorder]}>
                    <Text style={styles.checkLabel}>{doc.label}</Text>
                    {doc.statutory && <Badge label="Required" variant="info" format={false} />}
                  </View>
                ))}
              </Card>
              <Pressable onPress={() => setShowChecklist(false)}>
                <Text style={styles.link}>Hide checklist</Text>
              </Pressable>
            </Section>
          ) : (
            <Pressable onPress={() => setShowChecklist(true)} style={styles.checklistLink}>
              <Text style={styles.link}>{SIMPLE.compliance.seeChecklist}</Text>
            </Pressable>
          )}

          <Text style={styles.sectionHead}>{SIMPLE.compliance.yourProperties}</Text>
        </View>
      }
      renderItem={({ item }) => {
        const missing = item.report.checks.filter((c) => c.status !== 'compliant').length;
        return (
          <Pressable onPress={() => router.push(`/(app)/property/${item.property.id}`)} style={styles.propertyWrap}>
            <ComplianceScoreCard report={item.report} propertyName={item.property.name} compact />
            <View style={styles.propertyMeta}>
              <Text style={styles.postcode}>{item.property.postcode}</Text>
              {missing > 0 && <Badge label={`${missing} to fix`} variant="warning" format={false} />}
              <Badge label={getComplianceLabel(item.report.status)} variant={getComplianceVariant(item.report.status)} />
            </View>
          </Pressable>
        );
      }}
      ListFooterComponent={
        canAdd ? (
          <Button title="Add property" variant="outline" onPress={() => router.push('/(app)/property/new')} fullWidth style={styles.addBtn} />
        ) : null
      }
    />
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  pageTitle: { ...theme.typography.h2, color: theme.colors.text },
  pageSub: { color: theme.colors.textSecondary, fontSize: 14, marginTop: 4, marginBottom: theme.spacing.md },
  scoreCard: { alignItems: 'center', marginBottom: theme.spacing.lg, paddingVertical: theme.spacing.lg },
  scoreLabel: { ...theme.typography.label, color: theme.colors.textMuted, textTransform: 'uppercase' },
  scoreValue: { fontSize: 44, fontWeight: '800', letterSpacing: -2, marginTop: 4 },
  scoreHint: { color: theme.colors.textSecondary, fontSize: 13, textAlign: 'center', marginTop: 8 },
  filesBtn: { marginTop: theme.spacing.md },
  allGood: { color: theme.colors.textSecondary, lineHeight: 20, fontSize: 14 },
  fixRow: { padding: theme.spacing.md },
  fixBorder: { borderTopWidth: 1, borderTopColor: theme.colors.borderLight },
  pressed: { backgroundColor: theme.colors.surfaceMuted },
  fixTitle: { fontWeight: '700', fontSize: 15, color: theme.colors.text },
  fixMeta: { color: theme.colors.textMuted, fontSize: 12, marginTop: 2 },
  fixReason: { color: theme.colors.textSecondary, fontSize: 13, marginTop: 4, lineHeight: 18 },
  checkRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: theme.spacing.md,
    gap: 8,
  },
  checkLabel: { flex: 1, fontSize: 14, color: theme.colors.text },
  checklistLink: { marginBottom: theme.spacing.md },
  link: { color: theme.colors.secondary, fontWeight: '700', fontSize: 14, textAlign: 'center', marginVertical: theme.spacing.sm },
  sectionHead: { ...theme.typography.h3, color: theme.colors.text, marginBottom: theme.spacing.sm },
  propertyWrap: { marginBottom: theme.spacing.sm },
  propertyMeta: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: -4, marginBottom: theme.spacing.sm, flexWrap: 'wrap' },
  postcode: { fontSize: 13, color: theme.colors.textMuted, flex: 1 },
  addBtn: { marginTop: theme.spacing.md, marginBottom: theme.spacing.lg },
});
