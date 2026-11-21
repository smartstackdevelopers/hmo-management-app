import { useQueries } from '@tanstack/react-query';
import { useRouter } from 'expo-router';

import { TileGrid } from '@/components/staff/ui';
import { HeroCard } from '@/components/ui/HeroCard';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { numberFromUnknown } from '@/lib/hmore/communityHubSummary';
import { getApplicationDashboard, getAssessment, listCvs } from '@/lib/hmore/services/employment';
import { listSavedMatchedJobs, listTrainingRecommendations } from '@/lib/hmore/services/jobMatching';
import { StyleSheet, Text } from 'react-native';

function countItems(payload: unknown): number | null {
  if (Array.isArray(payload)) return payload.length;
  if (payload && typeof payload === 'object' && Array.isArray((payload as { items?: unknown[] }).items)) {
    return (payload as { items: unknown[] }).items.length;
  }
  return null;
}

function cvPercent(cv: Record<string, unknown>): number | null {
  const completion = cv.completion;
  if (typeof completion === 'number') return completion;
  if (completion && typeof completion === 'object') {
    return numberFromUnknown((completion as { percent?: unknown }).percent);
  }
  return null;
}

export default function EmploymentHubScreen() {
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const [cvsQ, appsQ, skillsQ, savedQ, trainingQ] = useQueries({
    queries: [
      { queryKey: ['hmore', 'employment-cvs'], queryFn: listCvs, retry: 1 },
      { queryKey: ['hmore', 'employment-dash'], queryFn: getApplicationDashboard, retry: 1 },
      { queryKey: ['hmore', 'employment-assessment'], queryFn: getAssessment, retry: 1 },
      { queryKey: ['hmore', 'community-hub', 'saved-jobs'], queryFn: listSavedMatchedJobs, retry: 1 },
      { queryKey: ['hmore', 'community-hub', 'training'], queryFn: listTrainingRecommendations, retry: 1 },
    ],
  });

  const cvs = ((cvsQ.data as { items?: Record<string, unknown>[] } | undefined)?.items ?? []) as Record<string, unknown>[];
  const openCv = cvs
    .map((cv) => ({ id: cv.id != null ? String(cv.id) : '', percent: cvPercent(cv) }))
    .find((cv) => cv.id && cv.percent != null && cv.percent < 100);
  const apps = appsQ.data as Record<string, unknown> | undefined;
  const appTotal = numberFromUnknown(apps?.total);
  const preparing = numberFromUnknown(apps?.preparing);
  const skills = (skillsQ.data as { skills?: unknown[] } | undefined)?.skills;
  const skillCount = Array.isArray(skills) ? skills.length : null;
  const savedCount = savedQ.error ? null : countItems(savedQ.data);
  const trainingCount = trainingQ.error ? null : countItems(trainingQ.data);
  const heroSubtitle = openCv?.percent != null
    ? `${t('employment.completion')}: ${Math.round(openCv.percent)}%`
    : t('employment.lead');

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 28 * fontScale }]} accessibilityRole="header">{t('employment.title')}</Text>
      <Text style={styles.lead}>{t('employment.lead')}</Text>
      <HeroCard
        kicker={t('employment.cvs')}
        title={openCv ? t('employment.preview') : t('employment.cvs')}
        subtitle={heroSubtitle}
        ctaLabel={t('employment.cvs')}
        onCta={() => router.push(openCv?.id ? `/(app)/employment-cv/${openCv.id}` : '/(app)/employment-cvs')}
      />
      <TileGrid
        tiles={[
          {
            key: 'jobs',
            title: t('jobMatching.title'),
            subtitle: savedCount == null ? null : `${savedCount} ${t('jobMatching.saved')}`,
            onPress: () => router.push('/(app)/job-matching'),
          },
          {
            key: 'cvs',
            title: t('employment.cvs'),
            subtitle: cvsQ.data ? String(cvs.length) : null,
            onPress: () => router.push('/(app)/employment-cvs'),
          },
          {
            key: 'apps',
            title: t('employment.applications'),
            subtitle: appTotal == null ? null : `${appTotal}${preparing != null ? ` · ${preparing} ${t('employment.preparing')}` : ''}`,
            onPress: () => router.push('/(app)/employment-applications'),
          },
          {
            key: 'interview',
            title: t('employment.interview'),
            onPress: () => router.push('/(app)/employment-interview'),
          },
          {
            key: 'skills',
            title: t('employment.skills'),
            subtitle: skillCount == null ? null : String(skillCount),
            onPress: () => router.push('/(app)/employment-skills'),
          },
          {
            key: 'training',
            title: t('jobMatching.training'),
            subtitle: trainingCount == null ? null : String(trainingCount),
            onPress: () => router.push('/(app)/job-matching-training'),
          },
        ]}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.xs },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginBottom: theme.spacing.md },
});
