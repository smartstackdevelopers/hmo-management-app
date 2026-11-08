import { Redirect, Stack } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';

const headerOptions = {
  headerStyle: { backgroundColor: theme.colors.background },
  headerTintColor: theme.colors.text,
  headerTitleStyle: { fontWeight: '700' as const, fontSize: 17, letterSpacing: -0.3 },
  headerShadowVisible: false,
  headerBackTitle: 'Back',
  contentStyle: { backgroundColor: theme.colors.background, flex: 1 },
};

export default function AppLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return <LoadingScreen message="Loading your account..." />;

  if (!isAuthenticated) {
    return <Redirect href="/(auth)/welcome" />;
  }

  return (
    <View style={styles.root}>
      <Stack screenOptions={{ headerShown: false, contentStyle: { flex: 1, backgroundColor: theme.colors.background } }}>
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="property/[id]" options={{ ...headerOptions, headerShown: true, title: 'Property Details' }} />
        <Stack.Screen name="property/new" options={{ ...headerOptions, headerShown: true, title: 'Add Property' }} />
        <Stack.Screen name="property/add-room" options={{ ...headerOptions, headerShown: true, title: 'Add Room' }} />
        <Stack.Screen name="property/upload-document" options={{ ...headerOptions, headerShown: true, title: 'Upload Document' }} />
        <Stack.Screen name="maintenance/[id]" options={{ ...headerOptions, headerShown: true, title: 'Repair Details' }} />
        <Stack.Screen name="maintenance/new" options={{ ...headerOptions, headerShown: true, title: 'Report Repair' }} />
        <Stack.Screen name="conversation/[id]" options={{ ...headerOptions, headerShown: true, title: 'Conversation' }} />
        <Stack.Screen name="conversation/new" options={{ ...headerOptions, headerShown: true, title: 'New Message' }} />
        <Stack.Screen name="listing/[id]" options={{ ...headerOptions, headerShown: true, title: 'Room Listing' }} />
        <Stack.Screen name="listing/new" options={{ ...headerOptions, headerShown: true, title: 'Create Listing' }} />
        <Stack.Screen name="inspection/[id]" options={{ ...headerOptions, headerShown: true, title: 'Inspection' }} />
        <Stack.Screen name="inspection/new" options={{ ...headerOptions, headerShown: true, title: 'Schedule Inspection' }} />
        <Stack.Screen name="documents" options={{ ...headerOptions, headerShown: true, title: 'My files' }} />
        <Stack.Screen name="notifications" options={{ ...headerOptions, headerShown: true, title: 'Notifications' }} />
        <Stack.Screen name="community" options={{ ...headerOptions, headerShown: true, title: 'Local services' }} />
        <Stack.Screen name="jobs" options={{ ...headerOptions, headerShown: true, title: 'Jobs and training' }} />
        <Stack.Screen name="assistant" options={{ ...headerOptions, headerShown: true, title: 'Assistant' }} />
        <Stack.Screen name="accessibility" options={{ ...headerOptions, headerShown: true, title: 'Accessibility' }} />
        <Stack.Screen name="security" options={{ ...headerOptions, headerShown: true, title: 'Privacy & Security' }} />
        <Stack.Screen name="browse" options={{ ...headerOptions, headerShown: true, title: 'Find a Room' }} />
        <Stack.Screen name="wishlist" options={{ ...headerOptions, headerShown: true, title: 'Wishlist' }} />
      </Stack>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: theme.colors.background },
});
