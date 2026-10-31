import { Redirect } from 'expo-router';
import { ReactNode } from 'react';

import { LoadingScreen } from '@/components/ui/States';
import { roleHasAccess } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { UserRole } from '@/types';

export function useRoleGuard(allowed: UserRole[]): ReactNode | null {
  const { user, isLoading } = useAuth();

  if (isLoading) return <LoadingScreen />;
  if (!user?.role) return <Redirect href="/(auth)/welcome" />;
  if (!roleHasAccess(user.role, allowed)) return <Redirect href="/(app)/(tabs)" />;

  return null;
}
