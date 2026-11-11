import { useQueries } from '@tanstack/react-query';
import { router } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ListRow } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import {
  communityDirectorySummary,
  employmentApplicationsSummary,
  numberFromUnknown,
  savedJobsSummary,
  skillsSummary,
  trainingSummary,
  wellbeingPrivateSummary,
} from '@/lib/hmore/communityHubSummary';
import { HUB_PRIMARY_LINKS } from '@/lib/hmore/phase5Navigation';
import { listCommunityServicesPage } from '@/lib/hmore/services/community';
import { getApplicationDashboard, getAssessment } from '@/lib/hmore/services/employment';
import { listSavedMatchedJobs, listTrainingRecommendations } from '@/lib/hmore/services/jobMatching';
import { getWellbeingDashboard } from '@/lib/hmore/services/wellbeing';
import { readConnectivity } from '@/lib/hmore/offline/network';

const SECTION_TITLE_KEYS = {
  community_support: 'communityHub.communitySupport',
  help_near_me: 'communityHub.helpNearMe',
  skills_career: 'communityHub.skillsCareer',
  find_jobs: 'communityHub.findJobs',
  job_applications: 'communityHub.jobApplications',
  training: 'communityHub.training',
  wellbeing: 'communityHub.wellbeing',
  daily_routine: 'communityHub.dailyRoutine',
} as const;

