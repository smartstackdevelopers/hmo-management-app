import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { Alert, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getMaintenance, uploadMaintenancePhoto } from '@/lib/hmore/services/maintenance';
import { pickImage } from '@/lib/uploads';

export function HmoreRepairDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['hmore', 'maintenance', id],
    queryFn: () => getMaintenance(id!),
    enabled: !!id,
  });
  const upload = useMutation({
    mutationFn: async () => {
      const image = await pickImage();
      if (!image || !id) return null;
      return uploadMaintenancePhoto(id, {
        uri: image.uri,
        name: image.fileName || 'repair.jpg',
        mimeType: image.mimeType || 'image/jpeg',
      });
    },
    onSuccess: async (row) => {
      if (!row) return;
      await client.invalidateQueries({ queryKey: ['hmore', 'maintenance'] });
      Alert.alert('Photo added', 'The photo is attached to this repair.');
    },
  });

  if (!id) return <ErrorState message="Missing repair." />;
  if (query.isLoading) return <LoadingScreen message="Loading repair..." />;
  if (query.error || !query.data) {
    return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load this repair')} onRetry={query.refetch} />;
  }

  const row = query.data;
  return (
    <ScrollView style={styles.page} contentContainerStyle={styles.content}>
      {row.show_emergency_panel ? (
        <Card style={styles.alert}>
          <Text style={styles.alertTitle}>Safety</Text>
          <Text style={styles.body}>
            If you are in immediate danger, call 999. This repair is flagged for the organisation to review. The assistant and this screen do not dispatch emergency services.
          </Text>
        </Card>
      ) : null}
      <View style={styles.header}>
        <Text style={styles.title}>{row.title}</Text>
        <Badge label={row.status.replace(/_/g, ' ')} format={false} />
      </View>
      <Text style={styles.meta}>{row.reference_number} · {row.category_code} · {row.priority}</Text>
      <Text style={styles.body}>{row.description}</Text>
      <Text style={styles.meta}>Reported {formatUKDate(row.reported_at || row.created_at)}</Text>
      {row.scheduled_visit_at ? <Text style={styles.meta}>Visit booked {formatUKDate(row.scheduled_visit_at)}</Text> : null}
      {row.completion_summary ? <Text style={styles.body}>Completed: {row.completion_summary}</Text> : null}
      <Text style={styles.meta}>{row.file_ids?.length ?? 0} photo(s) on file</Text>
      {upload.error ? <Text style={styles.error}>{hmoreErrorMessage(upload.error)}</Text> : null}
      <Button title="Add a photo" onPress={() => upload.mutate()} loading={upload.isPending} fullWidth />
      <Text style={styles.hint}>
        Photos upload to the repair. {Platform.OS === 'web' ? 'Open documents from My files.' : 'Photo files stay with the organisation record.'}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  alert: { backgroundColor: theme.colors.warningLight, marginBottom: theme.spacing.md },
  alertTitle: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: 6 },
  header: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  title: { fontFamily: FONT_BOLD, fontSize: 22, color: theme.colors.text, flex: 1 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 8, textTransform: 'capitalize' },
  body: { fontFamily: FONT_MEDIUM, fontSize: 15, lineHeight: 22, color: theme.colors.text, marginTop: theme.spacing.md },
  error: { color: theme.colors.error, marginVertical: 8, fontFamily: FONT_MEDIUM },
  hint: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: theme.spacing.sm },
});
