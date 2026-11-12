import fs from 'fs';
import path from 'path';

import { STAFF_RELEASE_FEATURES, TENANT_RELEASE_FEATURES } from '@/lib/hmore/release/featureVerification';
import { validateProductionApiUrl } from '@/lib/hmore/release/productionApi';

const ROOT = path.join(__dirname, '..');

function readJson(rel: string): Record<string, unknown> {
  return JSON.parse(fs.readFileSync(path.join(ROOT, rel), 'utf8')) as Record<string, unknown>;
}

describe('F7.7 release readiness', () => {
  it('rejects dev API URLs for production', () => {
    expect(validateProductionApiUrl(null)).toMatch(/required/i);
    expect(validateProductionApiUrl('http://localhost:8000/api/v1')).toMatch(/HTTPS/i);
    expect(validateProductionApiUrl('https://api.hmore.example.uk/api/v1')).toBeNull();
  });

  it('uses Android App Bundle for production EAS profile', () => {
    const eas = readJson('eas.json') as { build: { production: { android: { buildType: string } } } };
    expect(eas.build.production.android.buildType).toBe('app-bundle');
  });

  it('keeps stable iOS and Android application identifiers', () => {
    const app = readJson('app.json') as {
      expo: { ios: { bundleIdentifier: string }; android: { package: string } };
    };
    expect(app.expo.ios.bundleIdentifier).toBe('com.roomready.app');
    expect(app.expo.android.package).toBe('com.roomready.app');
  });

  it('documents tenant and staff feature routes', () => {
    expect(TENANT_RELEASE_FEATURES.length).toBeGreaterThanOrEqual(8);
    expect(STAFF_RELEASE_FEATURES.length).toBeGreaterThanOrEqual(8);
    for (const row of TENANT_RELEASE_FEATURES) {
      expect(row.routes.length).toBeGreaterThan(0);
    }
  });

  it('does not commit Play service account key path as a real file', () => {
    const example = path.join(ROOT, 'store', 'eas.submit.json.example');
    expect(fs.existsSync(example)).toBe(true);
    expect(fs.existsSync(path.join(ROOT, 'google-play-service-account.json'))).toBe(false);
  });
});
