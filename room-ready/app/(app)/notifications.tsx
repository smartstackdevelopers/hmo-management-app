import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';

import { FilterChips, InitialsTile, SearchField, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { StaffAlertList } from '@/components/staff/StaffAlertList';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { ListScreen } from '@/components/ui/ListScreen';
import { ScreenHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { staffShellActive } from '@/constants/navigation';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { useMarkNotificationRead, useNotifications } from '@/hooks/useApi';
import { NotificationItem } from '@/lib/api';
import { HmoreApiError } from '@/lib/hmore/client';
import { getAnnouncement, listAnnouncements } from '@/lib/hmore/services/communications';
import type { AnnouncementSummary } from '@/lib/hmore/types';
import { navigateFromNotification } from '@/lib/notificationNavigation';
import { router } from 'expo-router';

type NoticeFilter = 'all' | 'unread' | 'announcements';

type Row = {
  id: string;
  name: string;
  title: string;
  meta: string;
  chip?: string;
  tone?: Tone;
  day: string;
  onPress: () => void;
};

async function loadAnnouncements(): Promise<AnnouncementSummary[]> {
  try {
    return await listAnnouncements();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 400 || error.status === 403 || error.status === 404)) return [];
    throw error;
  }
}

function dayKey(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const today = new Date();
  return date.toDateString() === today.toDateString() ? 'Today' : formatUKDate(iso);
}

function notificationRow(item: NotificationItem, onPress: () => void): Row {
  let chip: string | undefined;
  let tone: Tone | undefined;
  if (!item.read) {
    chip = 'New';
    tone = 'blue';
  } else if (item.severity && item.severity !== 'info') {
    chip = item.severity === 'critical' ? 'Critical' : item.severity === 'high' ? 'High' : 'Medium';
    tone = item.severity === 'critical' ? 'red' : item.severity === 'high' ? 'amber' : 'indigo';
  }
  return {
    id: item.id,
    name: item.title,
    title: item.title,
    meta: [item.body, formatUKDate(item.createdAt)].filter(Boolean).join(' · '),
    chip,
    tone,
    day: dayKey(item.createdAt),
    onPress,
  };
}

export default function NotificationsScreen() {
  const { hmore, user } = useAuth();
  if (staffShellActive(user?.role, !!hmore)) return <StaffAlertList />;
  return <AlertsScreen />;
}

