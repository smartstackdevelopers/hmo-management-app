import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState, type ReactNode } from 'react';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { InitialsTile, StatTiles, titleCase } from '@/components/dashboard/mobileChrome';
import { repairPriorityTone, repairStatusText, repairStatusTone } from '@/components/maintenance/repairTone';
import { DraftBadge, Feedback, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip, type Tone } from '@/components/ui/Chip';
import { HeroCard } from '@/components/ui/HeroCard';
import { Avatar } from '@/components/ui/ListRow';
import { QuickActions, type QuickAction } from '@/components/ui/QuickActions';
import { Screen } from '@/components/ui/Screen';
import { Section } from '@/components/ui/Section';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { useStaffDrafts } from '@/hooks/useStaffDrafts';
import { HmoreApiError, hmoreErrorMessage } from '@/lib/hmore/client';
import { listOwnTenants } from '@/lib/hmore/services/tenants';
import type { ApprovalInboxItem } from '@/lib/hmore/services/staff/approvals';
import { listApprovalInbox } from '@/lib/hmore/services/staff/approvals';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';
import { listHandovers } from '@/lib/hmore/services/staff/handovers';
import { listOrganisationMemberships } from '@/lib/hmore/services/staff/memberships';
import { listSafeguardingAlerts, type SafeguardingAlertRecord } from '@/lib/hmore/services/staff/safeguardingAlerts';
import { listOwnTasks, type StaffTask } from '@/lib/hmore/services/staff/tasks';
import { listVisits, type StaffVisit } from '@/lib/hmore/services/staff/visits';
import { listAssignedWorkOrders } from '@/lib/hmore/services/staff/workOrders';
import type { MaintenanceRequest } from '@/lib/hmore/types';
import { hasPermission } from '@/lib/hmore/roles';

const DONE_VISIT = new Set(['completed', 'cancelled', 'missed']);
const DONE_TASK = new Set(['completed', 'cancelled', 'done']);
const CLOSED_JOB = new Set(['completed', 'closed', 'cancelled']);
const CLOSED_APPROVAL = new Set(['approved', 'rejected', 'completed', 'cancelled', 'declined']);
const CLOSED_ALERT = new Set(['closed', 'resolved', 'acknowledged', 'cancelled']);

type ActivityRow = {
  key: string;
  name: string;
  title: string;
  meta: string;
  chip: string;
  tone: Tone;
  onPress: () => void;
};

async function orNull<T>(task: () => Promise<T>): Promise<T | null> {
  try {
    return await task();
  } catch (error) {
    if (error instanceof HmoreApiError && (error.status === 400 || error.status === 403 || error.status === 404)) {
      return null;
    }
    throw error;
  }
}

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

function formatClock(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function isSameLocalDay(iso: string, now = new Date()): boolean {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return false;
  return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth() && date.getDate() === now.getDate();
}

function inThisWeek(iso: string, now = new Date()): boolean {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return false;
  const day = now.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + mondayOffset);
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  return date >= start && date < end;
}

function endOfToday(): number {
  const date = new Date();
  date.setHours(23, 59, 59, 999);
  return date.getTime();
}

export function StaffHome() {
  const { user } = useAuth();
  if (user?.role === 'organisation_admin') return <OrgAdminHome />;
  if (user?.role === 'contractor') return <ContractorHome />;
  return <SupportWorkerHome />;
}

