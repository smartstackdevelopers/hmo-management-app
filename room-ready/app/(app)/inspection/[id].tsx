import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useInspections, useUpdateInspection } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function InspectionDetailScreen() {
  const guard = useRoleGuard(ROUTE_ROLES.inspectionDetail);
  if (guard) return guard;

  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useAuth();
  const { data, isLoading, error, refetch } = useInspections();
  const update = useUpdateInspection();
  const [finding, setFinding] = useState('');
  const [notes, setNotes] = useState('');

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Inspection not found" onRetry={refetch} />;

  const inspection = data?.inspections?.find((i) => i.id === id);
  if (!inspection) return <ErrorState message="Inspection not found" onRetry={refetch} />;

  const canEdit = ['property_manager', 'admin', 'landlord'].includes(user?.role ?? '');
  const isComplete = inspection.status === 'completed';
  const inspectionId = inspection.id;
  const existingFindings = inspection.findings ?? [];
  const existingNotes = inspection.notes;

  async function handleComplete() {
    const findings = finding.trim() ? [...existingFindings, finding.trim()] : existingFindings;
    try {
      await update.mutateAsync({
        id: inspectionId,
        status: 'completed',
        findings,
        notes: notes || existingNotes,
      });
      router.back();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Update failed');
    }
  }

  async function handleCancel() {
    try {
      await update.mutateAsync({ id: inspectionId, status: 'cancelled' });
      router.back();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Update failed');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Text style={styles.title}>{inspection.property?.name}</Text>
        <Badge label={inspection.status} variant={isComplete ? 'success' : 'info'} />
      </View>
      <Text style={styles.address}>{inspection.property?.addressLine1}, {inspection.property?.postcode}</Text>

      <Card style={styles.section}>
        <Text style={styles.sectionTitle}>Scheduled</Text>
        <Text style={styles.body}>{formatUKDate(inspection.scheduledAt)}</Text>
        {inspection.inspector && (
          <Text style={styles.body}>Inspector: {inspection.inspector.firstName} {inspection.inspector.lastName}</Text>
        )}
        {inspection.notes && <Text style={styles.body}>{inspection.notes}</Text>}
      </Card>

      {inspection.findings?.length > 0 && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Findings</Text>
          {inspection.findings.map((f, i) => (
            <Text key={i} style={styles.finding}>• {f}</Text>
          ))}
        </Card>
      )}

      {canEdit && !isComplete && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Complete Inspection</Text>
          <Input label="Add finding" value={finding} onChangeText={setFinding} placeholder="e.g. Smoke alarm tested — OK" />
          <Input label="Notes" value={notes} onChangeText={setNotes} multiline numberOfLines={3} placeholder={inspection.notes ?? 'Final notes...'} />
          <Button title="Mark Complete" onPress={handleComplete} loading={update.isPending} fullWidth style={styles.btn} />
          <Button title="Cancel Inspection" variant="outline" onPress={handleCancel} fullWidth />
        </Card>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  title: { ...theme.typography.h2, color: theme.colors.text, flex: 1 },
  address: { color: theme.colors.textSecondary, marginTop: 8, marginBottom: theme.spacing.lg },
  section: { marginBottom: theme.spacing.md },
  sectionTitle: { fontWeight: '700', color: theme.colors.text, marginBottom: 8 },
  body: { color: theme.colors.textSecondary, lineHeight: 22, fontSize: 15 },
  finding: { color: theme.colors.textSecondary, lineHeight: 22, marginBottom: 4 },
  btn: { marginBottom: theme.spacing.sm },
});
