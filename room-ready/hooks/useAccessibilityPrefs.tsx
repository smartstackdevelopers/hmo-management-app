import { useCallback, useEffect, useState } from 'react';

import {
  AccessibilityPrefs,
  DEFAULT_ACCESSIBILITY,
  loadAccessibilityPrefs,
  saveAccessibilityPrefs,
  textScaleMultiplier,
} from '@/lib/hmore/accessibility';

export function useAccessibilityPrefs() {
  const [prefs, setPrefs] = useState<AccessibilityPrefs>(DEFAULT_ACCESSIBILITY);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    loadAccessibilityPrefs().then((loaded) => {
      if (!active) return;
      setPrefs(loaded);
      setReady(true);
    });
    return () => {
      active = false;
    };
  }, []);

  const update = useCallback(async (partial: Partial<AccessibilityPrefs>) => {
    let next = DEFAULT_ACCESSIBILITY;
    setPrefs((current) => {
      next = { ...current, ...partial };
      return next;
    });
    await saveAccessibilityPrefs(next);
    return next;
  }, []);

  return {
    prefs,
    ready,
    update,
    fontScale: textScaleMultiplier(prefs.textScale),
  };
}
