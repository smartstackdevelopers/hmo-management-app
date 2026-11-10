import { en } from './en';
import { ur } from './ur';

const dictionaries = { en, ur };

export type AppLanguage = keyof typeof dictionaries;

export function resolveLanguage(language: string | null | undefined): AppLanguage {
  return language === 'ur' ? 'ur' : 'en';
}

function readPath(source: unknown, key: string): string | undefined {
  let current: unknown = source;
  for (const part of key.split('.')) {
    if (!current || typeof current !== 'object' || !(part in current)) return undefined;
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === 'string' ? current : undefined;
}

/** Missing keys, and any language other than Urdu, fall back to English. */
export function translate(language: string | null | undefined, key: string): string {
  const locale = resolveLanguage(language);
  return readPath(dictionaries[locale], key) ?? readPath(dictionaries.en, key) ?? key;
}

export { en, ur };
