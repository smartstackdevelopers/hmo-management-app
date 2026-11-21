import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { InitialsTile } from '@/components/dashboard/mobileChrome';
import { repairStatusText, repairStatusTone } from '@/components/maintenance/repairTone';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { MaintenanceItem } from '@/lib/api';
import { statusLabel } from '@/lib/maintenance';

export function RepairCard({ item }: { item: MaintenanceItem }) {
  const place = [item.room?.name, item.property?.name].filter(Boolean).join(' · ') || item.category;
  return (
    <Card style={styles.card} onPress={() => router.push(`/(app)/maintenance/${item.id}`)}>
      <View style={styles.row}>
        <InitialsTile name={item.title} size={42} />
        <View style={styles.copy}>
          <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
          <Text style={styles.place} numberOfLines={1}>{place}</Text>
        </View>
        <Chip label={statusLabel(item.status) || repairStatusText(item.status)} tone={repairStatusTone(item.status)} />
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontSize: 15, fontFamily: FONT_SEMIBOLD, fontWeight: '600', color: theme.colors.text },
  place: { fontSize: 13, fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 2 },
});