function SupportWorkerHome() {
  const { user } = useAuth();
  const { prefs, fontScale, t } = useI18n();
  const visitsQuery = useQuery({
    queryKey: ['hmore', 'staff', 'visits'],
    queryFn: () => listVisits(),
  });
  const tasksQuery = useQuery({
    queryKey: ['hmore', 'staff', 'tasks', user?.id],
    queryFn: () => orNull(() => listOwnTasks(user?.id || '')),
    enabled: !!user?.id,
  });
  const caseloadQuery = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', user?.role],
    queryFn: () => orNull(() => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' })),
  });
  const handoversQuery = useQuery({
    queryKey: ['hmore', 'staff', 'handovers', 'home'],
    queryFn: () => orNull(() => listHandovers(user?.role, { page: 1, page_size: 50, pending_only: true })),
  });

  if (visitsQuery.isLoading || tasksQuery.isLoading || caseloadQuery.isLoading || handoversQuery.isLoading) {
    return <LoadingScreen message="Loading..." />;
  }
  if (visitsQuery.isError) {
    return <ErrorState message={hmoreErrorMessage(visitsQuery.error, 'Could not load visits')} onRetry={visitsQuery.refetch} />;
  }

  const contrast = prefs.highContrast;
  const name = user?.firstName?.trim() || 'there';
  const fullName = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || name;
  const today = new Intl.DateTimeFormat('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
  const visits = visitsQuery.data?.items ?? [];
  const tasks = tasksQuery.data?.items ?? [];
  const names = new Map(
    (caseloadQuery.data?.items ?? []).map((row) => [
      row.tenant_id,
      row.tenant_preferred_name || row.tenant_full_name || '',
    ]),
  );
  const upcoming = visits
    .filter((visit) => !DONE_VISIT.has(visit.status))
    .sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());
  const next = upcoming.find((visit) => new Date(visit.scheduled_at).getTime() >= Date.now()) ?? upcoming[0];
  const visitsToday = visits.filter((visit) => visit.status !== 'cancelled' && isSameLocalDay(visit.scheduled_at));
  const tasksDue = tasks.filter((task) => {
    if (DONE_TASK.has(task.status)) return false;
    if (task.overdue) return true;
    return !!task.due_at && new Date(task.due_at).getTime() <= endOfToday();
  });
  const handoverValue = handoversQuery.isLoading ? '—' : handoversQuery.data ? String(handoversQuery.data.total ?? handoversQuery.data.items.length) : '—';
  const nextName = next ? names.get(next.tenant_id) || next.purpose || titleCase(next.visit_type) : '';
  const nextClock = next ? formatClock(next.scheduled_at) : null;
  const rows = supportActivity(upcoming, tasksDue, names);

  return (
    <HomeFrame
      kicker={today}
      name={name}
      fullName={fullName}
      contrast={contrast}
      fontScale={fontScale}
      refreshing={visitsQuery.isRefetching || tasksQuery.isRefetching || caseloadQuery.isRefetching || handoversQuery.isRefetching}
      onRefresh={() => {
        visitsQuery.refetch();
        tasksQuery.refetch();
        caseloadQuery.refetch();
        handoversQuery.refetch();
      }}
    >
      <HeroCard
        kicker="Next visit"
        value={next ? (nextClock ? `${nextClock} · ${nextName}` : nextName) : undefined}
        title={next ? undefined : 'No visit scheduled'}
        subtitle={next ? [next.location, next.purpose && names.get(next.tenant_id) ? next.purpose : null].filter(Boolean).join(' · ') || titleCase(next.visit_type) : 'Assigned visits show up here.'}
        ctaLabel="Start visit"
        onCta={() => router.push(next ? `/(app)/staff/visits?visitId=${next.id}` : '/(app)/staff/visits')}
      />
      <StatTiles
        highContrast={contrast}
        items={[
          { value: String(visitsToday.length), label: 'Visits today' },
          { value: tasksQuery.data ? String(tasksDue.length) : '—', label: 'Tasks due' },
          { value: handoverValue, label: 'Handover' },
        ]}
      />
      <Section title={t('communityHub.quickActions')}>
        <QuickActions
          actions={[
            { key: 'log', label: 'Daily log', icon: 'create-outline', tone: 'blue', onPress: () => router.push('/(app)/(tabs)/notes') },
            { key: 'incident', label: 'Incident', icon: 'alert-circle-outline', tone: 'amber', onPress: () => router.push('/(app)/staff/incidents') },
            { key: 'handover', label: 'Handover', icon: 'swap-horizontal-outline', tone: 'indigo', onPress: () => router.push('/(app)/staff/handovers') },
            { key: 'safeguard', label: 'Safeguard', icon: 'shield-outline', tone: 'green', onPress: () => router.push('/(app)/staff/safeguarding-alerts') },
          ]}
        />
      </Section>
      <DraftSync />
      <ActivitySection
        contrast={contrast}
        empty="Assigned visits and tasks show up here."
        rows={rows}
        onSeeAll={() => router.push('/(app)/staff/visits')}
      />
    </HomeFrame>
  );
}

