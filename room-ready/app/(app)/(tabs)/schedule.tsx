import { router } from 'expo-router';
import { SectionList, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useTabClearance } from '@/hooks/useLayout';
import { MaintenanceItem } from '@/lib/api';
import { useMaintenance } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

type JobSection = { title: string; data: MaintenanceItem[] };

function groupJobs(jobs: MaintenanceItem[]): JobSection[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const endOfWeek = new Date(startOfToday);
  endOfWeek.setDate(endOfWeek.getDate() + 7);

  const today: MaintenanceItem[] = [];
  const thisWeek: MaintenanceItem[] = [];
  const later: MaintenanceItem[] = [];

  for (const job of jobs) {
    const date = new Date(job.updatedAt ?? job.createdAt);
    if (date >= startOfToday && date < new Date(startOfToday.getTime() + 86400000)) {
      today.push(job);
    } else if (date >= startOfToday && date < endOfWeek) {
      thisWeek.push(job);
    } else {
      later.push(job);
    }
  }

  const sections: JobSection[] = [];
  if (today.length) sections.push({ title: 'Today', data: today });
  if (thisWeek.length) sections.push({ title: 'This week', data: thisWeek });
  if (later.length) sections.push({ title: 'Upcoming', data: later });
  return sections;
}

export default function ScheduleScreen() {
  const bottomPad = useTabClearance();
  const guard = useRoleGuard(TAB_ROLES.schedule);
  if (guard) return guard;

  const { data, isLoading, error, refetch, isRefetching } = useMaintenance();

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load schedule" onRetry={refetch} />;

  const jobs = (data?.requests ?? []).filter((r) =>
    ['assigned', 'in_progress', 'awaiting_parts'].includes(r.status)
  );
  const sections = groupJobs(jobs);

  if (jobs.length === 0) {
    return (
      <EmptyState
        title="No active jobs"
        message="When you're assigned repair work, jobs will appear here grouped by schedule."
        icon="calendar-outline"
      />
    );
  }

  return (
    <SectionList
      style={styles.container}
      sections={sections}
      keyExtractor={(item) => item.id}
      contentContainerStyle={[styles.list, { paddingBottom: bottomPad }]}
      refreshing={isRefetching}
      onRefresh={refetch}
      renderSectionHeader={({ section: { title } }) => (
        <Text style={styles.sectionTitle}>{title}</Text>
      )}
      renderItem={({ item }) => <JobCard item={item} />}
      stickySectionHeadersEnabled={false}
    />
  );
}

function JobCard({ item }: { item: MaintenanceItem }) {
  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/maintenance/${item.id}`)}>
      <View style={styles.row}>
        <Text style={styles.title} numberOfLines={2}>{item.title}</Text>
        <Badge label={item.status.replace(/_/g, ' ')} variant="info" />
      </View>
      <Text style={styles.property} numberOfLines={1}>{item.property?.name}</Text>
      <Text style={styles.address} numberOfLines={1}>{item.property?.addressLine1}, {item.property?.postcode}</Text>
      <View style={styles.meta}>
        <Badge label={item.priority} variant={item.priority === 'emergency' ? 'error' : item.priority === 'high' ? 'warning' : 'default'} />
        <Text style={styles.metaText}>{item.category}</Text>
        <Text style={styles.metaText}>Updated {formatUKDate(item.updatedAt ?? item.createdAt)}</Text>
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  list: { padding: theme.spacing.md },
  sectionTitle: {
    ...theme.typography.h3,
    color: theme.colors.text,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.sm,
  },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 },
  title: { fontWeight: '600', fontSize: 16, color: theme.colors.text, flex: 1, minWidth: 0 },
  property: { color: theme.colors.text, marginTop: 4, fontWeight: '600' },
  address: { color: theme.colors.textSecondary, fontSize: 14 },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: 8, flexWrap: 'wrap' },
  metaText: { color: theme.colors.textMuted, fontSize: 13 },
});
