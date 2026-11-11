import { readFileSync, existsSync } from 'fs';
import path from 'path';

import {
  communityDirectorySummary,
  employmentApplicationsSummary,
  savedJobsSummary,
  skillsSummary,
  trainingSummary,
  wellbeingPrivateSummary,
} from '@/lib/hmore/communityHubSummary';
import {
  COMMUNITY_HUB_HREF,
  HUB_PRIMARY_LINKS,
  PHASE5_ROUTES,
  phase5ModulesCovered,
  routesForModule,
} from '@/lib/hmore/phase5Navigation';
import { translate } from '@/lib/i18n';

const appRoot = path.join(__dirname, '../app/(app)');

describe('F5.6 Phase 5 navigation catalogue', () => {
  it('covers F5.1–F5.5 modules', () => {
    expect(phase5ModulesCovered()).toEqual(['f51', 'f52', 'f53', 'f54', 'f55']);
    expect(routesForModule('f51').some((r) => r.id === 'community')).toBe(true);
    expect(routesForModule('f52').some((r) => r.id === 'help-near-me')).toBe(true);
    expect(routesForModule('f53').some((r) => r.id === 'employment-cvs')).toBe(true);
    expect(routesForModule('f54').some((r) => r.id === 'job-matching-recommended')).toBe(true);
    expect(routesForModule('f55').some((r) => r.id === 'wellbeing-navigator')).toBe(true);
  });

  it('registers community hub and every Phase 5 screen file', () => {
    expect(COMMUNITY_HUB_HREF).toBe('/(app)/community-hub');
    expect(existsSync(path.join(appRoot, 'community-hub.tsx'))).toBe(true);
    for (const route of PHASE5_ROUTES) {
      const relative = route.href.replace('/(app)/', '');
      const filePath = relative.includes('[')
        ? path.join(appRoot, `${relative}.tsx`)
        : path.join(appRoot, `${relative}.tsx`);
      expect(existsSync(filePath)).toBe(true);
    }
  });

  it('exposes eight hub primary links without inventing data', () => {
    expect(HUB_PRIMARY_LINKS).toHaveLength(8);
    expect(HUB_PRIMARY_LINKS.map((item) => item.section)).toEqual([
      'community_support',
      'help_near_me',
      'skills_career',
      'find_jobs',
      'job_applications',
      'training',
      'wellbeing',
      'daily_routine',
    ]);
  });
});

describe('F5.6 community hub summaries', () => {
  it('formats directory counts from real totals only', () => {
    expect(communityDirectorySummary({ total: null })).toBeNull();
    expect(communityDirectorySummary({ error: true, total: 3 })).toBeNull();
    expect(communityDirectorySummary({ total: 0 })).toBe('No published local services yet.');
    expect(communityDirectorySummary({ total: 2 })).toBe('2 published local services.');
  });

  it('formats employment and job matching summaries without fake stats', () => {
    expect(employmentApplicationsSummary({})).toBeNull();
    expect(employmentApplicationsSummary({ total: 0 })).toBe('No job applications recorded yet.');
    expect(employmentApplicationsSummary({ total: 3, preparing: 1, interviews: 1 })).toContain('3 applications');
    expect(savedJobsSummary({ total: 0 })).toBe('No saved jobs yet.');
    expect(trainingSummary({ total: 4 })).toBe('4 training suggestions.');
    expect(skillsSummary({ skillCount: 0 })).toBe('No skills recorded yet.');
  });

  it('keeps wellbeing summary private-friendly and non-clinical', () => {
    expect(wellbeingPrivateSummary({})).toBeNull();
    expect(wellbeingPrivateSummary({ todayCheckin: true, latestMood: 'very_good', completed: 1, planned: 2 })).toBe(
      'Check-in done today · Mood: very good · Routines 1/2.',
    );
    const privacy = translate('en', 'communityHub.privacy').toLowerCase();
    expect(privacy).toContain('not a medical service');
    expect(privacy).toContain('job ranking');
  });
});

describe('F5.6 wiring in tenant shell', () => {
  it('wires community hub into home, account and stack layout', () => {
    const home = readFileSync(path.join(__dirname, '../components/tenant/TenantHome.tsx'), 'utf8');
    const account = readFileSync(path.join(__dirname, '../components/tenant/HmoreAccount.tsx'), 'utf8');
    const layout = readFileSync(path.join(__dirname, '../app/(app)/_layout.tsx'), 'utf8');
    const hub = readFileSync(path.join(appRoot, 'community-hub.tsx'), 'utf8');
    expect(home).toContain("router.push('/(app)/community-hub')");
    expect(account).toContain("router.push('/(app)/community-hub')");
    expect(layout).toContain('community-hub');
    expect(hub).toContain('listCommunityServicesPage');
    expect(hub).toContain('getWellbeingDashboard');
    expect(hub).toContain('getApplicationDashboard');
    expect(hub).toContain('listSavedMatchedJobs');
    expect(hub).not.toMatch(/sample|fake|mock job|lorem/i);
  });

  it('does not put private mood on the shared TenantHome dashboard', () => {
    const home = readFileSync(path.join(__dirname, '../components/tenant/TenantHome.tsx'), 'utf8');
    expect(home.toLowerCase()).not.toContain('mood');
    expect(home.toLowerCase()).not.toContain('checkin');
    expect(home.toLowerCase()).not.toContain('wellbeing');
  });
});