function ContractorHome() {
  const { user } = useAuth();
  const { prefs, fontScale, t } = useI18n();
  const ordersQuery = useQuery({
    queryKey: ['hmore', 'staff', 'work-orders'],
    queryFn: listAssignedWorkOrders,
  });

  if (ordersQuery.isLoading) return <LoadingScreen message="Loading..." />;
  if (ordersQuery.isError) {
    return <ErrorState message={hmoreErrorMessage(ordersQuery.error, 'Could not load work orders')} onRetry={ordersQuery.refetch} />;
  }

  const contrast = prefs.highContrast;
  const name = user?.firstName?.trim() || 'there';
  const fullName = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || name;
  const orders = ordersQuery.data?.items ?? [];
  const open = orders.filter((order) => !CLOSED_JOB.has(order.status));
  const todayJobs = open
    .filter((order) => !!order.scheduled_visit_at && isSameLocalDay(order.scheduled_visit_at))
    .sort((a, b) => new Date(a.scheduled_visit_at || 0).getTime() - new Date(b.scheduled_visit_at || 0).getTime());
  const weekJobs = open.filter((order) => !!order.scheduled_visit_at && inThisWeek(order.scheduled_visit_at));
  const signOff = orders.filter(
    (order) => order.status !== 'cancelled' && order.requires_approval && order.approval_status !== 'approved' && order.approval_status !== 'rejected',
  );
  const focus = todayJobs.length > 0 ? todayJobs : open;
  const first = focus[0];
  const firstClock = todayJobs[0] ? formatClock(todayJobs[0].scheduled_visit_at) : null;
  const heroValue = todayJobs.length
    ? `${todayJobs.length} job${todayJobs.length === 1 ? '' : 's'}${firstClock ? ` · first at ${firstClock}` : ''}`
    : open.length
      ? `${open.length} open`
      : undefined;
  const heroKicker = todayJobs.length > 0 || open.length === 0 ? 'Today' : 'Open jobs';

  return (
    <HomeFrame
      kicker={greeting()}
      name={name}
      fullName={fullName}
      contrast={contrast}
      fontScale={fontScale}
      refreshing={ordersQuery.isRefetching}
      onRefresh={ordersQuery.refetch}
    >
      <HeroCard
        kicker={heroKicker}
        value={heroValue}
        title={heroValue ? undefined : 'No jobs scheduled'}
        subtitle={first?.title || 'Assigned jobs show up here.'}
        ctaLabel="Start route"
        onCta={() => router.push('/(app)/(tabs)/work-orders')}
      />
      <StatTiles
        highContrast={contrast}
        items={[
          { value: String(todayJobs.length), label: 'Today' },
          { value: String(weekJobs.length), label: 'This week' },
          { value: String(signOff.length), label: 'Need sign-off' },
        ]}
      />
      <Section title={t('communityHub.quickActions')}>
        <QuickActions actions={contractorActions()} />
      </Section>
      <DraftSync />
      <ActivitySection
        contrast={contrast}
        empty="Today's jobs show up here."
        rows={focus.slice(0, 4).map(jobRow)}
        onSeeAll={() => router.push('/(app)/(tabs)/work-orders')}
      />
    </HomeFrame>
  );
}

