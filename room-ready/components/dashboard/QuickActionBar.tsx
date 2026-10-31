import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { theme } from '@/constants/theme';
import { UserRole } from '@/types';

interface QuickAction {
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  route: string;
}

const ACTIONS: Record<UserRole, QuickAction[]> = {
  landlord: [
    { label: 'Add property', icon: 'add-circle-outline', route: '/(app)/property/new' },
    { label: 'My files', icon: 'folder-outline', route: '/(app)/documents' },
    { label: 'List room', icon: 'bed-outline', route: '/(app)/(tabs)/listings' },
  ],
  tenant: [
    { label: 'Find room', icon: 'search-outline', route: '/(app)/browse' },
    { label: 'Report issue', icon: 'construct-outline', route: '/(app)/maintenance/new' },
    { label: 'Messages', icon: 'chatbubble-outline', route: '/(app)/(tabs)/messages' },
  ],
  property_manager: [
    { label: 'Properties', icon: 'business-outline', route: '/(app)/(tabs)/properties' },
    { label: 'Inspect', icon: 'clipboard-outline', route: '/(app)/inspection/new' },
    { label: 'Repairs', icon: 'construct-outline', route: '/(app)/(tabs)/maintenance' },
  ],
  contractor: [
    { label: 'Jobs', icon: 'briefcase-outline', route: '/(app)/(tabs)/schedule' },
    { label: 'Messages', icon: 'chatbubbles-outline', route: '/(app)/(tabs)/messages' },
    { label: 'Files', icon: 'folder-outline', route: '/(app)/documents' },
  ],
  admin: [
    { label: 'Users', icon: 'people-outline', route: '/(app)/(tabs)/users' },
    { label: 'Listings', icon: 'list-outline', route: '/(app)/(tabs)/listings' },
    { label: 'Alerts', icon: 'notifications-outline', route: '/(app)/notifications' },
  ],
};

export function QuickActionBar({ role }: { role: UserRole }) {
  const actions = ACTIONS[role];

  return (
    <View style={styles.wrap}>
      <View style={styles.row}>
        {actions.map((action) => (
          <Pressable
            key={action.label}
            style={({ pressed }) => [styles.tile, pressed && styles.pressed]}
            onPress={() => router.push(action.route as never)}
          >
            <View style={styles.icon}>
              <Ionicons name={action.icon} size={22} color={theme.colors.secondary} />
            </View>
            <Text style={styles.label} numberOfLines={2}>{action.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { marginBottom: theme.spacing.md, paddingTop: theme.spacing.xs },
  row: { flexDirection: 'row', gap: theme.spacing.sm },
  tile: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 14,
    paddingHorizontal: 6,
    backgroundColor: theme.colors.surfaceSecondary,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
    gap: 8,
  },
  pressed: { backgroundColor: theme.colors.surfaceMuted },
  icon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: 12,
    fontWeight: '600',
    color: theme.colors.text,
    textAlign: 'center',
    lineHeight: 15,
  },
});
