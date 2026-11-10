import { useCallback } from 'react';

import { useAccessibilityPrefs } from '@/hooks/useAccessibilityPrefs';
import { resolveLanguage, translate, type AppLanguage } from '@/lib/i18n';

export function useI18n() {
  const access = useAccessibilityPrefs();
  const locale: AppLanguage = resolveLanguage(access.prefs.language);
  const t = useCallback((key: string) => translate(locale, key), [locale]);
  return { ...access, locale, t };
}
