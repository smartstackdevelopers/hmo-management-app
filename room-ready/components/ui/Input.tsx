import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';

import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  leftIcon?: keyof typeof Ionicons.glyphMap;
}

export function Input({
  label,
  error,
  hint,
  leftIcon,
  style,
  secureTextEntry,
  editable = true,
  accessibilityLabel,
  onFocus,
  onBlur,
  ...props
}: InputProps) {
  const [focused, setFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = secureTextEntry === true;

  return (
    <View style={styles.container}>
      {label ? (
        <Text nativeID={`${props.id ?? label}-label`} style={styles.label}>
          {label}
        </Text>
      ) : null}
      <View style={styles.inputWrap}>
        {leftIcon && (
          <View style={styles.leftIcon} pointerEvents="none">
            <Ionicons
              name={leftIcon}
              size={18}
              color={error ? theme.colors.error : focused ? theme.colors.secondaryDark : theme.colors.textMuted}
            />
          </View>
        )}
        <TextInput
          style={[
            styles.input,
            props.multiline && styles.inputMultiline,
            leftIcon && styles.inputWithLeftIcon,
            isPassword && styles.inputWithIcon,
            focused && styles.inputFocused,
            error && styles.inputError,
            editable === false && styles.inputDisabled,
            style,
          ]}
          placeholderTextColor={theme.colors.textMuted}
          secureTextEntry={isPassword && !showPassword}
          editable={editable}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          {...props}
          accessibilityLabel={accessibilityLabel ?? label}
          accessibilityLabelledBy={label ? `${props.id ?? label}-label` : undefined}
        />
        {isPassword && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
            style={styles.eyeBtn}
            onPress={() => setShowPassword((v) => !v)}
            hitSlop={8}
          >
            <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={20} color={theme.colors.textMuted} />
          </Pressable>
        )}
      </View>
      {error ? (
        <View style={styles.errorRow}>
          <Ionicons name="alert-circle" size={14} color={theme.colors.error} />
          <Text style={styles.error} accessibilityRole="alert" accessibilityLiveRegion="polite">
            {error}
          </Text>
        </View>
      ) : null}
      {hint && !error && <Text style={styles.hint}>{hint}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: theme.spacing.md },
  label: {
    fontSize: 13,
    fontFamily: FONT_SEMIBOLD,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 6,
  },
  inputWrap: { position: 'relative', justifyContent: 'center' },
  input: {
    minHeight: 46,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    paddingHorizontal: 14,
    paddingVertical: 11,
    fontSize: 15,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.text,
  },
  inputMultiline: { minHeight: 96, textAlignVertical: 'top' },
  inputWithLeftIcon: { paddingLeft: 42 },
  inputWithIcon: { paddingRight: 48 },
  inputFocused: {
    borderColor: theme.colors.secondary,
    borderWidth: 1.5,
  },
  inputError: { borderColor: theme.colors.error, borderWidth: 1.5 },
  inputDisabled: { backgroundColor: theme.colors.surfaceMuted, color: theme.colors.textMuted },
  leftIcon: { position: 'absolute', left: 14, top: 0, bottom: 0, justifyContent: 'center', zIndex: 1 },
  eyeBtn: {
    position: 'absolute',
    right: 4,
    top: 0,
    bottom: 0,
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  errorRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 6 },
  error: { color: theme.colors.error, fontSize: 13, fontFamily: FONT_MEDIUM, flexShrink: 1 },
  hint: { color: theme.colors.textMuted, fontSize: 12, marginTop: 6, fontFamily: FONT_MEDIUM },
});
