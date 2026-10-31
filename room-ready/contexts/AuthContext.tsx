import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { api, AuthResponse, clearToken, loadToken, saveToken } from '@/lib/api';
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
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (data: RegisterData) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  const bootstrap = useCallback(async () => {
    try {
      const token = await loadToken();
      if (!token) {
        setState({ user: null, isLoading: false, isAuthenticated: false });
        return;
      }
      const { user } = await api.get<{ user: User }>('/auth/me');
      setState({ user, isLoading: false, isAuthenticated: true });
    } catch {
      await clearToken();
      setState({ user: null, isLoading: false, isAuthenticated: false });
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const signIn = useCallback(async (email: string, password: string) => {
    const { user, token } = await api.post<AuthResponse>('/auth/login', { email, password });
    await saveToken(token);
    setState({ user, isLoading: false, isAuthenticated: true });
  }, []);

  const signUp = useCallback(async (data: RegisterData) => {
    const { user, token } = await api.post<AuthResponse>('/auth/register', data);
    await saveToken(token);
    setState({ user, isLoading: false, isAuthenticated: true });
  }, []);

  const signOut = useCallback(async () => {
    await clearToken();
    await AsyncStorage.removeItem('@roomready_auth');
    setState({ user: null, isLoading: false, isAuthenticated: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, signIn, signUp, signOut }}>
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
