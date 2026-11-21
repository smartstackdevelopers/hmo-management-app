import { Ionicons } from '@expo/vector-icons';
import { ActivityIndicator, Platform, Pressable, StyleProp, StyleSheet, Text, View, ViewStyle } from 'react-native';

import { FONT_SEMIBOLD, webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'outlineLight' | 'ghost' | 'accent' | 'soft' | 'danger' | 'white';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
  icon?: keyof typeof Ionicons.glyphMap;
  iconPosition?: 'left' | 'right';
}

const textColor: Record<ButtonVariant, string> = {
  primary: theme.colors.textInverse,
  secondary: theme.colors.textInverse,
  accent: theme.colors.textInverse,
  danger: theme.colors.textInverse,
  outline: theme.colors.secondaryDark,
  outlineLight: theme.colors.text,
  ghost: theme.colors.secondaryDark,
  soft: theme.colors.secondaryDark,
  white: theme.colors.secondaryDark,
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  style,
  accessibilityLabel,
  icon,
  iconPosition = 'left',
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const color = textColor[variant];
  const filled = variant === 'primary' || variant === 'secondary' || variant === 'accent';
  const iconNode = icon ? <Ionicons name={icon} size={size === 'sm' ? 15 : 18} color={color} /> : null;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      onPress={onPress ?? (() => {})}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        styles[`size_${size}`],
        fullWidth && styles.fullWidth,
        filled ? (Platform.OS === 'web' ? webShadow('sm') : theme.shadows.sm) : undefined,
        pressed && !isDisabled && styles.pressed,
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={color} size="small" />
      ) : (
        <View style={styles.inner}>
          {iconPosition === 'left' && iconNode}
          <Text style={[styles.text, { color }, styles[`textSize_${size}`]]} numberOfLines={1}>
            {title}
          </Text>
          {iconPosition === 'right' && iconNode}
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: theme.radius.md,
  },
  inner: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8 },
  fullWidth: { width: '100%' },
  pressed: { opacity: 0.9, transform: [{ scale: 0.985 }] },
  disabled: { opacity: 0.45 },

  primary: { backgroundColor: theme.colors.secondaryDark },
  secondary: { backgroundColor: theme.colors.secondary },
  accent: { backgroundColor: theme.colors.secondaryDark },
  danger: { backgroundColor: theme.colors.error },
  soft: { backgroundColor: theme.colors.accentLight, borderWidth: 1, borderColor: theme.colors.accentSoft },
  white: { backgroundColor: theme.colors.surface },
  outline: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1.5,
    borderColor: theme.colors.secondaryDark,
  },
  outlineLight: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  ghost: { backgroundColor: 'transparent' },

  size_sm: { paddingVertical: 8, paddingHorizontal: 14, minHeight: 44 },
  size_md: { paddingVertical: 12, paddingHorizontal: 18, minHeight: 48 },
  size_lg: { paddingVertical: 14, paddingHorizontal: 22, minHeight: 52 },

  text: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', letterSpacing: -0.1 },
  textSize_sm: { fontSize: 13 },
  textSize_md: { fontSize: 15 },
  textSize_lg: { fontSize: 16 },
});
