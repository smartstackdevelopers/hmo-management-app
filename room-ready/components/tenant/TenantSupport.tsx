import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useState } from 'react';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { titleCase, useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { TenantFilterChips } from '@/components/tenant/TenantFilterChips';
import { ActivityRow } from '@/components/tenant/ActivityRow';
import { useConnectivity } from '@/components/tenant/safeFetch';
import { TenantLoadError, TenantOffline } from '@/components/tenant/TenantStates';
import { shortDate, shortTime } from '@/components/tenant/tenantFormat';
import type { Tone } from '@/components/ui/Chip';
import { Screen } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useI18n } from '@/hooks/useI18n';
import { listOwnSupportPlans } from '@/lib/hmore/services/supportPlans';
import { getOwnProfile } from '@/lib/hmore/services/tenants';
import { getTimeline, listAppointments } from '@/lib/hmore/services/timeline';
import type { TimelineItem } from '@/lib/hmore/types';

function statusTone(status: string): Tone {
  const key = status.toLowerCase();
  if (['completed', 'done', 'attended', 'active'].includes(key)) return 'green';
  if (['pending', 'requested', 'awaiting', 'on_hold'].includes(key)) return 'amber';
  if (['cancelled', 'canceled', 'closed'].includes(key)) return 'gray';
  return 'indigo';
}

function timelineTarget(item: TimelineItem): `/(app)/maintenance/${string}` | null {
  if (item.resource_type.toLowerCase().includes('maintenance') && item.resource_id) {
    return `/(app)/maintenance/${item.resource_id}`;
  }
  return null;
}

