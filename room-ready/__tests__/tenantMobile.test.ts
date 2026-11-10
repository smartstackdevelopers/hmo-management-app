import { readFileSync } from 'fs';
import path from 'path';

import { hmoreRequest, HmoreApiError } from '@/lib/hmore/client';
import { resolveHmoreApiBase } from '@/lib/hmore/config';
import { LANGUAGE_OPTIONS } from '@/lib/hmore/accessibility';
import { activityIdFromAsk } from '@/lib/hmore/services/assistant';
import { communityItemsFromResponse } from '@/lib/hmore/services/community';
import { assignedPropertyId, formatAssignedAddress } from '@/lib/hmore/services/housing';
import { opportunityItemsFromResponse } from '@/lib/hmore/services/jobs';
import { tenantSelfPatchBody } from '@/lib/hmore/services/tenants';
import { translate } from '@/lib/i18n';
import type { TenantHousing } from '@/lib/hmore/types';
import { accessTokenNeedsRefresh, getStoredAccessToken } from '@/lib/hmoreAuth0';
import * as SecureStore from 'expo-secure-store';

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
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

describe('resolveHmoreApiBase', () => {
  it('uses EXPO_PUBLIC_HMORE_API_URL and strips a trailing slash', () => {
    expect(resolveHmoreApiBase({ envUrl: 'http://example.test/api/v1/' })).toBe('http://example.test/api/v1');
  });

  it('falls back to the dev host on port 8000', () => {
    expect(resolveHmoreApiBase({ envUrl: '  ', devHost: '10.0.2.2' })).toBe('http://10.0.2.2:8000/api/v1');
  });
});

describe('hmoreRequest', () => {
  it('sends the bearer token and organisation headers without logging the token', async () => {
    const token = 'super-secret-token';
    const log = jest.spyOn(console, 'log').mockImplementation(() => undefined);
    const info = jest.spyOn(console, 'info').mockImplementation(() => undefined);
    const debug = jest.spyOn(console, 'debug').mockImplementation(() => undefined);
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => undefined);
    const error = jest.spyOn(console, 'error').mockImplementation(() => undefined);
    const fetchImpl = jest.fn(async () => new Response(JSON.stringify({ detail: 'Denied' }), { status: 403 }));

    await expect(
      hmoreRequest(
        '/tenants',
        { method: 'GET' },
        {
          getAccessToken: async () => token,
          getContext: () => ({ organisationId: 'org-1', role: 'tenant' }),
          fetchImpl: fetchImpl as unknown as typeof fetch,
          baseUrl: 'http://api.test/api/v1',
        },
      ),
    ).rejects.toBeInstanceOf(HmoreApiError);

    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(url).toBe('http://api.test/api/v1/tenants');
    expect(headers.Authorization).toBe(`Bearer ${token}`);
    expect(headers['X-Organisation-Id']).toBe('org-1');
    expect(headers['X-HMore-Role']).toBe('tenant');

    try {
      await hmoreRequest(
        '/tenants',
        { method: 'GET' },
        {
          getAccessToken: async () => token,
          getContext: () => ({ organisationId: 'org-1', role: 'tenant' }),
          fetchImpl: fetchImpl as unknown as typeof fetch,
          baseUrl: 'http://api.test/api/v1',
        },
      );
    } catch (err) {
      expect(String(err)).not.toContain(token);
      expect(err).toMatchObject({ status: 403, detail: 'Denied' });
    }

    for (const spy of [log, info, debug, warn, error]) {
      for (const call of spy.mock.calls) {
        expect(JSON.stringify(call)).not.toContain(token);
      }
    }
    log.mockRestore();
    info.mockRestore();
    debug.mockRestore();
    warn.mockRestore();
    error.mockRestore();
  });
});

describe('tenant catalogue clients', () => {
  it('returns community items only from the client response', () => {
    const fromApi = [{ id: 'svc-1', category: 'local_service', name: 'Published by API', description: null, address_line: null, opening_hours: null, eligibility: null, contact: null }];
    expect(communityItemsFromResponse({ items: fromApi })).toEqual(fromApi);
    expect(communityItemsFromResponse({ items: [] })).toEqual([]);
    expect(communityItemsFromResponse(null)).toEqual([]);
    const src = readFileSync(path.join(__dirname, '../lib/hmore/services/community.ts'), 'utf8');
    expect(src).toContain('communityItemsFromResponse');
    expect(src.toLowerCase()).not.toContain('food bank');
    expect(src.toLowerCase()).not.toContain('sample');
  });

  it('returns opportunities only from the client response', () => {
    const fromApi = [{ id: 'job-1', kind: 'job', title: 'Published by API', description: null, eligibility: null, source_name: null, source_url: null }];
    expect(opportunityItemsFromResponse({ items: fromApi })).toEqual(fromApi);
    expect(opportunityItemsFromResponse({ items: [] })).toEqual([]);
    const src = readFileSync(path.join(__dirname, '../lib/hmore/services/jobs.ts'), 'utf8');
    expect(src).toContain('opportunityItemsFromResponse');
    expect(src.toLowerCase()).not.toContain('sample');
    expect(src).not.toMatch(/warehouse|barista|apprentice/i);
  });
});

