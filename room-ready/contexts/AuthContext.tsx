import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { queryClient } from '@/contexts/QueryProvider';
import { api, AuthResponse, clearToken, loadToken, saveToken } from '@/lib/api';
import { clearRequestContext, loadRequestContext } from '@/lib/hmore/requestContext';
import { loadHmoreSession, type HmoreSession } from '@/lib/hmore/services/session';
import {
  clearAuth0Tokens,
  getStoredAccessToken,
  isAuth0MobileConfigured,
  loginWithAuth0,
  logoutAuth0,
} from '@/lib/hmoreAuth0';
import { deactivateRegisteredPush, registerPushAfterSession } from '@/lib/hmore/push/register';
import { registerCurrentDeviceSession, revokeCurrentDeviceSession } from '@/lib/hmore/security/deviceSession';
import { endLocalSession, subscribeLocalSessionEnded } from '@/lib/hmore/security/deviceSessionRevoke';
import { mapHmoreRole } from '@/lib/hmore/roles';
import { AuthState, User } from '@/types';

interface RegisterData {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  role: User['role'];
  phone?: string;
}

interface AuthContextValue extends AuthState {
  /** Auth0 + FastAPI when configured; local password API only when Auth0 env is unset. */
  authMode: 'auth0' | 'legacy';
  hmore: HmoreSession | null;
  signIn: (email: string, password: string) => Promise<void>;
  signInWithAuth0: () => Promise<void>;
  signUp: (data: RegisterData) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const AUTH0_ONLY = 'Sign in with your organisation account.';

export function userFromHmoreSession(session: HmoreSession): User {
  const name = session.auth.display_name?.trim() || session.auth.email || 'Account';
  const parts = name.split(/\s+/).filter(Boolean);
  return {
    id: session.auth.id,
    email: session.auth.email ?? '',
    firstName: parts[0] || 'Account',
    lastName: parts.slice(1).join(' '),
    role: mapHmoreRole(session.rbac.active_role),
    verified: true,
    active: true,
    createdAt: new Date(0).toISOString(),
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const authMode = isAuth0MobileConfigured() ? 'auth0' : 'legacy';
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });
  const [hmore, setHmore] = useState<HmoreSession | null>(null);

  const applyHmore = useCallback((session: HmoreSession) => {
    setHmore(session);
    setState({ user: userFromHmoreSession(session), isLoading: false, isAuthenticated: true });
  }, []);

  const bootstrap = useCallback(async () => {
    if (isAuth0MobileConfigured()) {
      try {
        await loadRequestContext();
        const token = await getStoredAccessToken();
        if (!token) {
          setHmore(null);
          setState({ user: null, isLoading: false, isAuthenticated: false });
          return;
        }
        applyHmore(await loadHmoreSession());
      } catch {
        await clearAuth0Tokens();
        await clearRequestContext();
        setHmore(null);
        setState({ user: null, isLoading: false, isAuthenticated: false });
      }
      return;
    }

    try {
      const token = await loadToken();
      if (!token) {
        setState({ user: null, isLoading: false, isAuthenticated: false });
        return;
      }
      const { user } = await api.get<{ user: User }>('/auth/me');
      setHmore(null);
      setState({ user, isLoading: false, isAuthenticated: true });
    } catch {
      await clearToken();
      setState({ user: null, isLoading: false, isAuthenticated: false });
    }
  }, [applyHmore]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    return subscribeLocalSessionEnded(() => {
      queryClient.clear();
      setHmore(null);
      setState({ user: null, isLoading: false, isAuthenticated: false });
    });
  }, []);

  useEffect(() => {
    if (!state.isAuthenticated || !hmore) return;
    let cancelled = false;
    void registerCurrentDeviceSession()
      .then(() => {
        void queryClient.invalidateQueries({ queryKey: ['hmore', 'device-sessions'] });
        void queryClient.invalidateQueries({ queryKey: ['hmore', 'device-session', 'local'] });
      })
      .catch(() => {
        if (cancelled) return;
      });
    return () => {
      cancelled = true;
    };
  }, [state.isAuthenticated, hmore]);

  useEffect(() => {
    if (!state.isAuthenticated || !hmore) return;
    void registerPushAfterSession();
  }, [state.isAuthenticated, hmore]);

  const signInWithAuth0 = useCallback(async () => {
    if (!isAuth0MobileConfigured()) {
      throw new Error('Organisation sign-in is not configured.');
    }
    await loginWithAuth0();
    await clearToken();
    applyHmore(await loadHmoreSession());
  }, [applyHmore]);

  const signIn = useCallback(async (email: string, password: string) => {
    if (isAuth0MobileConfigured()) {
      throw new Error(AUTH0_ONLY);
    }
    const { user, token } = await api.post<AuthResponse>('/auth/login', { email, password });
    await saveToken(token);
    setHmore(null);
    setState({ user, isLoading: false, isAuthenticated: true });
  }, []);

  const signUp = useCallback(async (data: RegisterData) => {
    if (isAuth0MobileConfigured()) {
      throw new Error(AUTH0_ONLY);
    }
    const { user, token } = await api.post<AuthResponse>('/auth/register', data);
    await saveToken(token);
    setHmore(null);
    setState({ user, isLoading: false, isAuthenticated: true });
  }, []);

  const signOut = useCallback(async () => {
    try {
      await revokeCurrentDeviceSession();
    } catch {
      // The device row may already be revoked, or the phone may be offline.
    }
    try {
      await deactivateRegisteredPush();
    } catch {
      // Local sign-out continues when the device row cannot be reached.
    }
    await endLocalSession();
    queryClient.clear();
    if (isAuth0MobileConfigured()) {
      await logoutAuth0();
    }
    await AsyncStorage.removeItem('@roomready_auth');
    setHmore(null);
    setState({ user: null, isLoading: false, isAuthenticated: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, authMode, hmore, signIn, signInWithAuth0, signUp, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