export function TenantSupport() {
  useHideTabHeader();
  const { hmore } = useAuth();
  const { t, fontScale, prefs } = useI18n();
  const net = useConnectivity();
  const [tab, setTab] = useState<'plan' | 'appointments' | 'activity'>('plan');
  const tenantQuery = useQuery({
    queryKey: ['hmore', 'tenant-me'],
    queryFn: getOwnProfile,
    enabled: hmore?.rbac.active_role === 'tenant',
  });
  const plansQuery = useQuery({
    queryKey: ['hmore', 'support-plans'],
    queryFn: listOwnSupportPlans,
  });
  const tenantId = tenantQuery.data?.id;
  const appointmentsQuery = useQuery({
    queryKey: ['hmore', 'appointments', tenantId],
    queryFn: () => listAppointments(tenantId!),
    enabled: !!tenantId,
  });
  const timelineQuery = useQuery({
    queryKey: ['hmore', 'timeline', tenantId],
    queryFn: () => getTimeline(tenantId!),
    enabled: !!tenantId,
  });

  const offline = net.data === 'offline';
  const loading =
    (tenantQuery.isLoading && tenantQuery.data === undefined) || (plansQuery.isLoading && !plansQuery.data);
  if (loading && tenantQuery.data === undefined && !plansQuery.data) {
    if (offline) return <TenantOffline />;
    return <LoadingScreen message={t('support.loading')} />;
  }
  const error = tenantQuery.error ?? plansQuery.error;
  if (error && !plansQuery.data && tenantQuery.data === undefined) {
    if (offline) return <TenantOffline />;
    return (
      <TenantLoadError
        title={t('support.error')}
        showContact={false}
        onRetry={() => {
          tenantQuery.refetch();
          plansQuery.refetch();
        }}
      />
    );
  }

  const plans = plansQuery.data?.items ?? [];
  const appointments = appointmentsQuery.data?.items ?? [];
  const timeline = (timelineQuery.data?.items ?? []).filter((item) => item.can_view);
  const contrast = prefs.highContrast;
  const needs = tenantQuery.data?.needs_goals?.trim() ?? '';

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={plansQuery.isRefetching || appointmentsQuery.isRefetching || timelineQuery.isRefetching}
          onRefresh={() => {
            tenantQuery.refetch();
            plansQuery.refetch();
            appointmentsQuery.refetch();
            timelineQuery.refetch();
            net.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={[styles.title, { fontSize: 28 * fontScale }]} accessibilityRole="header">
        {t('nav.support')}
      </Text>
      <Text style={[styles.lead, { fontSize: 14 * fontScale }]}>{t('support.lead')}</Text>
      <TenantFilterChips
        options={[
          { id: 'plan' as const, label: t('support.plan') },
          { id: 'appointments' as const, label: t('support.appointments') },
          { id: 'activity' as const, label: t('support.activity') },
        ]}
        value={tab}
        onChange={setTab}
      />
      {!tenantId ? (
        <EmptyState title={t('support.noProfileTitle')} message={t('support.noProfile')} icon="people-outline" />
      ) : null}

      {tab === 'plan' && tenantId ? (
        <View>
          {needs ? (
            <ActivityRow highContrast={contrast} name={t('support.needs')} title={t('support.needs')} meta={needs} />
          ) : null}
          {plans.length === 0 ? (
            <EmptyState compact title={t('support.plan')} message={t('support.emptyPlan')} icon="people-outline" />
          ) : (
            plans.map((plan) => (
              <ActivityRow
                key={plan.id}
                highContrast={contrast}
                name={plan.title}
                title={plan.title}
                meta={[
                  plan.reference_number,
                  plan.tenant_summary || plan.description || '',
                  plan.planned_review_date ? `${t('support.review')} ${shortDate(plan.planned_review_date)}` : '',
                ]
                  .filter(Boolean)
                  .join(' · ')}
                chip={titleCase(plan.status)}
                chipTone={statusTone(plan.status)}
              />
            ))
          )}
        </View>
      ) : null}

      {tab === 'appointments' && tenantId ? (
        <View>
          {appointmentsQuery.error ? (
            <ErrorState
              compact
              title={t('support.error')}
              message={t('states.draftsSafe')}
              actionLabel={t('states.tryAgain')}
              onRetry={() => appointmentsQuery.refetch()}
            />
          ) : appointments.length === 0 ? (
            <EmptyState
              compact
              title={t('support.appointments')}
              message={t('support.emptyAppointments')}
              icon="calendar-outline"
            />
          ) : (
            appointments.map((item) => (
              <ActivityRow
                key={item.id}
                highContrast={contrast}
                name={item.title}
                title={item.title}
                meta={[
                  shortDate(item.starts_at),
                  shortTime(item.starts_at),
                  titleCase(item.appointment_kind),
                  item.location || '',
                ]
                  .filter(Boolean)
                  .join(' · ')}
                chip={titleCase(item.status)}
                chipTone={statusTone(item.status)}
              />
            ))
          )}
        </View>
      ) : null}

      {tab === 'activity' && tenantId ? (
        <View>
          {timelineQuery.error ? (
            <ErrorState
              compact
              title={t('support.error')}
              message={t('states.draftsSafe')}
              actionLabel={t('states.tryAgain')}
              onRetry={() => timelineQuery.refetch()}
            />
          ) : timeline.length === 0 ? (
            <EmptyState compact title={t('support.activity')} message={t('support.emptyActivity')} icon="time-outline" />
          ) : (
            timeline.map((item) => {
              const href = timelineTarget(item);
              return (
                <ActivityRow
                  key={item.dedupe_key}
                  highContrast={contrast}
                  name={item.title}
                  title={item.title}
                  meta={[titleCase(item.activity_type), shortDate(item.occurred_at), item.summary || '']
                    .filter(Boolean)
                    .join(' · ')}
                  chip={item.status ? titleCase(item.status) : undefined}
                  chipTone={item.status ? statusTone(item.status) : 'gray'}
                  onPress={href ? () => router.push(href) : undefined}
                />
              );
            })
          )}
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.5 },
  lead: { fontFamily: FONT_MEDIUM, lineHeight: 20, color: theme.colors.textSecondary, marginTop: 4, marginBottom: theme.spacing.md },
});
