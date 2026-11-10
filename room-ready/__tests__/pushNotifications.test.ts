import { handlePushOpen, parsePushData, pushOpenHref } from '@/lib/hmore/push/links';
import { PUSH_PERMISSION_RATIONALE, registerDevicePush, resolveEasProjectId } from '@/lib/hmore/push/registerCore';

const INCIDENT = '11111111-1111-4111-8111-111111111111';
const REPAIR = '22222222-2222-4222-8222-222222222222';
const MESSAGE = '33333333-3333-4333-8333-333333333333';
const PROJECT = '44444444-4444-4444-8444-444444444444';

describe('push deep links', () => {
  it('parses routing ids and drops narrative fields', () => {
    const parsed = parsePushData({
      message_id: MESSAGE,
      related_resource_type: 'incident',
      related_resource_id: INCIDENT,
      body: 'Patient fracture narrative',
    });
    expect(parsed).toEqual({
      message_id: MESSAGE,
      related_resource_type: 'incident',
      related_resource_id: INCIDENT,
    });
    expect(JSON.stringify(parsed)).not.toContain('fracture');
  });

  it('opens the same staff record as the in-app alert list', () => {
    expect(pushOpenHref({ related_resource_type: 'incident', related_resource_id: INCIDENT }, true)).toBe(
      `/(app)/staff/incident/${INCIDENT}`,
    );
    expect(pushOpenHref({ related_resource_type: 'daily_log' }, true)).toBe('/(app)/(tabs)/notes');
  });

  it('opens a tenant repair and otherwise the notifications inbox', () => {
    expect(pushOpenHref({ related_resource_type: 'maintenance_request', related_resource_id: REPAIR }, false)).toBe(
      `/(app)/maintenance/${REPAIR}`,
    );
    expect(pushOpenHref({ related_resource_type: 'incident', related_resource_id: INCIDENT }, false)).toBe('/(app)/notifications');
  });

  it('marks the message read when a message id is present', async () => {
    const markRead = jest.fn().mockResolvedValue(undefined);
    const navigate = jest.fn();
    await handlePushOpen(
      { message_id: MESSAGE, related_resource_type: 'incident', related_resource_id: INCIDENT },
      true,
      { navigate, markRead },
    );
    expect(navigate).toHaveBeenCalledWith(`/(app)/staff/incident/${INCIDENT}`);
    expect(markRead).toHaveBeenCalledWith(MESSAGE);
  });
});

describe('push registration', () => {
  it('skips registration without permission', async () => {
    const getToken = jest.fn();
    const registerApi = jest.fn();
    const result = await registerDevicePush({
      getPermission: async () => ({ granted: false }),
      requestPermission: async () => ({ granted: false }),
      getToken,
      projectId: PROJECT,
      platform: 'android',
      registerApi,
      storeDeviceId: async () => undefined,
    });
    expect(result).toEqual({ registered: false, reason: 'permission_denied' });
    expect(getToken).not.toHaveBeenCalled();
    expect(registerApi).not.toHaveBeenCalled();
    expect(PUSH_PERMISSION_RATIONALE.length).toBeGreaterThan(20);
  });

  it('rejects a placeholder EAS project id', () => {
    expect(resolveEasProjectId({ envProjectId: '', easConfigProjectId: 'room-ready-hmo' })).toBeNull();
    expect(resolveEasProjectId({ envProjectId: PROJECT, easConfigProjectId: 'room-ready-hmo' })).toBe(PROJECT);
  });
});
