import { Platform, Pressable, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

import { webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface CardProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
  elevated?: boolean;
  variant?: 'default' | 'outlined' | 'filled' | 'glass';
  padded?: boolean;
}

export function Card({
  children,
  style,
  onPress,
  elevated = true,
  variant = 'default',
  padded = true,
}: CardProps) {
  const shadow = elevated
    ? Platform.OS === 'web'
      ? webShadow('sm')
      : theme.shadows.sm
    : undefined;

  const content = (
    <View
      style={[
        styles.card,
        !padded && styles.unpadded,
        variant === 'filled' && styles.filled,
        variant === 'outlined' && styles.outlined,
        shadow,
        style,
      ]}
    >
      {children}
    </View>
  );

  if (onPress) {
    return (
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.pressable, pressed && styles.pressed]}
      >
        {content}
      </Pressable>
    );
  }

  return content;
}

const styles = StyleSheet.create({
  pressable: { width: '100%' },
  card: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    padding: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  unpadded: { padding: 0 },
  filled: {
    backgroundColor: theme.colors.surfaceSecondary,
    borderColor: theme.colors.borderLight,
  },
  outlined: {
    backgroundColor: theme.colors.surface,
    borderColor: theme.colors.border,
    borderWidth: 1.5,
  },
  pressed: { opacity: 0.94, transform: [{ scale: 0.995 }] },
});
