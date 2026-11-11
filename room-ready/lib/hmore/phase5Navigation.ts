/**
 * F5.6: canonical Phase 5 tenant mobile routes.
 * Screens already exist — this catalogue drives the Community hub and regression tests.
 */
export type Phase5Route = {
  id: string;
  href: `/(app)/${string}`;
  module: 'f51' | 'f52' | 'f53' | 'f54' | 'f55';
  hubSection:
    | 'community_support'
    | 'help_near_me'
    | 'skills_career'
    | 'find_jobs'
    | 'job_applications'
    | 'training'
    | 'wellbeing'
    | 'daily_routine';
};

/** Ionicons glyph names used by ListRow — kept as string to avoid Expo imports in unit tests. */
type IoniconName =
  | 'location-outline'
  | 'navigate-outline'
  | 'school-outline'
  | 'search-outline'
  | 'briefcase-outline'
  | 'ribbon-outline'
  | 'heart-outline'
  | 'time-outline';

export const PHASE5_ROUTES: readonly Phase5Route[] = [
  { id: 'community', href: '/(app)/community', module: 'f51', hubSection: 'community_support' },
  { id: 'help-near-me', href: '/(app)/help-near-me', module: 'f52', hubSection: 'help_near_me' },
  { id: 'employment', href: '/(app)/employment', module: 'f53', hubSection: 'skills_career' },
  { id: 'employment-skills', href: '/(app)/employment-skills', module: 'f53', hubSection: 'skills_career' },
  { id: 'employment-cvs', href: '/(app)/employment-cvs', module: 'f53', hubSection: 'skills_career' },
  { id: 'employment-applications', href: '/(app)/employment-applications', module: 'f53', hubSection: 'job_applications' },
  { id: 'employment-interview', href: '/(app)/employment-interview', module: 'f53', hubSection: 'skills_career' },
  { id: 'employment-roadmap', href: '/(app)/employment-roadmap', module: 'f53', hubSection: 'skills_career' },
  { id: 'job-matching', href: '/(app)/job-matching', module: 'f54', hubSection: 'find_jobs' },
  { id: 'job-matching-search', href: '/(app)/job-matching-search', module: 'f54', hubSection: 'find_jobs' },
  { id: 'job-matching-recommended', href: '/(app)/job-matching-recommended', module: 'f54', hubSection: 'find_jobs' },
  { id: 'job-matching-saved', href: '/(app)/job-matching-saved', module: 'f54', hubSection: 'find_jobs' },
  { id: 'job-matching-training', href: '/(app)/job-matching-training', module: 'f54', hubSection: 'training' },
  { id: 'job-matching-preferences', href: '/(app)/job-matching-preferences', module: 'f54', hubSection: 'find_jobs' },
  { id: 'wellbeing', href: '/(app)/wellbeing', module: 'f55', hubSection: 'wellbeing' },
  { id: 'wellbeing-checkin', href: '/(app)/wellbeing-checkin', module: 'f55', hubSection: 'wellbeing' },
  { id: 'wellbeing-history', href: '/(app)/wellbeing-history', module: 'f55', hubSection: 'wellbeing' },
  { id: 'wellbeing-routines', href: '/(app)/wellbeing-routines', module: 'f55', hubSection: 'daily_routine' },
  { id: 'wellbeing-exercise', href: '/(app)/wellbeing-exercise', module: 'f55', hubSection: 'wellbeing' },
  { id: 'wellbeing-mindfulness', href: '/(app)/wellbeing-mindfulness', module: 'f55', hubSection: 'wellbeing' },
  { id: 'wellbeing-directory', href: '/(app)/wellbeing-directory', module: 'f55', hubSection: 'wellbeing' },
  { id: 'wellbeing-navigator', href: '/(app)/wellbeing-navigator', module: 'f55', hubSection: 'wellbeing' },
] as const;

export const COMMUNITY_HUB_HREF = '/(app)/community-hub' as const;

export const HUB_PRIMARY_LINKS: Array<{
  section: Phase5Route['hubSection'];
  href: `/(app)/${string}`;
  icon: IoniconName;
}> = [
  { section: 'community_support', href: '/(app)/community', icon: 'location-outline' },
  { section: 'help_near_me', href: '/(app)/help-near-me', icon: 'navigate-outline' },
  { section: 'skills_career', href: '/(app)/employment', icon: 'school-outline' },
  { section: 'find_jobs', href: '/(app)/job-matching', icon: 'search-outline' },
  { section: 'job_applications', href: '/(app)/employment-applications', icon: 'briefcase-outline' },
  { section: 'training', href: '/(app)/job-matching-training', icon: 'ribbon-outline' },
  { section: 'wellbeing', href: '/(app)/wellbeing', icon: 'heart-outline' },
  { section: 'daily_routine', href: '/(app)/wellbeing-routines', icon: 'time-outline' },
];

export function phase5ModulesCovered(): Array<'f51' | 'f52' | 'f53' | 'f54' | 'f55'> {
  return ['f51', 'f52', 'f53', 'f54', 'f55'];
}

export function routesForModule(module: Phase5Route['module']): Phase5Route[] {
  return PHASE5_ROUTES.filter((route) => route.module === module);
}