function contractorActions(): QuickAction[] {
  return [
    { key: 'jobs', label: 'Jobs', icon: 'construct-outline', tone: 'blue', onPress: () => router.push('/(app)/(tabs)/work-orders') },
    { key: 'schedule', label: 'Schedule', icon: 'calendar-outline', tone: 'indigo', onPress: () => router.push('/(app)/(tabs)/schedule') },
    { key: 'photos', label: 'Photos', icon: 'camera-outline', tone: 'amber', onPress: () => router.push('/(app)/(tabs)/evidence') },
    { key: 'invoice', label: 'Invoice', icon: 'document-text-outline', tone: 'green', onPress: () => router.push('/(app)/documents') },
  ];
}

function OrgAdminHome() {
  const { user, hmore } = useAuth();
  const { prefs, fontScale, t } = useI18n();
  const canReview = hasPermission(hmore?.rbac.permissions, 'approvals.inbox.read');
  const canListStaff = hasPermission(hmore?.rbac.permissions, 'organisation.users.read');
  const organisationId = hmore?.rbac.active_organisation_id;
  const approvalsQuery = useQuery({
    queryKey: ['hmore', 'staff', 'approvals'],
    queryFn: () => orNull(() => listApprovalInbox()),
    enabled: canReview,
  });
  const tenantsQuery = useQuery({
    queryKey: ['hmore', 'tenants', 'org-home'],
    queryFn: () => orNull(() => listOwnTenants()),
  });
  const staffQuery = useQuery({
    queryKey: ['hmore', 'org-memberships', organisationId],
    queryFn: () => orNull(() => listOrganisationMemberships(organisationId || '')),
    enabled: canListStaff && !!organisationId,
  });
  const alertsQuery = useQuery({
    queryKey: ['hmore', 'safeguarding-alerts', 'home'],
    queryFn: () => orNull(() => listSafeguardingAlerts()),
  });

  const loading =
    (canReview && approvalsQuery.isLoading) ||
    tenantsQuery.isLoading ||
    alertsQuery.isLoading ||
    (canListStaff && !!organisationId && staffQuery.isLoading);
  if (loading) return <LoadingScreen message="Loading..." />;

  const contrast = prefs.highContrast;
  const name = user?.firstName?.trim() || 'there';
  const fullName = `${user?.firstName ?? ''} ${user?.lastName ?? ''}`.trim() || name;
  const pending = (approvalsQuery.data?.items ?? []).filter((item) => !CLOSED_APPROVAL.has(item.status.toLowerCase()));
  const alerts = (alertsQuery.data ?? []).filter((alert) => !CLOSED_ALERT.has(alert.status.toLowerCase()));
  const staffCount = staffQuery.data
    ? new Set(
        staffQuery.data.memberships
          .filter((row) => row.status === 'active' && row.role !== 'tenant')
          .map((row) => row.user_id),
      ).size
    : null;
  const approvalValue = !canReview ? undefined : approvalsQuery.data ? pending.length : null;
  const subtitle = approvalValue == null
    ? 'Pending approvals show up here when this account can read the inbox.'
    : sourceSummary(pending);

  return (
    <HomeFrame
      kicker={greeting()}
      name={name}
      fullName={fullName}
      contrast={contrast}
      fontScale={fontScale}
      refreshing={approvalsQuery.isRefetching || tenantsQuery.isRefetching || staffQuery.isRefetching || alertsQuery.isRefetching}
      onRefresh={() => {
        if (canReview) approvalsQuery.refetch();
        tenantsQuery.refetch();
        if (canListStaff) staffQuery.refetch();
        alertsQuery.refetch();
      }}
    >
      <HeroCard
        kicker="Pending approvals"
        value={approvalValue != null ? `${approvalValue} request${approvalValue === 1 ? '' : 's'} waiting` : undefined}
        title={approvalValue == null ? 'Approvals unavailable' : undefined}
        subtitle={subtitle || 'Nothing is waiting.'}
        ctaLabel={canReview ? 'Review now' : undefined}
        onCta={canReview ? () => router.push('/(app)/staff/approvals') : undefined}
      />
      <StatTiles
        highContrast={contrast}
        items={[
          { value: tenantsQuery.data ? String(tenantsQuery.data.total ?? tenantsQuery.data.items.length) : '—', label: 'Tenants' },
          { value: staffCount == null ? '—' : String(staffCount), label: 'Staff' },
          { value: alertsQuery.data ? String(alerts.length) : '—', label: 'Alerts' },
        ]}
      />
      <Section title={t('communityHub.quickActions')}>
        <QuickActions
          actions={[
            canReview
              ? { key: 'approvals', label: 'Approvals', icon: 'checkmark-done-outline', tone: 'blue' as const, onPress: () => router.push('/(app)/staff/approvals') }
              : { key: 'tasks', label: 'Tasks', icon: 'checkbox-outline', tone: 'blue' as const, onPress: () => router.push('/(app)/staff/tasks') },
            { key: 'tenants', label: 'Tenants', icon: 'people-outline', tone: 'indigo', onPress: () => router.push('/(app)/(tabs)/caseload') },
            { key: 'alerts', label: 'Alerts', icon: 'notifications-outline', tone: 'amber', onPress: () => router.push('/(app)/staff/safeguarding-alerts') },
            { key: 'incidents', label: 'Incidents', icon: 'alert-circle-outline', tone: 'green', onPress: () => router.push('/(app)/staff/incidents') },
          ]}
        />
      </Section>
      <DraftSync />
      <ActivitySection
        contrast={contrast}
        empty="Approvals and alerts that need attention show up here."
        rows={[...pending.slice(0, 3).map(approvalRow), ...alerts.slice(0, 2).map(alertRow)]}
        onSeeAll={() => router.push(canReview ? '/(app)/staff/approvals' : '/(app)/notifications')}
      />
    </HomeFrame>
  );
}

