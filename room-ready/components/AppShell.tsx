import { Platform, StyleSheet, View } from 'react-native';

import { theme } from '@/constants/theme';

export function AppShell({ children }: { children: React.ReactNode }) {
  if (Platform.OS !== 'web') {
    return <View style={styles.native}>{children}</View>;
  }

  return (
    <View style={styles.webOuter}>
      <View style={styles.webGlow} />
      <View style={styles.webFrame}>{children}</View>
    </View>
  );
}

const styles = StyleSheet.create({
  native: { flex: 1, backgroundColor: theme.colors.background },
  webOuter: {
    flex: 1,
    minHeight: '100dvh' as unknown as number,
    backgroundColor: '#E8EEF2',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  webGlow: {
    position: 'absolute',
    top: '12%',
    width: 520,
    height: 520,
    borderRadius: 260,
    backgroundColor: 'rgba(13, 148, 136, 0.08)',
  },
  webFrame: {
    flex: 1,
    width: '100%',
    maxWidth: theme.layout.phoneMaxWidth,
    minHeight: '100dvh' as unknown as number,
    backgroundColor: theme.colors.background,
    overflow: 'hidden',
    borderLeftWidth: 1,
    borderRightWidth: 1,
    borderColor: theme.colors.border,
    ...(Platform.OS === 'web'
      ? ({ boxShadow: '0 0 0 1px rgba(11,18,32,0.03), 0 24px 64px rgba(11,18,32,0.1)' } as object)
      : {}),
  },
});
