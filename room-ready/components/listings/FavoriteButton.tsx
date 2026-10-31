import { Pressable, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';

import { theme } from '@/constants/theme';
import { ListingItem } from '@/lib/api';

interface FavoriteButtonProps {
  listing: ListingItem;
  active: boolean;
  onToggle: (listing: ListingItem) => void;
  size?: number;
}

export function FavoriteButton({ listing, active, onToggle, size = 22 }: FavoriteButtonProps) {
  return (
    <Pressable
      onPress={() => onToggle(listing)}
      hitSlop={10}
      style={({ pressed }) => [styles.btn, pressed && styles.pressed]}
      accessibilityLabel={active ? 'Remove from wishlist' : 'Save to wishlist'}
    >
      <Ionicons
        name={active ? 'heart' : 'heart-outline'}
        size={size}
        color={active ? theme.colors.error : theme.colors.textMuted}
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: { padding: 4 },
  pressed: { opacity: 0.7 },
});
