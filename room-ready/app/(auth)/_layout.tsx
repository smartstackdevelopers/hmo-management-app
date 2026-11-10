import { Redirect, Stack } from 'expo-router';
import { View } from 'react-native';

import { DeviceSessionRevokedNotice } from '@/components/security/DeviceSessionRevokedNotice';
import { LoadingScreen } from '@/components/ui/States';
import { useAuth } from '@/contexts/AuthContext';

export default function AuthLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingScreen message="Checking your session..." />;

  if (isAuthenticated) {
    return <Redirect href="/(app)/(tabs)" />;
  }

  return (
    <View style={{ flex: 1 }}>
      <DeviceSessionRevokedNotice />
      <Stack screenOptions={{ headerShown: false, animation: 'fade' }}>
        <Stack.Screen name="welcome" />
        <Stack.Screen name="login" />
        <Stack.Screen name="register" />
        <Stack.Screen name="forgot-password" />
      </Stack>
    </View>
  );
}
