/** Relative luminance (WCAG). */
export function relativeLuminance(hex: string): number {
  const normalized = hex.replace("#", "");
  const channels = [0, 2, 4].map((i) => {
    const v = parseInt(normalized.slice(i, i + 2), 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

export function contrastRatio(foreground: string, background: string): number {
  const l1 = relativeLuminance(foreground);
  const l2 = relativeLuminance(background);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/** Documented HMore brand pairs used in F7.5 verification. */
export const BRAND_CONTRAST_SAMPLES = {
  bodyOnCream: { fg: "#334155", bg: "#f6f3ee", minRatio: 4.5 },
  headingForestOnCream: { fg: "#0f3b32", bg: "#f6f3ee", minRatio: 4.5 },
  primaryButton: { fg: "#ffffff", bg: "#0f766e", minRatio: 4.5 },
  navOnForest: { fg: "#ecfdf5", bg: "#0f3b32", minRatio: 4.5 },
} as const;

export function verifyBrandContrastSamples(): { id: string; ratio: number; pass: boolean }[] {
  return Object.entries(BRAND_CONTRAST_SAMPLES).map(([id, sample]) => {
    const ratio = contrastRatio(sample.fg, sample.bg);
    return { id, ratio: Math.round(ratio * 100) / 100, pass: ratio >= sample.minRatio };
  });
}
