import { Ionicons } from '@expo/vector-icons';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, TextInputProps, View } from 'react-native';

import { FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
}

export function Input({
  label,
  error,
  hint,
  style,
  secureTextEntry,
  editable = true,
  accessibilityLabel,
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
        <TextInput
          style={[
            styles.input,
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
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            props.onBlur?.(e);
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
        <Text style={styles.error} accessibilityRole="alert" accessibilityLiveRegion="polite">
          {error}
        </Text>
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
    marginBottom: 7,
  },
  inputWrap: { position: 'relative' },
  input: {
    backgroundColor: theme.colors.surface,
    borderWidth: 1.5,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.md,
    paddingHorizontal: theme.spacing.md,
    paddingVertical: 14,
    fontSize: 16,
    fontFamily: FONT_MEDIUM,
    color: theme.colors.text,
  },
  inputWithIcon: { paddingRight: 48 },
  inputFocused: {
    borderColor: theme.colors.secondary,
    backgroundColor: theme.colors.accentLight,
  },
  inputError: { borderColor: theme.colors.error, backgroundColor: theme.colors.errorLight },
  inputDisabled: { backgroundColor: theme.colors.surfaceMuted, color: theme.colors.textMuted },
  eyeBtn: { position: 'absolute', right: 12, top: 0, bottom: 0, justifyContent: 'center' },
  error: { color: theme.colors.error, fontSize: 13, marginTop: 6, fontFamily: FONT_MEDIUM },
  hint: { color: theme.colors.textMuted, fontSize: 13, marginTop: 6 },
});