function sourceSummary(items: ApprovalInboxItem[]): string {
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = item.source_type.replace(/_/g, ' ');
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts.entries()]
    .slice(0, 3)
    .map(([key, count]) => `${count} ${key}`)
    .join(' · ');
}

function supportActivity(visits: StaffVisit[], tasks: StaffTask[], names: Map<string, string>): ActivityRow[] {
  const visitRows: ActivityRow[] = visits.slice(0, 3).map((visit) => {
    const who = names.get(visit.tenant_id) || visit.purpose || titleCase(visit.visit_type);
    const clock = formatClock(visit.scheduled_at);
    return {
      key: visit.id,
      name: who,
      title: who,
      meta: [clock, visit.location].filter(Boolean).join(' · ') || titleCase(visit.visit_type),
      chip: titleCase(visit.status),
      tone: statusTone(visit.status),
      onPress: () => router.push(`/(app)/staff/visits?visitId=${visit.id}`),
    };
  });
  const taskRows: ActivityRow[] = tasks.slice(0, 4 - visitRows.length).map((task) => ({
    key: task.id,
    name: task.title,
    title: task.title,
    meta: task.due_at ? formatUKDate(task.due_at) : titleCase(task.priority),
    chip: task.overdue ? 'Overdue' : titleCase(task.status),
    tone: task.overdue ? 'red' : statusTone(task.status),
    onPress: () => router.push(`/(app)/staff/tasks?taskId=${task.id}`),
  }));
  return [...visitRows, ...taskRows];
}

function jobRow(order: MaintenanceRequest): ActivityRow {
  const flagged = order.priority === 'urgent' || order.priority === 'emergency' || order.priority === 'high';
  const clock = formatClock(order.scheduled_visit_at);
  return {
    key: order.id,
    name: order.title,
    title: order.title,
    meta: [order.reference_number, clock || (order.reported_at ? formatUKDate(order.reported_at) : null)].filter(Boolean).join(' · '),
    chip: flagged ? titleCase(order.priority) : repairStatusText(order.status),
    tone: flagged ? repairPriorityTone(order.priority) : repairStatusTone(order.status),
    onPress: () => router.push(`/(app)/staff/work-order/${order.id}`),
  };
}

function approvalRow(item: ApprovalInboxItem): ActivityRow {
  return {
    key: `${item.source_type}:${item.source_id}`,
    name: item.title,
    title: item.title,
    meta: `${item.reference} · ${item.source_type.replace(/_/g, ' ')}`,
    chip: titleCase(item.status),
    tone: statusTone(item.status),
    onPress: () => router.push('/(app)/staff/approvals'),
  };
}