export default function CommunityHubScreen() {
  const { t, fontScale, prefs } = useI18n();
  const contrast = prefs.highContrast;

  const [directoryQ, assessmentQ, appsQ, savedQ, trainingQ, wellbeingQ, connectivityQ] = useQueries({
    queries: [
      {
        queryKey: ['hmore', 'community-hub', 'directory'],
        queryFn: () => listCommunityServicesPage({ page: 1, page_size: 1 }),
        retry: 1,
      },
      {
        queryKey: ['hmore', 'community-hub', 'assessment'],
        queryFn: getAssessment,
        retry: 1,
      },
      {
        queryKey: ['hmore', 'community-hub', 'applications'],
        queryFn: getApplicationDashboard,
        retry: 1,
      },
      {
        queryKey: ['hmore', 'community-hub', 'saved-jobs'],
        queryFn: listSavedMatchedJobs,
        retry: 1,
      },
      {
        queryKey: ['hmore', 'community-hub', 'training'],
        queryFn: listTrainingRecommendations,
        retry: 1,
      },
      {
        queryKey: ['hmore', 'community-hub', 'wellbeing'],
        queryFn: getWellbeingDashboard,
        retry: 1,
      },
      {
        queryKey: ['hmore', 'community-hub', 'connectivity'],
        queryFn: () => readConnectivity(),
        retry: 0,
        staleTime: 30_000,
      },
    ],
  });

  const assessment = assessmentQ.data as Record<string, unknown> | undefined;
  const skills = Array.isArray(assessment?.skills) ? assessment!.skills : [];
  const skillSummary = skillsSummary({
    skillCount: skills.length,
    completion: numberFromUnknown(assessment?.completion_percent ?? assessment?.completion),
    error: Boolean(assessmentQ.error),
  });

  const apps = appsQ.data as Record<string, unknown> | undefined;
  const appsSummary = employmentApplicationsSummary({
    total: numberFromUnknown(apps?.total),
    preparing: numberFromUnknown(apps?.preparing),
    interviews: numberFromUnknown(apps?.interviews),
    error: Boolean(appsQ.error),
  });

  const savedPayload = savedQ.data as { items?: unknown[] } | unknown[] | undefined;
  const savedItems = Array.isArray(savedPayload)
    ? savedPayload
    : Array.isArray(savedPayload?.items)
      ? savedPayload.items
      : [];
  const jobsSummary = savedJobsSummary({
    total: savedItems.length,
    error: Boolean(savedQ.error),
  });

  const trainingPayload = trainingQ.data as { items?: unknown[] } | unknown[] | undefined;
  const trainingItems = Array.isArray(trainingPayload)
    ? trainingPayload
    : Array.isArray(trainingPayload?.items)
      ? trainingPayload.items
      : [];
  const trainSummary = trainingSummary({
    total: trainingItems.length,
    error: Boolean(trainingQ.error),
  });

  const wellbeing = wellbeingQ.data as Record<string, unknown> | undefined;
  const progress = (wellbeing?.routine_progress as Record<string, unknown> | undefined) ?? {};
  const wellSummary = wellbeingPrivateSummary({
    todayCheckin: Boolean(wellbeing?.today_checkin),
    latestMood: wellbeing?.latest_mood != null ? String(wellbeing.latest_mood) : null,
    completed: numberFromUnknown(progress.completed),
    planned: numberFromUnknown(progress.planned),
    error: Boolean(wellbeingQ.error),
  });

  const directorySummary = communityDirectorySummary({
    total: directoryQ.data?.total ?? null,
    error: Boolean(directoryQ.error),
  });

  const connectivity = connectivityQ.data;
  const offlineNote =
    connectivity === 'offline'
      ? t('communityHub.offline')
      : connectivity === 'unstable'
        ? t('communityHub.unstable')
        : null;

  const sectionSubtitle: Record<(typeof HUB_PRIMARY_LINKS)[number]['section'], string | null> = {
    community_support: directorySummary,
    help_near_me: t('communityHub.helpNearMeLead'),
    skills_career: skillSummary,
    find_jobs: jobsSummary ?? t('communityHub.findJobsLead'),
    job_applications: appsSummary,
    training: trainSummary,
    wellbeing: wellSummary ?? t('communityHub.wellbeingLead'),
    daily_routine: wellSummary,
  };

  return (
    <Screen style={contrast ? styles.contrast : undefined}>
      <Text style={[styles.title, contrast && styles.contrastText, { fontSize: 26 * fontScale }]}>
        {t('communityHub.title')}
      </Text>
      <Text style={[styles.lead, contrast && styles.contrastMuted]}>{t('communityHub.lead')}</Text>

      {offlineNote ? (
        <Card style={styles.banner}>
          <Text style={styles.bannerText}>{offlineNote}</Text>
          <Button
            title={t('profile.offlineDrafts')}
            variant="secondary"
            onPress={() => router.push('/(app)/offline-drafts')}
          />
        </Card>
      ) : null}

      <Card padded={false} style={styles.group}>
        {HUB_PRIMARY_LINKS.map((link, index) => (
          <View key={link.section}>
            {index > 0 ? <View style={styles.divider} /> : null}
            <ListRow
              title={t(SECTION_TITLE_KEYS[link.section])}
              subtitle={sectionSubtitle[link.section] ?? undefined}
              icon={link.icon}
              onPress={() => router.push(link.href)}
              accessibilityLabel={t(SECTION_TITLE_KEYS[link.section])}
            />
          </View>
        ))}
      </Card>

      <Text style={styles.section}>{t('communityHub.quickActions')}</Text>
      <View style={styles.row}>
        <Button
          title={t('wellbeing.checkin')}
          variant="outline"
          style={styles.half}
          onPress={() => router.push('/(app)/wellbeing-checkin')}
        />
        <Button
          title={t('jobMatching.search')}
          variant="outline"
          style={styles.half}
          onPress={() => router.push('/(app)/job-matching-search')}
        />
      </View>
      <View style={styles.row}>
        <Button
          title={t('nav.helpNearMe')}
          variant="outline"
          style={styles.half}
          onPress={() => router.push('/(app)/help-near-me')}
        />
        <Button
          title={t('employment.cvs')}
          variant="outline"
          style={styles.half}
          onPress={() => router.push('/(app)/employment-cvs')}
        />
      </View>
      <Button
        title={t('communityHub.openDirectory')}
        onPress={() => router.push('/(app)/community')}
        fullWidth
        style={styles.primary}
      />
      <Text style={styles.privacy}>{t('communityHub.privacy')}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastMuted: { color: '#111111' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4 },
  lead: {
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    marginTop: 6,
    marginBottom: theme.spacing.md,
  },
  banner: { marginBottom: theme.spacing.md, gap: 10 },
  bannerText: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 13, lineHeight: 18 },
  group: { marginBottom: theme.spacing.md },
  divider: { height: 1, backgroundColor: theme.colors.borderLight, marginLeft: 60 },
  section: {
    fontFamily: FONT_SEMIBOLD,
    fontSize: 15,
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
  },
  row: { flexDirection: 'row', gap: theme.spacing.sm, marginBottom: theme.spacing.sm },
  half: { flex: 1 },
  primary: { marginTop: theme.spacing.xs },
  privacy: {
    fontFamily: FONT_MEDIUM,
    fontSize: 12,
    lineHeight: 17,
    color: theme.colors.textMuted,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
});
