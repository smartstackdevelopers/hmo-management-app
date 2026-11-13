import { useEffect, useState } from 'react';
import { Text, View, StyleSheet, ScrollView, ActivityIndicator } from 'react-native';
import {
  listSafeguardingAlerts,
  type SafeguardingAlertRecord,
} from '@/lib/hmore/services/staff/safeguardingAlerts';

export default function StaffSafeguardingAlertsScreen() {
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState<SafeguardingAlertRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSafeguardingAlerts()
      .then(setAlerts)
      .catch(() => setError('Unable to load safeguarding alerts.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.title}>Safeguarding alerts</Text>
      <Text style={styles.subtitle}>Push notifications never include confidential case details.</Text>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {alerts.length === 0 ? (
        <Text style={styles.muted}>No alerts assigned or visible.</Text>
      ) : (
        alerts.map((a) => (
          <View key={a.id} style={styles.card}>
            <Text style={styles.ref}>{a.reference_number}</Text>
            <Text style={styles.meta}>
              {a.priority} · {a.status}
              {a.requires_human_review ? ' · Review required' : ''}
            </Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 16 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 22, fontWeight: '600', color: '#0f172a' },
  subtitle: { marginTop: 6, fontSize: 13, color: '#64748b' },
  error: { marginTop: 12, color: '#b91c1c' },
  muted: { marginTop: 16, color: '#64748b' },
  card: {
    marginTop: 12,
    padding: 12,
    borderRadius: 8,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  ref: { fontWeight: '600', color: '#0f172a' },
  meta: { marginTop: 4, fontSize: 13, color: '#475569' },
});