function AlertsScreen() {
  useHideTabHeader();
  const { hmore } = useAuth();
  const { t } = useI18n();
  const { data, isLoading, error, refetch, isRefetching } = useNotifications();
  const announcements = useQuery({
    queryKey: ['hmore', 'announcements', 'notifications'],
    queryFn: loadAnnouncements,
    enabled: !!hmore,
  });
  const markRead = useMarkNotificationRead();
  const [filter, setFilter] = useState<NoticeFilter>('all');
  const [query, setQuery] = useState('');

  const notifications = data?.notifications ?? [];
  const notices = announcements.data ?? [];

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const messageRows = notifications
      .filter((item) => {
        if (filter === 'announcements') return false;
        if (filter === 'unread' && item.read) return false;
        if (!needle) return true;
        return `${item.title} ${item.body}`.toLowerCase().includes(needle);
      })
      .map((item) =>
        notificationRow(item, () => {
          if (!item.read) markRead.mutate(item.id);
          navigateFromNotification(item);
        }),
      );
    const noticeRows: Row[] =
      filter === 'unread'
        ? []
        : notices
            .filter((item) => {
              if (filter === 'all' || filter === 'announcements') {
                if (!needle) return true;
                return `${item.title} ${item.reference_number}`.toLowerCase().includes(needle);
              }
              return false;
            })
            .map((item) => ({
              id: `announcement-${item.id}`,
              name: item.title,
              title: item.title,
              meta: [item.reference_number, item.published_at ? formatUKDate(item.published_at) : null].filter(Boolean).join(' · '),
              chip: 'Notice',
              tone: 'indigo' as Tone,
              day: item.published_at ? dayKey(item.published_at) : '',
              onPress: () => {
                getAnnouncement(item.id)
                  .then((detail) => Alert.alert(detail.title, detail.body || item.reference_number))
                  .catch((err: unknown) => Alert.alert('Notice', err instanceof Error ? err.message : 'Could not open this notice'));
              },
            }));
    return [...messageRows, ...noticeRows];
  }, [notifications, notices, filter, query, markRead]);

  if (isLoading) return <LoadingScreen message="Loading notifications..." />;
  if (error) return <ErrorState message="Could not load notifications" onRetry={refetch} />;

  const chips = [
    { id: 'all', label: 'All' },
    { id: 'unread', label: 'Unread' },
    ...(hmore && announcements.isSuccess ? [{ id: 'announcements', label: 'Announcements' }] : []),
  ];
  const sourceEmpty = notifications.length === 0 && notices.length === 0;

  const sections: { key: string; label?: string; row: Row }[] = [];
  let lastDay = '';
  for (const row of rows) {
    if (row.day && row.day !== lastDay) {
      lastDay = row.day;
      sections.push({ key: `day-${row.day}-${row.id}`, label: row.day, row });
    } else {
      sections.push({ key: row.id, row });
    }
  }

  return (
    <View style={styles.screen}>
      <Pressable onPress={() => router.back()} style={styles.back} accessibilityRole="button" accessibilityLabel="Back">
        <Ionicons name="chevron-back" size={18} color={theme.colors.secondaryDark} />
        <Text style={styles.backText}>Back</Text>
      </Pressable>
      <ListScreen
        data={sections}
        keyExtractor={(item) => item.key}
        refreshing={isRefetching || announcements.isRefetching}
        onRefresh={() => {
          refetch();
          if (hmore) announcements.refetch();
        }}
        padded={false}
        contentContainerStyle={[styles.list, sections.length === 0 && styles.emptyList]}
        ListHeaderComponent={
          <View>
            <ScreenHeader title={t('nav.alerts')} subtitle={`${notifications.length} alert${notifications.length === 1 ? '' : 's'}`} />
            <SearchField value={query} onChangeText={setQuery} placeholder="Search notifications" />
            <FilterChips options={chips} value={filter} onChange={(id) => setFilter(id as NoticeFilter)} />
          </View>
        }
        ListEmptyComponent={
          <EmptyState
            title={sourceEmpty ? 'No notifications' : 'Nothing in this filter'}
            message={sourceEmpty ? 'Alerts about repairs, applications and compliance will appear here.' : 'Try another filter or search.'}
            icon="notifications-outline"
          />
        }
        renderItem={({ item }) => (
          <View>
            {item.label ? <Text style={styles.day}>{item.label}</Text> : null}
            <Card style={styles.card} onPress={item.row.onPress}>
              <View style={styles.row}>
                <InitialsTile name={item.row.name} size={42} />
                <View style={styles.copy}>
                  <Text style={styles.title} numberOfLines={1}>{item.row.title}</Text>
                  {item.row.meta ? <Text style={styles.meta} numberOfLines={2}>{item.row.meta}</Text> : null}
                </View>
                {item.row.chip && item.row.tone ? <Chip label={item.row.chip} tone={item.row.tone} /> : null}
                <Ionicons name="chevron-forward" size={18} color={theme.colors.textMuted} />
              </View>
            </Card>
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: theme.colors.background, paddingTop: theme.spacing.sm },
  back: { flexDirection: 'row', alignItems: 'center', marginLeft: theme.spacing.md },
  backText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 15 },
  list: { paddingHorizontal: theme.spacing.md },
  emptyList: { flexGrow: 1 },
  day: {
    fontFamily: FONT_SEMIBOLD,
    fontSize: 12,
    color: theme.colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    marginBottom: 8,
    marginTop: 4,
  },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  title: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textSecondary, marginTop: 2 },
});
