import { router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface PropertyActionBarProps {
  propertyId: string;
  listableRoomId?: string | null;
}

const ACTIONS = [
  { label: 'Add room', icon: 'bed-outline' as const, route: '/(app)/property/add-room' },
  { label: 'Upload doc', icon: 'document-outline' as const, route: '/(app)/property/upload-document' },
  { label: 'Message', icon: 'chatbubble-outline' as const, route: '/(app)/conversation/new' },
  { label: 'Checks', icon: 'shield-checkmark-outline' as const, route: '/(app)/(tabs)/compliance' },
] as const;

export function PropertyActionBar({ propertyId, listableRoomId }: PropertyActionBarProps) {
  const actions = listableRoomId
    ? [
        {
          label: 'Create listing',
          icon: 'megaphone-outline' as const,
          route: '/(app)/listing/new',
          params: { roomId: listableRoomId, propertyId },
        },
        ...ACTIONS,
      ]
    : [...ACTIONS];

  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      {actions.map((action) => (
        <Pressable
          key={action.label}
          style={({ pressed }) => [styles.chip, pressed && styles.chipPressed]}
          onPress={() =>
            router.push({
              pathname: action.route,
              params: 'params' in action ? action.params : { propertyId },
            } as never)
          }
        >
          <View style={styles.iconWrap}>
            <Ionicons name={action.icon} size={18} color={theme.colors.secondary} />
          </View>
          <Text style={styles.label}>{action.label}</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    gap: theme.spacing.sm,
    paddingVertical: theme.spacing.sm,
    marginBottom: theme.spacing.sm,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.full,
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  chipPressed: { opacity: 0.88, backgroundColor: theme.colors.surfaceSecondary },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: theme.radius.sm,
    backgroundColor: theme.colors.accentLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  label: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    paddingRight: 4,
  },
});
