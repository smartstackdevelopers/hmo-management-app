import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AppState, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { authenticateAsync, grantUnlock, isBiometricUnlockEnabled } from '@/lib/hmore/security/biometrics';
import { setBiometricLocked } from '@/lib/hmore/security/accessGate';

/**
 * Covers the signed-in app when it leaves the foreground.
 * If biometric unlock is enabled, the cover stays until the OS prompt succeeds.
 * The preference flag alone never unlocks the app.
 */
export function BiometricLockGate({ children }: { children: ReactNode }) {
  const { isAuthenticated, authMode, signOut, signInWithAuth0 } = useAuth();
  const [ready, setReady] = useState(false);
  const [locked, setLocked] = useState(false);
  const [covered, setCovered] = useState(false);
  const [busy, setBusy] = useState(false);
  const enabledRef = useRef(false);
  const lockedRef = useRef(false);
  const prompting = useRef(false);

  function lock() {
    lockedRef.current = true;
    setLocked(true);
    setBiometricLocked(true);
  }

  function unlock() {
    lockedRef.current = false;
    setLocked(false);
    setBiometricLocked(false);
  }

  async function prompt() {
    if (!enabledRef.current || prompting.current) return;
    prompting.current = true;
    setBusy(true);
    try {
      const success = await authenticateAsync();
      if (grantUnlock(success)) unlock();
    } finally {
      prompting.current = false;
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!isAuthenticated) {
      enabledRef.current = false;
      unlock();
      setReady(true);
      setCovered(false);
      return;
    }
    let cancelled = false;
    setReady(false);
    void (async () => {
      const enabled = await isBiometricUnlockEnabled();
      if (cancelled) return;
      enabledRef.current = enabled;
      if (enabled) {
        lock();
        setReady(true);
        await prompt();
      } else {
        unlock();
        setReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    const subscription = AppState.addEventListener('change', (next) => {
      if (next === 'active') {
        setCovered(false);
        if (lockedRef.current && enabledRef.current) void prompt();
        return;
      }
      setCovered(true);
      if (enabledRef.current && isAuthenticated) lock();
    });
    return () => subscription.remove();
  }, [isAuthenticated]);

  async function signInAgain() {
    await signOut();
    if (authMode === 'auth0') {
      try {
        await signInWithAuth0();
      } catch {
        // Cancelled organisation login leaves the welcome screen in place.
      }
    }
  }

  const blocked = isAuthenticated && (!ready || covered || locked);
  const showUnlock = isAuthenticated && ready && locked && !covered;

  return (
    <View style={styles.root}>
      <View
        style={styles.root}
        accessibilityElementsHidden={blocked}
        importantForAccessibility={blocked ? 'no-hide-descendants' : 'auto'}
      >
        {children}
      </View>
      {blocked ? (
        <View style={[StyleSheet.absoluteFill, styles.cover]} accessibilityViewIsModal>
          {showUnlock ? (
            <View style={styles.panel}>
              <Text style={styles.title}>Unlock HMore</Text>
              <Text style={styles.detail}>
                Confirm fingerprint or face to open the session already on this device. This is not a new login.
              </Text>
              <Button title="Try again" onPress={() => void prompt()} loading={busy} fullWidth />
              <Button title="Sign in with organisation account" variant="outline" onPress={() => void signInAgain()} fullWidth />
            </View>
          ) : null}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  cover: {
    backgroundColor: theme.colors.background,
    justifyContent: 'center',
    padding: theme.spacing.lg,
  },
  panel: { gap: theme.spacing.md },
  title: { fontFamily: FONT_SEMIBOLD, fontSize: 22, color: theme.colors.text },
  detail: { fontFamily: FONT_MEDIUM, fontSize: 15, lineHeight: 22, color: theme.colors.textSecondary },
});
