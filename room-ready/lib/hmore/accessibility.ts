import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = '@hmore/accessibility';

export type TextScale = 'default' | 'large' | 'xlarge';

export interface AccessibilityPrefs {
  textScale: TextScale;
  highContrast: boolean;
  language: string;
}

type PrefsListener = (prefs: AccessibilityPrefs) => void;
const listeners = new Set<PrefsListener>();

export function subscribeAccessibilityPrefs(listener: PrefsListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function publishAccessibilityPrefs(prefs: AccessibilityPrefs) {
  listeners.forEach((listener) => listener(prefs));
}

export const DEFAULT_ACCESSIBILITY: AccessibilityPrefs = {
  textScale: 'default',
  highContrast: false,
  language: 'en',
};

export const LANGUAGE_OPTIONS: { id: 'en' | 'ur'; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'ur', label: 'اردو' },
];

export function textScaleMultiplier(scale: TextScale): number {
  if (scale === 'large') return 1.15;
  if (scale === 'xlarge') return 1.3;
  return 1;
}

export async function loadAccessibilityPrefs(): Promise<AccessibilityPrefs> {
  const raw = await AsyncStorage.getItem(KEY);
  if (!raw) return DEFAULT_ACCESSIBILITY;
  try {
    const parsed = JSON.parse(raw) as Partial<AccessibilityPrefs>;
    const textScale: TextScale =
      parsed.textScale === 'large' || parsed.textScale === 'xlarge' ? parsed.textScale : 'default';
    return {
      textScale,
      highContrast: parsed.highContrast === true,
      language: parsed.language === 'ur' ? 'ur' : 'en',
    };
  } catch {
    return DEFAULT_ACCESSIBILITY;
  }
}

export async function saveAccessibilityPrefs(prefs: AccessibilityPrefs): Promise<void> {
  const next: AccessibilityPrefs = {
    ...prefs,
    language: prefs.language === 'ur' ? 'ur' : 'en',
  };
  await AsyncStorage.setItem(KEY, JSON.stringify(next));
  publishAccessibilityPrefs(next);
}
