import { StatusBar } from 'expo-status-bar';

/** Place at the top of a screen to override the root status bar style while focused. */
export function FocusStatusBar({ style }: { style: 'light' | 'dark' | 'auto' }) {
  return <StatusBar style={style} />;
}
