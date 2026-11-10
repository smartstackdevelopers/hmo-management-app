export const PUSH_PERMISSION_RATIONALE =
  'Room Ready uses notifications to tell you when a message is waiting. The notification does not include case notes or medical details.';

const PROJECT_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export type PushPlatform = 'ios' | 'android' | 'web';

export function resolveEasProjectId(input: {
  envProjectId?: string | null;
  easConfigProjectId?: string | null;
}): string | null {
  const candidates = [input.envProjectId, input.easConfigProjectId];
  for (const candidate of candidates) {
    const value = candidate?.trim();
    if (value && PROJECT_UUID.test(value)) return value;
  }
  return null;
}

export interface PushRegisterDeps {
  getPermission: () => Promise<{ granted: boolean }>;
  requestPermission: () => Promise<{ granted: boolean }>;
  getToken: (projectId: string) => Promise<string>;
  projectId: string | null;
  platform: PushPlatform;
  deviceName?: string | null;
  appVersion?: string | null;
  registerApi: (body: {
    expo_push_token: string;
    platform: PushPlatform;
    device_name?: string | null;
    app_version?: string | null;
  }) => Promise<{ id: string }>;
  storeDeviceId: (id: string) => Promise<void>;
}

export async function registerDevicePush(deps: PushRegisterDeps): Promise<{ registered: boolean; reason?: string }> {
  const current = await deps.getPermission();
  const permission = current.granted ? current : await deps.requestPermission();
  if (!permission.granted) {
    return { registered: false, reason: 'permission_denied' };
  }
  if (!deps.projectId) {
    return { registered: false, reason: 'missing_project_id' };
  }
  const token = await deps.getToken(deps.projectId);
  const row = await deps.registerApi({
    expo_push_token: token,
    platform: deps.platform,
    device_name: deps.deviceName ?? null,
    app_version: deps.appVersion ?? null,
  });
  await deps.storeDeviceId(row.id);
  return { registered: true };
}
