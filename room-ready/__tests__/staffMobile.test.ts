import { readFileSync } from 'fs';
import path from 'path';

import { tabsForRole } from '@/constants/navigation';
import { beginDictation, SPEECH_PERMISSION_MESSAGE, SPEECH_UNSUPPORTED_MESSAGE, speechAvailability } from '@/hooks/useDeviceSpeechToText';
import { staffAlertHref } from '@/lib/hmore/staff/alerts';
import { clearDraft, loadDrafts, saveDraft, syncDrafts, type DraftStorage } from '@/lib/hmore/staff/offlineDrafts';
import { OCCUPANCY_PHASE6_NOTICE, surveySummariesFromResponse } from '@/lib/hmore/staff/occupancyView';
import { isDeviceOnline } from '@/lib/hmore/staff/network';
import { mapHmoreRole } from '@/lib/hmore/roles';
import { assertCanUseCaseload } from '@/lib/hmore/services/staff/access';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';
import { validateStaffUpload } from '@/lib/hmore/uploads';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

jest.mock('expo-web-browser', () => ({
  maybeCompleteAuthSession: jest.fn(),
  openAuthSessionAsync: jest.fn(async () => ({ type: 'dismiss' })),
}));

jest.mock('expo-auth-session', () => ({
  makeRedirectUri: jest.fn(() => 'roomready://auth/callback'),
  AuthRequest: jest.fn(),
  exchangeCodeAsync: jest.fn(),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  getItem: jest.fn(async () => null),
  setItem: jest.fn(async () => undefined),
  removeItem: jest.fn(async () => undefined),
}));

function memoryStore(): DraftStorage & { secure: Map<string, string>; items: Map<string, string> } {
  const secure = new Map<string, string>();
  const items = new Map<string, string>();
  return {
    secure,
    items,
    getSecure: async (key) => secure.get(key) ?? null,
    setSecure: async (key, value) => {
      if (value.length > 2048) throw new Error('SecureStore value is too large');
      secure.set(key, value);
    },
    getItem: async (key) => items.get(key) ?? null,
    setItem: async (key, value) => {
      items.set(key, value);
    },
    removeItem: async (key) => {
      items.delete(key);
    },
  };
}

describe('staff role navigation', () => {
  it('keeps support workers out of the property manager shell', () => {
    expect(mapHmoreRole('support_worker')).toBe('support_worker');
    expect(mapHmoreRole('organisation_admin')).toBe('organisation_admin');
    expect(mapHmoreRole('maintenance_contractor')).toBe('contractor');
    expect(mapHmoreRole('tenant')).toBe('tenant');
    expect(mapHmoreRole('super_admin')).toBe('admin');

    expect(tabsForRole('support_worker', { hmore: true }).map((tab) => tab.name)).toEqual([
      'index',
      'caseload',
      'shifts',
      'notes',
      'more',
    ]);
    expect(tabsForRole('organisation_admin', { hmore: true }).map((tab) => tab.title)).toContain('My Tenants');
    const contractor = tabsForRole('contractor', { hmore: true }).map((tab) => tab.name);
    expect(contractor).toEqual(['index', 'work-orders', 'schedule', 'evidence', 'more']);
    expect(contractor).not.toContain('caseload');
    expect(tabsForRole('contractor', { hmore: false }).map((tab) => tab.title)).toEqual([
      'Jobs',
      'Schedule',
      'Messages',
      'Account',
    ]);
    expect(tabsForRole('tenant', { hmore: true }).map((tab) => tab.name)).toEqual([
      'index',
      'tenancy',
      'maintenance',
      'support',
      'more',
    ]);
  });
});

describe('caseload access', () => {
  it('refuses contractor calls before any request', () => {
    expect(() => assertCanUseCaseload('contractor')).toThrow(/caseload/i);
    expect(() => assertCanUseCaseload('maintenance_contractor')).toThrow(/caseload/i);
    expect(() => listCaseload('contractor')).toThrow(/caseload/i);
    expect(() => assertCanUseCaseload('support_worker')).not.toThrow();
    const src = readFileSync(path.join(__dirname, '../lib/hmore/services/staff/workOrders.ts'), 'utf8');
    expect(src).not.toContain('/caseload');
    expect(src).not.toContain('listCaseload');
  });
});

describe('occupancy surveys', () => {
  it('does not invent people counts', () => {
    const summaries = surveySummariesFromResponse({
      items: [
        {
          id: 'survey-1',
          property_id: 'property-1',
          status: 'completed',
          survey_date: '2026-11-01',
          feasibility_status: 'further_assessment_required',
          feasibility_summary: 'Camera software is out of scope.',
          people_count: 9,
          live_count: 4,
          occupant_count: 3,
        },
      ],
    });
    expect(summaries).toEqual([
      {
        id: 'survey-1',
        property_id: 'property-1',
        status: 'completed',
        survey_date: '2026-11-01',
        feasibility_status: 'further_assessment_required',
        feasibility_summary: 'Camera software is out of scope.',
      },
    ]);
    expect(JSON.stringify(summaries)).not.toMatch(/"people_count"|"live_count"|"occupant_count"/);
    expect(surveySummariesFromResponse({ items: [] })).toEqual([]);
    expect(surveySummariesFromResponse(null)).toEqual([]);
    expect(OCCUPANCY_PHASE6_NOTICE).toContain('Phase 6');
    const screen = readFileSync(path.join(__dirname, '../components/staff/OccupancySurveys.tsx'), 'utf8');
    expect(screen).toContain('OCCUPANCY_PHASE6_NOTICE');
    expect(screen).not.toMatch(/people_count|live_count|occupant_count|headcount/);
    expect(screen).not.toMatch(/There are \d+ people/);
    const liveScreen = readFileSync(path.join(__dirname, '../app/(app)/staff/occupancy.tsx'), 'utf8');
    expect(liveScreen).toContain("occupancy.read");
    expect(liveScreen).toContain('RoomOccupancyLive');
  });
});

