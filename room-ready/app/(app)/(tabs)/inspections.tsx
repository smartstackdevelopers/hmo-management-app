import { router } from 'expo-router';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { ListScreen } from '@/components/ui/ListScreen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { TAB_ROLES } from '@/constants/permissions';
import { useFabBottom } from '@/hooks/useLayout';
import { useAuth } from '@/contexts/AuthContext';
import { InspectionItem } from '@/lib/api';
import { useInspections } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function InspectionsScreen() {
  const fabBottom = useFabBottom();
  const guard = useRoleGuard(TAB_ROLES.inspections);
  if (guard) return guard;

  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useInspections();
  const canSchedule = ['property_manager', 'admin'].includes(user?.role ?? '');

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load inspections" onRetry={refetch} />;

  const inspections = data?.inspections ?? [];

  return (
    <View style={styles.container}>
      <ListScreen
        data={inspections}
        keyExtractor={(item) => item.id}
        refreshing={isRefetching}
        onRefresh={refetch}
        fabClearance={canSchedule ? theme.layout.fabSize + theme.spacing.md : 0}
        contentContainerStyle={inspections.length === 0 ? styles.emptyList : undefined}
        ListEmptyComponent={
          <EmptyState title="No inspections scheduled" message="Property inspections will appear here." />
        }
        renderItem={({ item }) => <InspectionCard item={item} />}
      />
      {canSchedule && (
        <Pressable style={[styles.fab, { bottom: fabBottom }]} onPress={() => router.push('/(app)/inspection/new')}>
          <Ionicons name="add" size={28} color={theme.colors.textInverse} />
        </Pressable>
      )}
    </View>
  );
}

function InspectionCard({ item }: { item: InspectionItem }) {
  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/inspection/${item.id}`)}>
      <View style={styles.row}>
        <Text style={styles.title} numberOfLines={1}>{item.property?.name}</Text>
        <Badge label={item.status} variant={item.status === 'completed' ? 'success' : 'info'} />
      </View>
      <Text style={styles.address} numberOfLines={1}>
        {item.property?.addressLine1}, {item.property?.postcode}
      </Text>
      <Text style={styles.date}>Scheduled: {formatUKDate(item.scheduledAt)}</Text>
      {item.inspector && (
        <Text style={styles.inspector} numberOfLines={1}>
          Inspector: {item.inspector.firstName} {item.inspector.lastName}
        </Text>
      )}
      {item.notes ? (
        <Text style={styles.notes} numberOfLines={2}>{item.notes}</Text>
      ) : null}
    </Card>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  emptyList: { flexGrow: 1 },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
  title: { fontWeight: '600', fontSize: 16, color: theme.colors.text, flex: 1, minWidth: 0 },
  address: { color: theme.colors.textSecondary, marginTop: 4 },
  date: { color: theme.colors.primary, marginTop: 8, fontWeight: '500' },
  inspector: { color: theme.colors.textMuted, fontSize: 13, marginTop: 4 },
  notes: { color: theme.colors.textSecondary, marginTop: 6, fontSize: 14 },
  fab: {
    position: 'absolute',
    right: theme.spacing.md,
    width: theme.layout.fabSize,
    height: theme.layout.fabSize,
    borderRadius: theme.layout.fabSize / 2,
    backgroundColor: theme.colors.secondary,
    alignItems: 'center',
    justifyContent: 'center',
    ...theme.shadows.glow,
  },
});
