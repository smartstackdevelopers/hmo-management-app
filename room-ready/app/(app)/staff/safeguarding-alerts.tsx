import { useMemo, useState } from 'react';
import { Text } from 'react-native';

import { FilterChips, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { BackLink, StaffPage, StatusRow, staffLabel, statusTone } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useNavigation } from 'expo-router';
import { useLayoutEffect } from 'react';
import { listSafeguardingAlerts, type SafeguardingAlertRecord } from '@/lib/hmore/services/staff/safeguardingAlerts';
import { useQuery } from '@tanstack/react-query';

type Filter = 'all' | 'open' | 'acknowledged' | 'closed';

function bucket(status: string): Exclude<Filter, 'all'> {
  const value = status.toLowerCase();
  if (value === 'acknowledged') return 'acknowledged';
  if (['closed', 'resolved', 'cancelled'].includes(value)) return 'closed';
  return 'open';
}

export default function StaffSafeguardingAlertsScreen() {
  const navigation = useNavigation();
  useLayoutEffect(() => {
    navigation.setOptions({ headerShown: false });
  }, [navigation]);
  const [queryText, setQueryText] = useState('');
  const [filter, setFilter] = useState<Filter>('open');
  const query = useQuery({
    queryKey: ['hmore', 'safeguarding-alerts'],
    queryFn: listSafeguardingAlerts,
  });

  const alerts = query.data ?? [];
  const visible = useMemo(() => {
    const needle = queryText.trim().toLowerCase();
    return alerts.filter((alert) => {
      if (filter !== 'all' && bucket(alert.status) !== filter) return false;
      if (!needle) return true;
      return `${alert.reference_number} ${alert.description} ${alert.priority}`.toLowerCase().includes(needle);
    });
  }, [alerts, filter, queryText]);

  if (query.isLoading) return <LoadingScreen message="Loading alerts..." />;
  if (query.isError) return <ErrorState message="Unable to load safeguarding alerts." onRetry={query.refetch} />;

  return (
    <StaffPage
      title="Alerts"
      subtitle="Safeguarding and operational alerts. Push text never includes case details."
      leading={<BackLink />}
      onRefresh={query.refetch}
      refreshing={query.isRefetching}
    >
      <SearchField value={queryText} onChangeText={setQueryText} placeholder="Search alerts" />
      <FilterChips
        value={filter}
        onChange={(id) => setFilter(id as Filter)}
        options={[
          { id: 'open', label: 'Open' },
          { id: 'acknowledged', label: 'Acknowledged' },
          { id: 'closed', label: 'Closed' },
          { id: 'all', label: 'All' },
        ]}
      />
      {visible.length === 0 ? (
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary }}>No alerts in this view.</Text>
      ) : (
        visible.map((alert) => <AlertRow key={alert.id} alert={alert} />)
      )}
    </StaffPage>
  );
}

function AlertRow({ alert }: { alert: SafeguardingAlertRecord }) {
  const title = alert.reference_number || 'Alert';
  return (
    <StatusRow
      name={title}
      title={title}
      subtitle={alert.description?.trim() || staffLabel(alert.status)}
      chip={staffLabel(alert.priority)}
      tone={statusTone(alert.priority)}
    />
  );
}