function alertRow(alert: SafeguardingAlertRecord): ActivityRow {
  return {
    key: alert.id,
    name: alert.reference_number || 'Alert',
    title: 'Safeguarding alert',
    meta: [alert.reference_number, titleCase(alert.status)].filter(Boolean).join(' · '),
    chip: titleCase(alert.priority),
    tone: statusTone(alert.priority),
    onPress: () => router.push('/(app)/staff/safeguarding-alerts'),
  };
}

function HomeFrame({
  kicker,
  name,
  fullName,
  contrast,
  fontScale,
  refreshing,
  onRefresh,
  children,
}: {
  kicker: string;
  name: string;
  fullName: string;
  contrast: boolean;
  fontScale: number;
  refreshing: boolean;
  onRefresh: () => void;
  children: ReactNode;
}) {
  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.secondary} />}
    >
      <View style={styles.top}>
        <View style={styles.topCopy}>
          <Text style={[styles.kicker, contrast && styles.contrastText]}>{kicker}</Text>
          <Text style={[styles.title, contrast && styles.contrastText, { fontSize: 32 * fontScale }]} numberOfLines={1}>
            {name}
          </Text>
        </View>
        <Avatar name={fullName} size={48} />
      </View>
      {children}
    </Screen>
  );
}

function ActivitySection({
  rows,
  empty,
  contrast,
  onSeeAll,
}: {
  rows: ActivityRow[];
  empty: string;
  contrast: boolean;
  onSeeAll: () => void;
}) {
  return (
    <Section title="Recent activity" actionLabel="See all" onAction={onSeeAll}>
      {rows.length === 0 ? (
        <Text style={[styles.muted, contrast && styles.contrastMuted]}>{empty}</Text>
      ) : (
        <View style={styles.list}>
          {rows.map((row) => (
            <Card key={row.key} style={contrast ? styles.contrastCard : undefined} onPress={row.onPress}>
              <View style={styles.row}>
                <InitialsTile name={row.name} size={40} />
                <View style={styles.copy}>
                  <Text style={styles.rowTitle} numberOfLines={1}>{row.title}</Text>
                  <Text style={styles.rowMeta} numberOfLines={1}>{row.meta}</Text>
                </View>
                <Chip label={row.chip} tone={row.tone} />
              </View>
            </Card>
          ))}
        </View>
      )}
    </Section>
  );
}

function DraftSync() {
  const drafts = useStaffDrafts();
  const [syncNote, setSyncNote] = useState('');

  async function sync() {
    const report = await drafts.sync();
    if (report.offline) {
      setSyncNote('Still offline. Drafts were not sent.');
      return;
    }
    const saved = report.results.filter((item) => item.saved).length;
    const kept = report.results.filter((item) => !item.saved).length;
    setSyncNote(
      kept
        ? `${saved} saved on the server. ${kept} still on this device.`
        : saved
          ? `${saved} saved on the server.`
          : 'No drafts to send.',
    );
  }

  if (drafts.count < 1 && !syncNote) return null;
  return (
    <View style={styles.drafts}>
      <DraftBadge count={drafts.count} />
      {drafts.count > 0 ? <Button title="Sync drafts" onPress={sync} variant="outline" fullWidth /> : null}
      {syncNote ? <Feedback text={syncNote} tone={syncNote.includes('still') || syncNote.includes('offline') ? 'warn' : 'ok'} /> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastMuted: { color: '#111111' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: theme.spacing.md },
  topCopy: { flex: 1, minWidth: 0 },
  kicker: { fontFamily: FONT_SEMIBOLD, color: theme.colors.textSecondary, fontSize: 14 },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.6, marginTop: 2 },
  muted: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20 },
  list: { gap: theme.spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, minWidth: 0 },
  rowTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  rowMeta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 2 },
  drafts: { marginBottom: theme.spacing.md },
});