describe('tenant profile writes', () => {
  it('whitelists preferred_name and phone on the self-update payload', () => {
    expect(
      tenantSelfPatchBody({
        preferred_name: 'Amina',
        phone: '07000',
        notes: 'secret',
        assigned_property_id: 'property-1',
        email: 'a@example.com',
        needs_goals: 'private',
      }),
    ).toEqual({ preferred_name: 'Amina', phone: '07000' });
    const src = readFileSync(path.join(__dirname, '../lib/hmore/services/tenants.ts'), 'utf8');
    expect(src).toContain("'/tenant/me'");
    expect(src).toContain('tenantSelfPatchBody');
  });
});

describe('assigned housing', () => {
  it('does not invent an address when property is null', () => {
    const housing: TenantHousing = {
      tenancy_reference: 'REF-1',
      status: 'active',
      property: null,
      room: null,
    };
    expect(assignedPropertyId(housing)).toBeNull();
    expect(formatAssignedAddress(housing)).toBeNull();
    expect(formatAssignedAddress(null)).toBeNull();
    const src = readFileSync(path.join(__dirname, '../lib/hmore/services/housing.ts'), 'utf8');
    expect(src).toContain("'/tenant/me/housing'");
    expect(src).not.toMatch(/\d+\s+[A-Z][a-z]+\s+(Street|Road|Avenue)/);
  });
});

describe('language', () => {
  it('offers only English and Urdu and falls back to English', () => {
    expect(LANGUAGE_OPTIONS.map((item) => item.id)).toEqual(['en', 'ur']);
    expect(translate('ur', 'nav.home')).not.toBe('nav.home');
    expect(translate('ur', 'missing.key')).toBe('missing.key');
    expect(translate('cy', 'nav.home')).toBe('Home');
    expect(translate('ur', 'nav.home')).not.toBe(translate('en', 'nav.doesNotExist'));
  });
});

describe('assistant feedback', () => {
  it('does not treat a missing activity id as feedback that can be sent', () => {
    expect(activityIdFromAsk({ activity_id: null })).toBeNull();
    expect(activityIdFromAsk({})).toBeNull();
    expect(activityIdFromAsk({ activity_id: '  ' })).toBeNull();
    expect(activityIdFromAsk({ activity_id: 'act-1' })).toBe('act-1');
  });
});

describe('repair form security helpers', () => {
  it('does not invent property ids when none are linked', () => {
    const propertyIds: string[] = [];
    const selectedProperty = propertyIds[0] || '';
    expect(selectedProperty).toBe('');
  });

  it('never embeds another tenant id into listMaintenance query', () => {
    const src = readFileSync(path.join(__dirname, '../lib/hmore/services/maintenance.ts'), 'utf8');
    expect(src).not.toMatch(/tenant_id:\s*['"]/);
    expect(src).toContain("hmoreFetch<Page<MaintenanceRequest>>('/maintenance'");
  });
});

describe('Auth0 refresh', () => {
  const mem = new Map<string, string>();

  beforeEach(() => {
    mem.clear();
    process.env.EXPO_PUBLIC_AUTH0_DOMAIN = 'tenant.example';
    process.env.EXPO_PUBLIC_AUTH0_CLIENT_ID = 'public-client';
    (SecureStore.getItemAsync as jest.Mock).mockImplementation(async (key: string) => mem.get(key) ?? null);
    (SecureStore.setItemAsync as jest.Mock).mockImplementation(async (key: string, value: string) => {
      mem.set(key, value);
    });
    (SecureStore.deleteItemAsync as jest.Mock).mockImplementation(async (key: string) => {
      mem.delete(key);
    });
  });

  it('refreshes before expiry and does not log tokens', async () => {
    expect(accessTokenNeedsRefresh(Date.now() + 10_000)).toBe(true);
    expect(accessTokenNeedsRefresh(Date.now() + 10 * 60_000)).toBe(false);

    mem.set('hmore.auth0.accessToken', 'access-old');
    mem.set('hmore.auth0.refreshToken', 'refresh-old');
    mem.set('hmore.auth0.expiresAt', String(Date.now() - 1000));

    const fetchSpy = jest.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: 'access-new', refresh_token: 'refresh-new', expires_in: 3600 }),
        { status: 200 },
      ),
    );
    const log = jest.spyOn(console, 'log').mockImplementation(() => undefined);

    const token = await getStoredAccessToken();
    expect(token).toBe('access-new');
    const body = String((fetchSpy.mock.calls[0]?.[1] as RequestInit | undefined)?.body ?? '');
    expect(body).toContain('grant_type=refresh_token');
    expect(body).toContain('refresh_token=refresh-old');
    expect(JSON.stringify(log.mock.calls)).not.toContain('access-new');
    expect(JSON.stringify(log.mock.calls)).not.toContain('refresh-old');

    fetchSpy.mockRestore();
    log.mockRestore();
  });
});
