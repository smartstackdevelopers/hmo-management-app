import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { FactGrid, titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Chip, type Tone } from '@/components/ui/Chip';
import { Input } from '@/components/ui/Input';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { ROUTE_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useInspections, useUpdateInspection } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

function toneFor(status: string): Tone {
  const value = status.toLowerCase();
  if (value === 'completed' || value === 'passed') return 'green';
  if (value.includes('fail') || value === 'cancelled') return 'amber';
  return 'indigo';
}

function chipLabel(status: string): string {
  const value = status.toLowerCase();
  if (value === 'cancelled') return 'Cancelled';
  if (value === 'completed' || value === 'passed') return 'Passed';
  if (value.includes('fail')) return 'Actions';
  if (value === 'scheduled' || value === 'booked' || value === 'upcoming' || value === 'pending') return 'Booked';
  return titleCase(status);
}

export default function InspectionDetailScreen() {
  useHideTabHeader();
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

  const inspection = data?.inspections?.find((item) => item.id === id);
  if (!inspection) return <ErrorState message="Inspection not found" onRetry={refetch} />;

  const canEdit = ['property_manager', 'admin', 'landlord'].includes(user?.role ?? '');
  const isComplete = inspection.status === 'completed' || inspection.status === 'passed';
  const title = inspection.property?.addressLine1 || inspection.property?.name || 'Inspection';
  const inspector = inspection.inspector ? `${inspection.inspector.firstName} ${inspection.inspector.lastName}`.trim() : '';

  async function handleComplete() {
    const findings = finding.trim() ? [...(inspection?.findings ?? []), finding.trim()] : inspection?.findings ?? [];
    try {
      await update.mutateAsync({
        id: inspection!.id,
        status: 'completed',
        findings,
        notes: notes || inspection?.notes,
      });
      router.back();
    } catch (err) {
      Alert.alert('Error', err instanceof Error ? err.message : 'Update failed');
    }
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <View style={styles.titleRow}>
        <Text style={styles.title}>{title}</Text>
        <Chip label={chipLabel(inspection.status)} tone={toneFor(inspection.status)} />
      </View>

      <FactGrid
        items={[
          { label: 'Scheduled', value: formatUKDate(inspection.scheduledAt) },
          { label: 'Postcode', value: inspection.property?.postcode || '—' },
          { label: 'Inspector', value: inspector || '—' },
          { label: 'Notes', value: inspection.notes || '—' },
        ]}
      />

      {inspection.findings?.length ? (
        <View style={styles.findings}>
          <Text style={styles.section}>Findings</Text>
          {inspection.findings.map((item, index) => (
            <Text key={`${index}-${item}`} style={styles.finding}>{item}</Text>
          ))}
        </View>
      ) : null}

      {canEdit && !isComplete ? (
        <View>
          <Input label="Add finding" value={finding} onChangeText={setFinding} placeholder="What you checked" />
          <Input label="Notes" value={notes} onChangeText={setNotes} multiline numberOfLines={3} placeholder="Optional" />
          <Button title="Mark complete" onPress={handleComplete} loading={update.isPending} fullWidth size="lg" />
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 48 },
  back: { flexDirection: 'row', alignItems: 'center', marginBottom: theme.spacing.md, alignSelf: 'flex-start' },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  titleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: theme.spacing.md },
  title: { flex: 1, fontSize: 28, fontFamily: FONT_BOLD, fontWeight: '700', color: theme.colors.text, letterSpacing: -0.4 },
  findings: { marginBottom: theme.spacing.lg },
  section: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, marginBottom: 8 },
  finding: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20, marginBottom: 4 },
});
