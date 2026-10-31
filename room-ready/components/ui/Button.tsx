import { ActivityIndicator, Platform, Pressable, StyleSheet, Text, ViewStyle } from 'react-native';

import { FONT_SEMIBOLD, webShadow } from '@/constants/fonts';
import { theme } from '@/constants/theme';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'outlineLight' | 'ghost' | 'accent';
type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  loading?: boolean;
  fullWidth?: boolean;
  style?: ViewStyle;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  fullWidth = false,
  style,
}: ButtonProps) {
  const isDisabled = disabled || loading;
  const spinnerColor =
    variant === 'outline' || variant === 'outlineLight' || variant === 'ghost'
      ? theme.colors.secondary
      : theme.colors.textInverse;

  return (
    <Pressable
      onPress={onPress ?? (() => {})}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        styles[variant],
        styles[`size_${size}`],
        fullWidth && styles.fullWidth,
        variant === 'secondary' || variant === 'accent'
          ? Platform.OS === 'web'
            ? webShadow('sm')
            : theme.shadows.glow
          : undefined,
        pressed && !isDisabled && styles.pressed,
        isDisabled && styles.disabled,
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={spinnerColor} size="small" />
      ) : (
        <Text style={[styles.text, styles[`text_${variant}`], styles[`textSize_${size}`]]}>{title}</Text>
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
  fullWidth: { width: '100%' },
  pressed: { opacity: 0.88, transform: [{ scale: 0.985 }] },
  disabled: { opacity: 0.45 },

  primary: { backgroundColor: theme.colors.primary },
  secondary: { backgroundColor: theme.colors.secondary },
  accent: { backgroundColor: theme.colors.secondaryDark },
  outline: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1.5,
    borderColor: theme.colors.border,
  },
  outlineLight: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1.5,
    borderColor: theme.colors.border,
  },
  ghost: { backgroundColor: 'transparent' },

  size_sm: { paddingVertical: 9, paddingHorizontal: 14, minHeight: 36 },
  size_md: { paddingVertical: 13, paddingHorizontal: 18, minHeight: 46 },
  size_lg: { paddingVertical: 16, paddingHorizontal: 22, minHeight: 54 },

  text: { fontFamily: FONT_SEMIBOLD, fontWeight: '600', letterSpacing: -0.1 },
  text_primary: { color: theme.colors.textInverse },
  text_secondary: { color: theme.colors.textInverse },
  text_accent: { color: theme.colors.textInverse },
  text_outline: { color: theme.colors.text },
  text_outlineLight: { color: theme.colors.text },
  text_ghost: { color: theme.colors.secondary },

  textSize_sm: { fontSize: 13 },
  textSize_md: { fontSize: 15 },
  textSize_lg: { fontSize: 16 },
});
