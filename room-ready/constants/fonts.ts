import { Platform, Text, TextInput } from 'react-native';

export const FONT_REGULAR = 'PlusJakartaSans_400Regular';
export const FONT_MEDIUM = 'PlusJakartaSans_500Medium';
export const FONT_SEMIBOLD = 'PlusJakartaSans_600SemiBold';
export const FONT_BOLD = 'PlusJakartaSans_700Bold';

export function applyGlobalFonts() {
  const textStyle = { fontFamily: FONT_REGULAR };
  const inputStyle = { fontFamily: FONT_REGULAR };

  const textDefaults = (Text as unknown as { defaultProps?: { style?: object } }).defaultProps ?? {};
  (Text as unknown as { defaultProps: { style?: object } }).defaultProps = {
    ...textDefaults,
    style: [textStyle, textDefaults.style],
  };

  const inputDefaults = (TextInput as unknown as { defaultProps?: { style?: object } }).defaultProps ?? {};
  (TextInput as unknown as { defaultProps: { style?: object } }).defaultProps = {
    ...inputDefaults,
    style: [inputStyle, inputDefaults.style],
  };
}

export function webShadow(level: 'sm' | 'md' | 'lg' = 'sm') {
  if (Platform.OS !== 'web') return {};
  const map = {
    sm: '0 1px 2px rgba(11, 18, 32, 0.04), 0 1px 3px rgba(11, 18, 32, 0.06)',
    md: '0 4px 12px rgba(11, 18, 32, 0.06), 0 2px 4px rgba(11, 18, 32, 0.04)',
    lg: '0 12px 32px rgba(11, 18, 32, 0.1), 0 4px 8px rgba(11, 18, 32, 0.04)',
  };
  return { boxShadow: map[level] } as object;
}