describe('offline drafts', () => {
  it('saves, loads, and clears a large note without putting the body in the key store', async () => {
    const store = memoryStore();
    const notes = 'welfare check '.repeat(400);
    expect(notes.length).toBeGreaterThan(2048);
    const saved = await saveDraft(
      { type: 'daily_log', payload: { tenant_id: 'tenant-1', notes, summary: 'Check', activity_category: 'welfare_check' } },
      store,
    );
    const loaded = await loadDrafts(store);
    expect(loaded).toHaveLength(1);
    expect(loaded[0].payload.notes).toBe(notes);
    expect(loaded[0].clientRequestId).toBe(saved.clientRequestId);
    for (const value of store.secure.values()) expect(value.length).toBeLessThanOrEqual(2048);
    expect(store.items.size).toBe(1);
    expect([...store.items.values()][0]).not.toContain(notes);

    const replaced = await saveDraft(
      { type: 'daily_log', payload: { tenant_id: 'tenant-1', notes: 'updated', summary: 'Check', activity_category: 'welfare_check' } },
      store,
    );
    expect(replaced.id).toBe(saved.id);
    expect(replaced.clientRequestId).toBe(saved.clientRequestId);
    expect(await loadDrafts(store)).toHaveLength(1);

    await clearDraft(saved.id, store);
    expect(await loadDrafts(store)).toEqual([]);
  });

  it('clears a draft only after a 2xx response and does not send it twice', async () => {
    const store = memoryStore();
    const draft = await saveDraft({ type: 'visit_update', payload: { visit_id: 'visit-1', status: 'completed' } }, store);
    const calls: string[] = [];
    const failed = await syncDrafts(async () => ({ status: 500, error: 'no' }), async () => true, store);
    expect(failed.results[0]).toMatchObject({ id: draft.id, saved: false, status: 500 });
    expect(await loadDrafts(store)).toHaveLength(1);

    const saved = await syncDrafts(
      async (item) => {
        calls.push(item.id);
        return { status: 200 };
      },
      async () => true,
      store,
    );
    expect(saved.results[0].saved).toBe(true);
    expect(calls).toEqual([draft.id]);
    expect(await loadDrafts(store)).toEqual([]);

    const again = await syncDrafts(
      async () => {
        calls.push('again');
        return { status: 200 };
      },
      async () => true,
      store,
    );
    expect(again.results).toEqual([]);
    expect(calls).toEqual([draft.id]);
  });

  it('does not sync while offline', async () => {
    const store = memoryStore();
    await saveDraft({ type: 'task_update', payload: { task_id: 'task-1', status: 'open' } }, store);
    let called = false;
    const report = await syncDrafts(
      async () => {
        called = true;
        return { status: 200 };
      },
      async () => false,
      store,
    );
    expect(report.offline).toBe(true);
    expect(called).toBe(false);
    expect(await loadDrafts(store)).toHaveLength(1);
  });
});

describe('device speech', () => {
  it('fails safely when recognition is unavailable', async () => {
    expect(speechAvailability(null)).toEqual({ supported: false, message: SPEECH_UNSUPPORTED_MESSAGE });
    expect(
      speechAvailability({
        start() {
          throw new Error('native');
        },
        stop() {
          return undefined;
        },
        requestPermissionsAsync: async () => ({ granted: true }),
        isRecognitionAvailable: () => false,
      }).supported,
    ).toBe(false);

    const denied = await beginDictation({
      start() {
        return undefined;
      },
      stop() {
        return undefined;
      },
      requestPermissionsAsync: async () => ({ granted: false, status: 'denied' }),
      isRecognitionAvailable: () => true,
    });
    expect(denied).toEqual({ ok: false, message: SPEECH_PERMISSION_MESSAGE });

    const crashed = await beginDictation({
      start() {
        throw new Error('unsupported');
      },
      stop() {
        return undefined;
      },
      requestPermissionsAsync: async () => ({ granted: true }),
    });
    expect(crashed).toEqual({ ok: false, message: SPEECH_UNSUPPORTED_MESSAGE });
  });
});

describe('staff alerts and uploads', () => {
  it('opens a record only for a known resource link', () => {
    expect(staffAlertHref({ related_resource_type: 'incident', related_resource_id: '11111111-1111-4111-8111-111111111111' })).toBe(
      '/(app)/staff/incident/11111111-1111-4111-8111-111111111111',
    );
    expect(staffAlertHref({ subject: 'Hello', body: 'no link here' })).toBeNull();
    expect(staffAlertHref({ body: 'hmore://maintenance_request/22222222-2222-4222-8222-222222222222' })).toContain('work-order');
  });

  it('matches the API upload allow-list', () => {
    expect(validateStaffUpload({ name: 'a.txt', mimeType: 'text/plain', size: 10 }, 'photo')).toMatch(/JPEG/);
    expect(validateStaffUpload({ name: 'a.jpg', mimeType: 'image/jpeg', size: 10 * 1024 * 1024 + 1 }, 'photo')).toMatch(/10/);
    expect(validateStaffUpload({ name: 'a.png', mimeType: 'image/png', size: 100 }, 'photo')).toBeNull();
  });

  it('treats a disconnected device as offline without a health ping', async () => {
    await expect(isDeviceOnline({ netInfo: { fetch: async () => ({ isConnected: false }) }, ping: async () => true })).resolves.toBe(false);
  });
});
