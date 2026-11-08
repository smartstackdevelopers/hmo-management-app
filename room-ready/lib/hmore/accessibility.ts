import AsyncStorage from '@react-native-async-storage/async-storage';

const KEY = '@hmore/accessibility';

export type TextScale = 'default' | 'large' | 'xlarge';

export interface AccessibilityPrefs {
  textScale: TextScale;
  highContrast: boolean;
  language: string;
}

export const DEFAULT_ACCESSIBILITY: AccessibilityPrefs = {
  textScale: 'default',
  highContrast: false,
  language: 'en',
};

export const LANGUAGE_OPTIONS: { id: string; label: string }[] = [
  { id: 'en', label: 'English' },
  { id: 'cy', label: 'Cymraeg' },
  { id: 'pl', label: 'Polski' },
  { id: 'ur', label: 'اردو' },
  { id: 'pa', label: 'ਪੰਜਾਬੀ' },
  { id: 'bn', label: 'বাংলা' },
  { id: 'so', label: 'Soomaali' },
  { id: 'ar', label: 'العربية' },
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
      language: typeof parsed.language === 'string' ? parsed.language : 'en',
    };
  } catch {
    return DEFAULT_ACCESSIBILITY;
  }
}

export async function saveAccessibilityPrefs(prefs: AccessibilityPrefs): Promise<void> {
  await AsyncStorage.setItem(KEY, JSON.stringify(prefs));
}
