import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { theme } from '@/constants/theme';

/** Bottom padding so scroll content clears the tab bar on web + native. */
export function useTabClearance(extra = 0): number {
  const insets = useSafeAreaInsets();
  return insets.bottom + theme.spacing.lg + theme.layout.tabBarClearance + extra;
}

/** Absolute FAB offset above the tab bar. */
export function useFabBottom(): number {
  const insets = useSafeAreaInsets();
  return Math.max(theme.layout.fabBottom, theme.layout.tabBarBase + insets.bottom + theme.spacing.md);
}
