import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getBiometricAvailability, isBiometricUnlockEnabled, setBiometricUnlockEnabled } from '@/lib/hmore/security/biometrics';
import {
  listDeviceSessions,
  reportDeviceSessionLost,
  revokeDeviceSession,
  type DeviceSessionRecord,
} from '@/lib/hmore/security/deviceSession';
import { readDeviceSessionId } from '@/lib/hmore/security/deviceSessionStore';

const SESSIONS_KEY = ['hmore', 'device-sessions'] as const;

function statusLabel(status: DeviceSessionRecord['status']): string {
  if (status === 'active') return 'Active';
  if (status === 'lost') return 'Reported lost';
  return 'Signed out';
}

export function DeviceSecurityPanel({ onSignedOut }: { onSignedOut?: () => void }) {
  const { hmore, signOut } = useAuth();
  const client = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const biometric = useQuery({ queryKey: ['hmore', 'biometric-unlock'], queryFn: isBiometricUnlockEnabled });
  const availability = useQuery({ queryKey: ['hmore', 'biometric-availability'], queryFn: getBiometricAvailability });
  const localSession = useQuery({
    queryKey: ['hmore', 'device-session', 'local'],
    queryFn: readDeviceSessionId,
    enabled: !!hmore,
  });
  const sessions = useQuery({ queryKey: SESSIONS_KEY, queryFn: listDeviceSessions, enabled: !!hmore });
  const enabled = biometric.data === true;
  const canEnable = availability.data?.enrolled === true;

  async function toggleBiometric() {
    setError(null);
    setMessage(null);
    const saved = await setBiometricUnlockEnabled(!enabled);
    if (!saved && !enabled) {
      setError('The device did not confirm fingerprint or face unlock. The preference was left off.');
    }
    await client.invalidateQueries({ queryKey: ['hmore', 'biometric-unlock'] });
  }

  async function refresh() {
    await client.invalidateQueries({ queryKey: SESSIONS_KEY });
    await client.invalidateQueries({ queryKey: ['hmore', 'device-session', 'local'] });
  }

  async function endThisDevice() {
    setPendingId('sign-out');
    setError(null);
    try {
      await signOut();
      onSignedOut?.();
    } catch (err) {
      setError(hmoreErrorMessage(err, 'Could not sign out this device.'));
    } finally {
      setPendingId(null);
    }
  }

  async function revoke(item: DeviceSessionRecord) {
    if (item.id === localSession.data) {
      await endThisDevice();
      return;
    }
    setPendingId(item.id);
    setError(null);
    try {
      await revokeDeviceSession(item.id);
      setMessage('That device was signed out. It will be blocked the next time it calls HMore.');
      await refresh();
    } catch (err) {
      setError(hmoreErrorMessage(err, 'Could not sign out that device.'));
    } finally {
      setPendingId(null);
    }
  }

  async function reportLost(item: DeviceSessionRecord) {
    setPendingId(item.id);
    setError(null);
    try {
      await reportDeviceSessionLost(item.id);
      if (item.id === localSession.data) {
        await signOut();
        onSignedOut?.();
        return;
      }
      setMessage('That device was reported lost and can no longer use this installation.');
      await refresh();
    } catch (err) {
      setError(hmoreErrorMessage(err, 'Could not report that device lost.'));
    } finally {
      setPendingId(null);
    }
  }

  return (
    <View>
      <Card style={styles.card}>
        <Text style={styles.title}>Fingerprint and face unlock</Text>
        <Text style={styles.detail}>
          This only unlocks a session that is already signed in on this phone. It does not replace your organisation login. Fingerprint and
          face data stay on the device. HMore does not receive or store them.
        </Text>
        <Text style={styles.detail}>A development build is required to try this on a phone. CI does not run a real biometric prompt.</Text>
        <Pressable
          accessibilityRole="switch"
          accessibilityLabel="Use fingerprint or face to unlock this device"
          accessibilityState={{ checked: enabled, disabled: biometric.isLoading || (!enabled && !canEnable) }}
          disabled={biometric.isLoading || (!enabled && !canEnable)}
          onPress={() => void toggleBiometric()}
          style={styles.row}
        >
          <Text style={styles.state}>{biometric.isLoading ? 'Checking' : enabled ? 'On' : 'Off'}</Text>
        </Pressable>
        {availability.data?.reason === 'not_enrolled' ? (
          <Text style={styles.detail}>Set up fingerprint or face unlock in the device settings before turning this on.</Text>
        ) : null}
        {availability.data?.reason === 'unsupported' || availability.data?.reason === 'unavailable' ? (
          <Text style={styles.detail}>This install cannot show a biometric prompt. Use an iOS or Android development build on a device.</Text>
        ) : null}
      </Card>

      <Card style={styles.card}>
        <Text style={styles.title}>Devices</Text>
        {hmore ? (
          <Text style={styles.detail}>
            Signing out a device blocks that installation. The phone must sign in again and register a new installation id. Offline drafts
            already on the phone stay there until the same account signs in.
          </Text>
        ) : (
          <Text style={styles.detail}>Device sign-out is available after you sign in with your organisation account.</Text>
        )}
        {hmore && sessions.isLoading ? <Text style={styles.detail}>Loading devices…</Text> : null}
        {hmore && sessions.isError ? <Text style={styles.error}>{hmoreErrorMessage(sessions.error, 'Could not load devices.')}</Text> : null}
        {(sessions.data ?? []).map((item) => {
          const current = item.id === localSession.data || item.is_current === true;
          return (
            <View key={item.id} style={styles.device}>
              <Text style={styles.deviceName}>{item.device_name || item.platform}</Text>
              <Text style={styles.detail}>
                {statusLabel(item.status)}
                {item.app_version ? ` · ${item.app_version}` : ''}
                {current ? ' · This device' : ''}
              </Text>
              {item.status === 'active' ? (
                <View style={styles.actions}>
                  <Button
                    title={current ? 'Sign out this device' : 'Sign out device'}
                    variant="outline"
                    size="sm"
                    onPress={() => void revoke(item)}
                    loading={pendingId === item.id || (current && pendingId === 'sign-out')}
                  />
                  <Button
                    title="Report lost"
                    variant="ghost"
                    size="sm"
                    onPress={() => void reportLost(item)}
                    loading={pendingId === item.id}
                  />
                </View>
              ) : null}
            </View>
          );
        })}
        {hmore && !sessions.isLoading && (sessions.data ?? []).length === 0 ? (
          <Text style={styles.detail}>No device session is registered yet. It appears after organisation sign-in on a phone.</Text>
        ) : null}
        {message ? <Text style={styles.saved}>{message}</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  card: { marginBottom: theme.spacing.md },
  title: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text },
  detail: { fontFamily: FONT_MEDIUM, fontSize: 13, lineHeight: 18, color: theme.colors.textSecondary, marginTop: 4 },
  row: { marginTop: theme.spacing.sm, alignSelf: 'flex-start' },
  state: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 14 },
  device: { marginTop: theme.spacing.md, paddingTop: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.border },
  deviceName: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text },
  actions: { marginTop: theme.spacing.sm, gap: theme.spacing.sm },
  saved: { fontFamily: FONT_MEDIUM, color: theme.colors.success, marginTop: theme.spacing.sm },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.error, marginTop: theme.spacing.sm },
});
